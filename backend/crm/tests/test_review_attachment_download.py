import io
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TransactionTestCase, override_settings
from rest_framework.test import APIClient
from PIL import Image

from crm.models import AccessRole, Customer, EmployeeProfile, FollowUp, FollowUpAttachment, OrganizationUnit, Position, RolePermission


@override_settings(DEVELOPMENT_SUPERADMIN=False, RBAC_ENFORCEMENT=True, AUDIT_LOG_ENABLED=True)
class ReviewAttachmentDownloadTests(TransactionTestCase):
    def test_opaque_storage_key_preserves_original_download_name_and_bytes(self):
        with tempfile.TemporaryDirectory(prefix="review-attachment-download-") as media:
            with override_settings(MEDIA_ROOT=media):
                operator = get_user_model().objects.create_superuser(
                    username="synthetic-download", password="test-only-password",
                )
                client = APIClient()
                client.force_authenticate(operator)
                customer = Customer.objects.create(code="REVIEW-DOWNLOAD", name="Synthetic download customer")
                follow_up = FollowUp.objects.create(
                    customer=customer, followed_at="2026-11-04T09:00:00Z",
                    type="email", subject="Synthetic attachment download",
                )
                body = b"Synthetic attachment bytes; no business data."
                response = client.post(
                    f"/api/follow-ups/{follow_up.pk}/attachments/",
                    {"files": [SimpleUploadedFile("office-evidence.txt", body, content_type="text/plain")]},
                    format="multipart",
                )
                self.assertEqual(response.status_code, 201, response.data)
                attachment = FollowUpAttachment.objects.get(follow_up=follow_up)
                self.assertNotEqual(attachment.file.name.rsplit("/", 1)[-1], attachment.name)
                downloaded = client.get(f"/api/media/{attachment.file.name}")
                try:
                    self.assertEqual(downloaded.status_code, 200)
                    self.assertEqual(b"".join(downloaded.streaming_content), body)
                    self.assertIn("attachment", downloaded["Content-Disposition"])
                    self.assertIn("office-evidence.txt", downloaded["Content-Disposition"])
                    self.assertEqual(downloaded["Content-Type"], "application/octet-stream")
                    self.assertEqual(downloaded["Cache-Control"], "private, no-store")
                    self.assertEqual(downloaded["X-Content-Type-Options"], "nosniff")
                    self.assertEqual(downloaded["Content-Security-Policy"], "default-src 'none'; sandbox")
                    self.assertEqual(downloaded["Cross-Origin-Resource-Policy"], "same-origin")
                finally:
                    downloaded.close()

    def _upload(self, client, filename, content, content_type, *, code="REVIEW-ACTIVE", customer_name="Synthetic attachment customer"):
        customer = Customer.objects.create(code=code, name=customer_name)
        follow_up = FollowUp.objects.create(
            customer=customer, followed_at="2026-11-04T09:00:00Z",
            type="email", subject="Synthetic attachment review",
        )
        response = client.post(
            f"/api/follow-ups/{follow_up.pk}/attachments/",
            {"files": [SimpleUploadedFile(filename, content, content_type=content_type)]},
            format="multipart",
        )
        self.assertEqual(response.status_code, 201, getattr(response, "data", response.content))
        return FollowUpAttachment.objects.get(follow_up=follow_up)

    def test_legacy_svg_and_html_with_misleading_png_metadata_are_download_only(self):
        with tempfile.TemporaryDirectory(prefix="review-active-media-") as media:
            with override_settings(MEDIA_ROOT=media):
                operator = get_user_model().objects.create_superuser(
                    username="synthetic-active-media", password="test-only-password",
                )
                client = APIClient()
                client.force_authenticate(operator)
                payload = b"<!doctype html><script>document.body.textContent='active'</script>"
                for index, (name, content_type) in enumerate((("old.svg", "image/svg+xml"), ("old.png", "image/png"))):
                    with self.subTest(name=name):
                        attachment = self._upload(
                            client, name, payload, content_type,
                            code=f"REVIEW-ACTIVE-{index}",
                            customer_name=f"Synthetic active customer {index}",
                        )
                        # Simulate old persisted metadata; the response policy must
                        # classify the bytes on every read.
                        attachment.content_type = content_type
                        attachment.save(update_fields=["content_type"])
                        downloaded = client.get(f"/api/media/{attachment.file.name}")
                        try:
                            self.assertEqual(downloaded.status_code, 200)
                            self.assertEqual(downloaded["Content-Type"], "application/octet-stream")
                            self.assertIn("attachment", downloaded["Content-Disposition"])
                            self.assertEqual(b"".join(downloaded.streaming_content), payload)
                        finally:
                            downloaded.close()

    def test_verified_raster_preview_uses_detected_type_not_client_mime(self):
        with tempfile.TemporaryDirectory(prefix="review-raster-preview-") as media:
            with override_settings(MEDIA_ROOT=media):
                operator = get_user_model().objects.create_superuser(
                    username="synthetic-raster-preview", password="test-only-password",
                )
                client = APIClient()
                client.force_authenticate(operator)
                buffer = io.BytesIO()
                Image.new("RGB", (2, 2), color=(12, 34, 56)).save(buffer, format="PNG")
                attachment = self._upload(
                    client, "diagram.png", buffer.getvalue(), "text/html",
                    code="REVIEW-RASTER", customer_name="Synthetic raster customer",
                )
                downloaded = client.get(f"/api/media/{attachment.file.name}")
                try:
                    self.assertEqual(downloaded.status_code, 200)
                    self.assertEqual(downloaded["Content-Type"], "image/png")
                    self.assertTrue(downloaded["Content-Disposition"].startswith("inline;"))
                    self.assertEqual(b"".join(downloaded.streaming_content), buffer.getvalue())
                finally:
                    downloaded.close()

    def test_corrupt_image_is_download_only_and_missing_file_is_generic_not_found(self):
        with tempfile.TemporaryDirectory(prefix="review-corrupt-media-") as media:
            with override_settings(MEDIA_ROOT=media):
                operator = get_user_model().objects.create_superuser(
                    username="synthetic-corrupt-media", password="test-only-password",
                )
                client = APIClient()
                client.force_authenticate(operator)
                damaged = b"\x89PNG\r\n\x1a\nnot-a-valid-image"
                attachment = self._upload(
                    client, "damaged.png", damaged, "image/png",
                    code="REVIEW-CORRUPT", customer_name="Synthetic damaged customer",
                )
                downloaded = client.get(f"/api/media/{attachment.file.name}")
                try:
                    self.assertEqual(downloaded.status_code, 200)
                    self.assertEqual(downloaded["Content-Type"], "application/octet-stream")
                    self.assertIn("attachment", downloaded["Content-Disposition"])
                    self.assertEqual(b"".join(downloaded.streaming_content), damaged)
                finally:
                    downloaded.close()

                attachment.file.storage.delete(attachment.file.name)
                missing = client.get(f"/api/media/{attachment.file.name}")
                self.assertEqual(missing.status_code, 404)
                self.assertIn("附件当前不可访问".encode(), missing.content)
                self.assertNotIn(attachment.file.name.encode(), missing.content)
                self.assertNotIn(b"Traceback", missing.content)

    def test_other_business_user_cannot_read_attachment_key(self):
        with tempfile.TemporaryDirectory(prefix="review-cross-business-media-") as media:
            with override_settings(MEDIA_ROOT=media):
                owner = get_user_model().objects.create_superuser(
                    username="synthetic-cross-business-owner", password="test-only-password",
                )
                owner_client = APIClient()
                owner_client.force_authenticate(owner)
                attachment = self._upload(
                    owner_client, "private-note.html", b"<html>private</html>", "text/html",
                    code="REVIEW-PRIVATE", customer_name="Synthetic private customer",
                )
                other = get_user_model().objects.create_user(
                    username="synthetic-other-business", password="test-only-password",
                )
                other_client = APIClient()
                other_client.force_authenticate(other)
                response = other_client.get(f"/api/media/{attachment.file.name}")
                self.assertIn(response.status_code, (403, 404))
                self.assertNotIn(attachment.file.name.encode(), response.content)
                self.assertNotIn(b"Traceback", response.content)

    def test_customer_scope_keeps_a_followup_attachment_bound_to_its_business(self):
        with tempfile.TemporaryDirectory(prefix="review-scoped-media-") as media:
            with override_settings(MEDIA_ROOT=media):
                operator = get_user_model().objects.create_superuser(
                    username="synthetic-scoped-media-creator", password="test-only-password",
                )
                creator = APIClient()
                creator.force_authenticate(operator)
                attachment = self._upload(
                    creator, "scoped-note.txt", b"private customer note", "text/plain",
                    code="REVIEW-SCOPED", customer_name="Synthetic scoped customer",
                )
                role = AccessRole.objects.create(name="合成附件查看", code="review-attachment-view", default_data_scope="self")
                RolePermission.objects.create(role=role, module="followups", can_view=True)
                unit = OrganizationUnit.objects.create(name="合成附件部门", code="REVIEW-ATTACHMENT-UNIT")
                position = Position.objects.create(unit=unit, name="合成附件岗位", code="REVIEW-ATTACHMENT-POS")

                profiles = []
                for username in ("synthetic-media-owner", "synthetic-media-other"):
                    user = get_user_model().objects.create_user(username=username, password="test-only-password")
                    profile = EmployeeProfile.objects.create(user=user, display_name=username, unit=unit, position=position)
                    profile.roles.add(role)
                    profiles.append((user, profile))

                customer = FollowUp.objects.get(attachments=attachment).customer
                customer.owner_profile = profiles[0][1]
                customer.save(update_fields=["owner_profile"])
                allowed = APIClient()
                allowed.force_authenticate(profiles[0][0])
                denied = APIClient()
                denied.force_authenticate(profiles[1][0])

                allowed_response = allowed.get(f"/api/media/{attachment.file.name}")
                denied_response = denied.get(f"/api/media/{attachment.file.name}")
                try:
                    self.assertEqual(allowed_response.status_code, 200)
                    self.assertEqual(b"".join(allowed_response.streaming_content), b"private customer note")
                    self.assertEqual(denied_response.status_code, 404)
                    self.assertNotIn(attachment.file.name.encode(), denied_response.content)
                    self.assertIn("附件当前不可访问".encode(), denied_response.content)
                finally:
                    allowed_response.close()

    def test_special_characters_in_original_filename_are_safely_preserved(self):
        with tempfile.TemporaryDirectory(prefix="review-filename-media-") as media:
            with override_settings(MEDIA_ROOT=media):
                operator = get_user_model().objects.create_superuser(
                    username="synthetic-filename-media", password="test-only-password",
                )
                client = APIClient()
                client.force_authenticate(operator)
                filename = '汇款凭证 "; 2026.txt'
                attachment = self._upload(
                    client, filename, b"synthetic filename body", "text/plain",
                    code="REVIEW-FILENAME", customer_name="Synthetic filename customer",
                )
                downloaded = client.get(f"/api/media/{attachment.file.name}")
                try:
                    self.assertEqual(downloaded.status_code, 200)
                    disposition = downloaded["Content-Disposition"]
                    self.assertIn("attachment", disposition)
                    self.assertTrue("filename*=" in disposition or filename in disposition)
                    self.assertNotIn("\r", disposition)
                    self.assertNotIn("\n", disposition)
                    self.assertEqual(b"".join(downloaded.streaming_content), b"synthetic filename body")
                finally:
                    downloaded.close()
