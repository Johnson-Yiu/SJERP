import hashlib
import json
from pathlib import Path
import tempfile
import time
from threading import Event, Thread, current_thread
from unittest import skipUnless
from unittest.mock import patch
from uuid import UUID

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import DatabaseError, connection, transaction, close_old_connections
from django.db.backends.base.base import BaseDatabaseWrapper
from django.test import TransactionTestCase, override_settings
from rest_framework.test import APIClient

from crm.models import (
    AccessRole,
    Contact,
    Customer,
    EmployeeProfile,
    FollowUp,
    FollowUpAttachment,
    OperationLog,
    OrganizationUnit,
    Position,
    RolePermission,
)
from crm.services import attachments as attachment_service
from crm.services.attachments import _delete_lock_key
from crm.services.private_media import build_private_media_manifest


def _read_storage(storage, name):
    with storage.open(name, "rb") as file_obj:
        return file_obj.read()


CI_RBAC_SETTINGS = {
    "APP_STAGE": "staging",
    "DEBUG": False,
    "DEVELOPMENT_SUPERADMIN": False,
    "RBAC_ENFORCEMENT": True,
    "AUDIT_LOG_ENABLED": True,
}


@override_settings(**CI_RBAC_SETTINGS)
class ReviewAttachmentAtomicityTests(TransactionTestCase):
    """Inject isolated storage/audit failures and assert attachment consistency."""

    def setUp(self):
        self.media_dir = tempfile.TemporaryDirectory(prefix="iss007-attachment-atomicity-")
        self.media_settings = override_settings(
            MEDIA_ROOT=self.media_dir.name,
            AUDIT_LOG_ENABLED=True,
        )
        self.media_settings.enable()

        self.client = APIClient(raise_request_exception=False)
        self.operator = get_user_model().objects.create_superuser(
            username="attachment-atomicity-review-operator",
            email="attachment-atomicity-review@example.test",
            password="test-only-password",
        )
        self.client.force_authenticate(self.operator)

        self.customer = Customer.objects.create(
            code="REVIEW-ATTACHMENT-CUSTOMER",
            name="Attachment atomicity review",
        )
        self.contact = Contact.objects.create(customer=self.customer, name="Review contact")
        self.follow_up = FollowUp.objects.create(
            customer=self.customer,
            contact=self.contact,
            followed_at="2026-11-04T09:00:00Z",
            type="email",
            subject="Attachment atomicity review",
        )

    def tearDown(self):
        self.media_settings.disable()
        self.media_dir.cleanup()

    def attachment_state(self, action_label):
        attachments = list(FollowUpAttachment.objects.filter(follow_up=self.follow_up))
        files = [path for path in Path(self.media_dir.name).rglob("*") if path.is_file()]
        audit_count = OperationLog.objects.filter(
            object_id=str(self.follow_up.pk),
            action_label=action_label,
        ).count()
        return len(attachments), len(files), audit_count

    def upload(self, *files):
        return self.client.post(
            f"/api/follow-ups/{self.follow_up.pk}/attachments/",
            {"files": list(files)},
            format="multipart",
        )

    def _start_delete_thread(self, name, attachment_pk, started, done, results):
        def run():
            close_old_connections()
            try:
                client = APIClient(raise_request_exception=False)
                client.force_authenticate(self.operator)
                started.set()
                response = client.delete(
                    f"/api/follow-ups/{self.follow_up.pk}/attachments/{attachment_pk}/"
                )
                results[name] = response.status_code
            except Exception as exc:  # make thread failures visible to the test thread
                results[name] = exc
            finally:
                done.set()
                close_old_connections()

        return Thread(target=run, name=name, daemon=True)

    def _wait_for_postgres_advisory_waiter(self, attachment_pk):
        lock_key = _delete_lock_key(attachment_pk) & ((1 << 64) - 1)
        class_id = (lock_key >> 32) & 0xFFFFFFFF
        object_id = lock_key & 0xFFFFFFFF
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT count(*) FROM pg_locks "
                    "WHERE locktype = 'advisory' AND NOT granted "
                    "AND classid = %s::oid AND objid = %s::oid AND objsubid = 1",
                    [class_id, object_id],
                )
                if cursor.fetchone()[0]:
                    return
            time.sleep(0.02)
        self.fail("second delete never queued on the attachment PostgreSQL session lock")

    def test_second_file_storage_failure_leaves_no_partial_batch(self):
        original_save = default_storage._save
        injected = []
        calls = []

        def fail_second_file(name, content):
            calls.append(name)
            if len(calls) == 2:
                injected.append(name)
                content.seek(0)
                partial = content.read(2)
                content.seek(0)
                original_save(name, ContentFile(partial))
                raise OSError("injected second attachment storage failure")
            return original_save(name, content)

        with patch.object(default_storage, "_save", side_effect=fail_second_file):
            response = self.upload(
                SimpleUploadedFile("first.txt", b"first", content_type="text/plain"),
                SimpleUploadedFile("second.txt", b"second", content_type="text/plain"),
            )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(len(injected), 1, "the second file storage failure must be reached")
        self.assertEqual(
            self.attachment_state("上传跟进附件"),
            (0, 0, 0),
            "a failed multi-file upload must leave no rows, stored files, or success audit",
        )

    def test_upload_audit_failure_leaves_no_files_or_attachment_rows(self):
        with patch(
            "crm.services.attachments.record_operation",
            side_effect=DatabaseError("injected attachment upload audit failure"),
        ):
            response = self.upload(
                SimpleUploadedFile("audit-one.txt", b"one", content_type="text/plain"),
                SimpleUploadedFile("audit-two.txt", b"two", content_type="text/plain"),
            )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            self.attachment_state("上传跟进附件"),
            (0, 0, 0),
            "an upload whose audit write fails must leave no rows or files",
        )

    def test_delete_audit_failure_preserves_attachment_row_and_file(self):
        attachment = FollowUpAttachment.objects.create(
            follow_up=self.follow_up,
            file=SimpleUploadedFile("delete-audit.txt", b"preserve me", content_type="text/plain"),
            name="delete-audit.txt",
            content_type="text/plain",
            size=len(b"preserve me"),
        )
        stored_path = Path(attachment.file.path)
        self.assertTrue(stored_path.is_file())

        with patch(
            "crm.services.attachments.record_operation",
            side_effect=DatabaseError("injected attachment delete audit failure"),
        ):
            response = self.client.delete(
                f"/api/follow-ups/{self.follow_up.pk}/attachments/{attachment.pk}/"
            )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            self.attachment_state("删除跟进附件"),
            (1, 1, 0),
            "a delete whose audit write fails must preserve both the database row and file",
        )

    def test_second_attachment_database_failure_cleans_batch_and_rolls_back_rows(self):
        original_save = FollowUpAttachment.save
        calls = []

        def fail_second_row(instance, *args, **kwargs):
            calls.append(instance.name)
            if len(calls) == 2:
                raise DatabaseError("injected second attachment row failure")
            return original_save(instance, *args, **kwargs)

        with patch.object(FollowUpAttachment, "save", autospec=True, side_effect=fail_second_row):
            response = self.upload(
                SimpleUploadedFile("db-one.txt", b"one", content_type="text/plain"),
                SimpleUploadedFile("db-two.txt", b"two", content_type="text/plain"),
            )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(len(calls), 2)
        self.assertEqual(
            self.attachment_state("上传跟进附件"),
            (0, 0, 0),
            "a row failure after the first saved attachment must roll back rows and clean both files",
        )

    def test_delete_database_failure_restores_original_file_and_row(self):
        attachment = FollowUpAttachment.objects.create(
            follow_up=self.follow_up,
            file=SimpleUploadedFile("delete-db.txt", b"keep after DB failure", content_type="text/plain"),
            name="delete-db.txt",
            content_type="text/plain",
            size=len(b"keep after DB failure"),
        )
        original_path = attachment.file.name
        original_delete = FollowUpAttachment.delete

        def delete_then_fail(instance, *args, **kwargs):
            original_delete(instance, *args, **kwargs)
            raise DatabaseError("injected attachment row delete failure")

        with patch.object(FollowUpAttachment, "delete", autospec=True, side_effect=delete_then_fail):
            response = self.client.delete(
                f"/api/follow-ups/{self.follow_up.pk}/attachments/{attachment.pk}/"
            )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            self.attachment_state("删除跟进附件"),
            (1, 1, 0),
            "a rolled-back row deletion must restore the original file and keep the row",
        )
        restored = FollowUpAttachment.objects.get(pk=attachment.pk)
        self.assertEqual(restored.file.name, original_path)
        self.assertEqual(Path(restored.file.path).read_bytes(), b"keep after DB failure")

    def test_storage_delete_failure_after_removal_restores_original_file(self):
        attachment = FollowUpAttachment.objects.create(
            follow_up=self.follow_up,
            file=SimpleUploadedFile("delete-storage.txt", b"keep after storage failure", content_type="text/plain"),
            name="delete-storage.txt",
            content_type="text/plain",
            size=len(b"keep after storage failure"),
        )
        original_delete = default_storage.delete

        def delete_then_fail(name):
            original_delete(name)
            raise OSError("injected storage delete failure after removal")

        with patch.object(default_storage, "delete", side_effect=delete_then_fail):
            response = self.client.delete(
                f"/api/follow-ups/{self.follow_up.pk}/attachments/{attachment.pk}/"
            )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            self.attachment_state("删除跟进附件"),
            (1, 1, 0),
            "a storage delete that removes then raises must restore the file and retain its row",
        )
        restored = FollowUpAttachment.objects.get(pk=attachment.pk)
        self.assertEqual(Path(restored.file.path).read_bytes(), b"keep after storage failure")

    def test_compensation_failure_retains_private_recovery_copy_and_manifest(self):
        attachment = FollowUpAttachment.objects.create(
            follow_up=self.follow_up,
            file=SimpleUploadedFile("dual-failure.txt", b"recovery bytes", content_type="text/plain"),
            name="dual-failure.txt",
            content_type="text/plain",
            size=len(b"recovery bytes"),
        )
        original_delete = default_storage.delete

        def delete_then_fail(name):
            original_delete(name)
            raise OSError("injected primary storage delete failure")

        def fail_restore(*args, **kwargs):
            raise OSError("injected compensation storage save failure")

        with patch.object(default_storage, "delete", side_effect=delete_then_fail):
            with patch.object(default_storage, "save", side_effect=fail_restore):
                response = self.client.delete(
                    f"/api/follow-ups/{self.follow_up.pk}/attachments/{attachment.pk}/"
                )

        self.assertEqual(response.status_code, 500)
        self.assertTrue(FollowUpAttachment.objects.filter(pk=attachment.pk).exists())
        self.assertFalse(default_storage.exists(attachment.file.name))
        recovery_dir = Path(self.media_dir.name) / ".private-attachment-recovery"
        backups = list(recovery_dir.glob("*.bin"))
        manifests = list(recovery_dir.glob("*.json"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(len(manifests), 1)
        manifest = json.loads(manifests[0].read_text(encoding="utf-8"))
        self.assertEqual(Path(manifest["backup_path"]), backups[0])
        self.assertEqual(manifest["attachment_id"], attachment.pk)
        self.assertEqual(manifest["follow_up_id"], self.follow_up.pk)
        self.assertEqual(manifest["original_storage_key"], attachment.file.name)
        self.assertEqual(hashlib.sha256(backups[0].read_bytes()).hexdigest(), manifest["sha256"])
        self.assertFalse(OperationLog.objects.filter(action_label="删除跟进附件").exists())

        media_manifest = build_private_media_manifest(self.media_dir.name)
        entries = {entry["path"]: entry for entry in media_manifest["files"]}
        for recovery_file in backups + manifests:
            relative_path = recovery_file.relative_to(self.media_dir.name).as_posix()
            self.assertIn(relative_path, entries)
            self.assertEqual(entries[relative_path]["size"], recovery_file.stat().st_size)
            self.assertEqual(
                entries[relative_path]["sha256"],
                hashlib.sha256(recovery_file.read_bytes()).hexdigest(),
            )

        for recovery_file in backups + manifests:
            recovery_key = f".private-attachment-recovery/{recovery_file.name}"
            for url in (f"/api/media/{recovery_key}", f"/media/{recovery_key}"):
                for client in (APIClient(), self.client):
                    response = client.get(url)
                    self.assertNotEqual(response.status_code, 200, url)

    def test_storage_candidate_collision_and_rename_never_delete_other_object(self):
        original_save = default_storage.save
        field = FollowUpAttachment._meta.get_field("file")
        batch_id = "a" * 32
        occupied_file_id = "b" * 32
        next_file_id = "c" * 32
        probe = FollowUpAttachment(follow_up=self.follow_up, name="rename-collision.txt")
        occupied_candidate = field.generate_filename(
            probe,
            f"{batch_id}/{occupied_file_id}",
        ).replace("\\", "/")
        preexisting_key = original_save(
            occupied_candidate,
            ContentFile(b"pre-existing collision"),
            max_length=field.max_length,
        )
        self.assertEqual(preexisting_key, occupied_candidate)
        objects = {}

        def collide_then_return_actual_key(requested_name, content, max_length=None):
            # Simulate another writer winning the requested key after our unique
            # key check. The backend stores this request under a different key.
            other_key = original_save(
                requested_name,
                ContentFile(b"other writer's object"),
                max_length=max_length,
            )
            normalized_name = requested_name.replace("\\", "/")
            parent = normalized_name.rsplit("/", 1)[0]
            actual_key = original_save(
                f"{parent}/renamed",
                content,
                max_length=max_length,
            )
            objects["other"] = other_key
            objects["actual"] = actual_key
            return actual_key

        with patch(
            "crm.services.attachments.uuid4",
            side_effect=[UUID(batch_id), UUID(occupied_file_id), UUID(next_file_id)],
        ):
            with patch.object(default_storage, "save", side_effect=collide_then_return_actual_key):
                with patch(
                    "crm.services.attachments.record_operation",
                    side_effect=DatabaseError("injected audit failure after storage rename"),
                ):
                    response = self.upload(
                        SimpleUploadedFile("rename-collision.txt", b"our upload", content_type="text/plain")
                    )

        self.assertEqual(response.status_code, 500)
        self.assertTrue(default_storage.exists(preexisting_key))
        self.assertEqual(_read_storage(default_storage, preexisting_key), b"pre-existing collision")
        self.assertTrue(default_storage.exists(objects["other"]))
        self.assertEqual(_read_storage(default_storage, objects["other"]), b"other writer's object")
        self.assertFalse(default_storage.exists(objects["actual"]))
        self.assertEqual(FollowUpAttachment.objects.filter(follow_up=self.follow_up).count(), 0)
        self.assertFalse(OperationLog.objects.filter(action_label="上传跟进附件").exists())

    def test_actions_fail_closed_inside_non_test_outer_transaction(self):
        with transaction.atomic():
            upload_response = self.upload(
                SimpleUploadedFile("outer-transaction.txt", b"no write", content_type="text/plain")
            )
            self.assertEqual(upload_response.status_code, 500)
            self.assertEqual(self.attachment_state("上传跟进附件"), (0, 0, 0))

            attachment = FollowUpAttachment.objects.create(
                follow_up=self.follow_up,
                file=SimpleUploadedFile("outer-delete.txt", b"keep", content_type="text/plain"),
                name="outer-delete.txt",
                content_type="text/plain",
                size=4,
            )
            stored_path = Path(attachment.file.path)
            delete_response = self.client.delete(
                f"/api/follow-ups/{self.follow_up.pk}/attachments/{attachment.pk}/"
            )
            self.assertEqual(delete_response.status_code, 500)
            self.assertTrue(FollowUpAttachment.objects.filter(pk=attachment.pk).exists())
            self.assertTrue(stored_path.is_file())

        self.assertEqual(FollowUpAttachment.objects.filter(follow_up=self.follow_up).count(), 1)

    def test_successful_batch_upload_and_delete_commit_rows_files_and_audits(self):
        response = self.upload(
            SimpleUploadedFile("success-one.txt", b"one", content_type="text/plain"),
            SimpleUploadedFile("success-two.txt", b"two", content_type="text/plain"),
        )

        self.assertEqual(response.status_code, 201, response.data)
        attachments = list(FollowUpAttachment.objects.filter(follow_up=self.follow_up))
        self.assertEqual(len(attachments), 2)
        self.assertEqual(
            [Path(item.file.path).read_bytes() for item in attachments],
            [b"one", b"two"],
        )
        upload_audit = OperationLog.objects.get(
            object_id=str(self.follow_up.pk),
            action_label="上传跟进附件",
        )
        self.assertEqual(upload_audit.operator, self.operator)
        self.assertEqual(len(upload_audit.metadata["attachment_ids"]), 2)

        target = attachments[0]
        target_path = Path(target.file.path)
        deleted = self.client.delete(
            f"/api/follow-ups/{self.follow_up.pk}/attachments/{target.pk}/"
        )

        self.assertEqual(deleted.status_code, 204)
        self.assertFalse(FollowUpAttachment.objects.filter(pk=target.pk).exists())
        self.assertFalse(target_path.exists())
        self.assertEqual(FollowUpAttachment.objects.filter(follow_up=self.follow_up).count(), 1)
        delete_audit = OperationLog.objects.get(
            object_id=str(self.follow_up.pk),
            action_label="删除跟进附件",
        )
        self.assertEqual(delete_audit.operator, self.operator)
        self.assertEqual(delete_audit.metadata["file_name"], target.name)

    def test_cross_follow_up_delete_is_rejected_without_side_effects(self):
        other_follow_up = FollowUp.objects.create(
            customer=self.customer,
            contact=self.contact,
            followed_at="2026-11-04T10:00:00Z",
            type="email",
            subject="Different follow-up",
        )
        attachment = FollowUpAttachment.objects.create(
            follow_up=self.follow_up,
            file=SimpleUploadedFile("owned-file.txt", b"owned", content_type="text/plain"),
            name="owned-file.txt",
            content_type="text/plain",
            size=5,
        )
        stored_path = Path(attachment.file.path)

        response = self.client.delete(
            f"/api/follow-ups/{other_follow_up.pk}/attachments/{attachment.pk}/"
        )

        self.assertEqual(response.status_code, 404)
        self.assertTrue(FollowUpAttachment.objects.filter(pk=attachment.pk, follow_up=self.follow_up).exists())
        self.assertTrue(stored_path.is_file())
        self.assertFalse(OperationLog.objects.filter(action_label="删除跟进附件").exists())

    def test_rbac_restricted_user_cannot_delete_attachment(self):
        unit = OrganizationUnit.objects.create(name="Attachment RBAC", code="ATTACH-RBAC-U")
        position = Position.objects.create(unit=unit, name="附件只读", code="ATTACH-RBAC-P")
        role = AccessRole.objects.create(name="附件只读角色", code="attachment-view-only")
        RolePermission.objects.create(role=role, module="followups", can_view=True)
        restricted_user = get_user_model().objects.create_user(
            username="attachment-restricted-operator",
            password="test-only-password",
        )
        profile = EmployeeProfile.objects.create(
            user=restricted_user,
            display_name="受限附件操作人",
            unit=unit,
            position=position,
        )
        profile.roles.add(role)
        attachment = FollowUpAttachment.objects.create(
            follow_up=self.follow_up,
            file=SimpleUploadedFile("restricted-delete.txt", b"keep", content_type="text/plain"),
            name="restricted-delete.txt",
            content_type="text/plain",
            size=4,
        )
        stored_path = Path(attachment.file.path)
        restricted_client = APIClient(raise_request_exception=False)
        restricted_client.force_authenticate(restricted_user)

        response = restricted_client.delete(
            f"/api/follow-ups/{self.follow_up.pk}/attachments/{attachment.pk}/"
        )

        self.assertEqual(response.status_code, 403)
        self.assertTrue(FollowUpAttachment.objects.filter(pk=attachment.pk).exists())
        self.assertTrue(stored_path.is_file())
        self.assertFalse(OperationLog.objects.filter(action_label="删除跟进附件").exists())

    @skipUnless(connection.vendor == "postgresql", "Requires PostgreSQL row and advisory locks.")
    def test_postgres_second_delete_waits_through_audit_failure_compensation(self):
        attachment = FollowUpAttachment.objects.create(
            follow_up=self.follow_up,
            file=SimpleUploadedFile("concurrent-audit.txt", b"serialize audit failure", content_type="text/plain"),
            name="concurrent-audit.txt",
            content_type="text/plain",
            size=len(b"serialize audit failure"),
        )
        stored_path = Path(attachment.file.path)
        first_in_audit = Event()
        release_first = Event()
        second_started, second_done = Event(), Event()
        results = {}
        original_record = attachment_service.record_operation

        def fail_first_audit(**kwargs):
            if current_thread().name == "attachment-audit-failure-first":
                first_in_audit.set()
                if not release_first.wait(10):
                    raise TimeoutError("test did not release first audit failure")
                raise DatabaseError("injected concurrent delete audit failure")
            return original_record(**kwargs)

        first = self._start_delete_thread(
            "attachment-audit-failure-first", attachment.pk, Event(), Event(), results
        )
        second = self._start_delete_thread(
            "attachment-audit-failure-second", attachment.pk, second_started, second_done, results
        )

        with patch.object(attachment_service, "record_operation", side_effect=fail_first_audit):
            first.start()
            try:
                self.assertTrue(first_in_audit.wait(10), "first request did not reach audit failure point")
                second.start()
                self.assertTrue(second_started.wait(10), "second request did not start")
                self._wait_for_postgres_advisory_waiter(attachment.pk)
                self.assertFalse(second_done.is_set(), "second delete crossed the held compensation lock")
            finally:
                release_first.set()
            first.join(15)
            second.join(15)

        self.assertFalse(first.is_alive())
        self.assertFalse(second.is_alive())
        self.assertEqual(results.get("attachment-audit-failure-first"), 500)
        self.assertEqual(results.get("attachment-audit-failure-second"), 204)
        self.assertFalse(FollowUpAttachment.objects.filter(pk=attachment.pk).exists())
        self.assertFalse(stored_path.exists())
        self.assertEqual(OperationLog.objects.filter(action_label="删除跟进附件").count(), 1)

    @skipUnless(connection.vendor == "postgresql", "Requires PostgreSQL row and advisory locks.")
    def test_postgres_second_delete_waits_through_commit_failure_compensation(self):
        attachment = FollowUpAttachment.objects.create(
            follow_up=self.follow_up,
            file=SimpleUploadedFile("concurrent-commit.txt", b"serialize commit failure", content_type="text/plain"),
            name="concurrent-commit.txt",
            content_type="text/plain",
            size=len(b"serialize commit failure"),
        )
        stored_path = Path(attachment.file.path)
        compensation_started, release_compensation = Event(), Event()
        second_started, second_done = Event(), Event()
        results = {}
        original_commit = BaseDatabaseWrapper.commit
        original_restore = attachment_service._restore_deleted_file

        def fail_first_commit(db_connection):
            if current_thread().name == "attachment-commit-failure-first":
                raise DatabaseError("injected durable commit failure")
            return original_commit(db_connection)

        def pause_first_compensation(**kwargs):
            if current_thread().name == "attachment-commit-failure-first":
                compensation_started.set()
                if not release_compensation.wait(10):
                    raise TimeoutError("test did not release commit compensation")
            return original_restore(**kwargs)

        first = self._start_delete_thread(
            "attachment-commit-failure-first", attachment.pk, Event(), Event(), results
        )
        second = self._start_delete_thread(
            "attachment-commit-failure-second", attachment.pk, second_started, second_done, results
        )

        with patch.object(BaseDatabaseWrapper, "commit", autospec=True, side_effect=fail_first_commit):
            with patch.object(
                attachment_service,
                "_restore_deleted_file",
                side_effect=pause_first_compensation,
            ):
                first.start()
                try:
                    self.assertTrue(
                        compensation_started.wait(10),
                        "first request did not enter compensation after commit failure",
                    )
                    second.start()
                    self.assertTrue(second_started.wait(10), "second request did not start")
                    self._wait_for_postgres_advisory_waiter(attachment.pk)
                    self.assertFalse(second_done.is_set(), "second delete crossed commit compensation lock")
                finally:
                    release_compensation.set()
                first.join(15)
                second.join(15)

        self.assertFalse(first.is_alive())
        self.assertFalse(second.is_alive())
        self.assertEqual(results.get("attachment-commit-failure-first"), 500)
        self.assertEqual(results.get("attachment-commit-failure-second"), 204)
        self.assertFalse(FollowUpAttachment.objects.filter(pk=attachment.pk).exists())
        self.assertFalse(stored_path.exists())
        self.assertEqual(OperationLog.objects.filter(action_label="删除跟进附件").count(), 1)

    def test_empty_upload_is_rejected_without_side_effects(self):
        response = self.client.post(
            f"/api/follow-ups/{self.follow_up.pk}/attachments/",
            {},
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.attachment_state("上传跟进附件"), (0, 0, 0))
