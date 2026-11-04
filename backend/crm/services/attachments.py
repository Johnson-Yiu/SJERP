"""Failure-aware persistence for follow-up attachments."""

import hashlib
import json
import logging
import os
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.files import File
from django.db import connection, transaction
from django.http import Http404

from ..audit import record_operation
from ..models import FollowUpAttachment


logger = logging.getLogger(__name__)


class AttachmentCompensationError(RuntimeError):
    """A storage operation failed and its compensating action also failed."""


def _delete_lock_key(attachment_pk):
    digest = hashlib.blake2b(
        f"follow-up-attachment-delete:{attachment_pk}".encode("ascii"),
        digest_size=8,
    ).digest()
    return int.from_bytes(digest, byteorder="big", signed=True)


@contextmanager
def _serialized_attachment_delete(attachment_pk):
    """Hold a PostgreSQL session lock through commit-failure compensation."""
    if connection.vendor != "postgresql":
        yield
        return

    lock_key = _delete_lock_key(attachment_pk)
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_lock(%s)", [lock_key])
    try:
        yield
    finally:
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_unlock(%s)", [lock_key])
        except Exception:
            logger.critical(
                "Could not release attachment delete session lock for id=%s; "
                "the PostgreSQL connection must be discarded.",
                attachment_pk,
                exc_info=True,
            )
            try:
                connection.close()
            except Exception:
                logger.exception("Could not discard the PostgreSQL connection after lock-release failure.")


def _digest_stream(file_obj):
    digest = hashlib.sha256()
    original_position = file_obj.tell()
    file_obj.seek(0)
    for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
        digest.update(chunk)
    file_obj.seek(original_position)
    return digest.digest()


def _storage_digest(storage, name):
    with storage.open(name, "rb") as file_obj:
        return _digest_stream(file_obj)


def _cleanup_confirmed_uploads(storage, names):
    failures = []
    for name in reversed(tuple(dict.fromkeys(names))):
        try:
            if storage.exists(name):
                storage.delete(name)
        except Exception as exc:  # continue cleaning other confirmed keys
            failures.append((name, exc))
    if failures:
        logger.critical(
            "Could not clean up %d confirmed attachment object(s): %s",
            len(failures),
            [name for name, _ in failures],
        )
        raise AttachmentCompensationError(
            f"Could not clean up {len(failures)} confirmed attachment object(s)."
        ) from failures[0][1]


def _storage_object_is_upload_prefix(storage, candidate_name, upload):
    """Check whether a failed write left an exact prefix of this uploaded file."""
    upload.seek(0)
    try:
        with storage.open(candidate_name, "rb") as stored:
            while True:
                stored_chunk = stored.read(1024 * 1024)
                if not stored_chunk:
                    return True
                if upload.read(len(stored_chunk)) != stored_chunk:
                    return False
    finally:
        upload.seek(0)


def _cleanup_failed_upload_candidate(storage, candidate_name, upload):
    """Remove a partial object only when its bytes identify this upload."""
    try:
        if not storage.exists(candidate_name):
            return
        if not _storage_object_is_upload_prefix(storage, candidate_name, upload):
            logger.critical(
                "Unconfirmed object remains at attachment candidate key %s; left untouched.",
                candidate_name,
            )
            raise AttachmentCompensationError(
                f"Unconfirmed object remains at attachment candidate key {candidate_name}; left untouched."
            )
        storage.delete(candidate_name)
    except AttachmentCompensationError:
        raise
    except Exception as exc:
        logger.exception("Could not verify or clean failed attachment candidate %s.", candidate_name)
        raise AttachmentCompensationError(
            f"Could not verify or clean failed attachment candidate {candidate_name}."
        ) from exc


def upload_follow_up_attachments(*, request, follow_up, uploads):
    """Save one batch with a durable DB boundary and file compensation.

    Each batch and each file receives a random storage namespace. Only keys
    returned by storage.save() enter the normal rollback cleanup list; a key
    returned by a backend after collision/renaming is therefore never confused
    with the original candidate.
    """
    field = FollowUpAttachment._meta.get_field("file")
    storage = field.storage
    batch_id = uuid4().hex
    saved_names = []
    attachments = []

    try:
        with transaction.atomic(durable=True):
            for upload in uploads:
                attachment = FollowUpAttachment(
                    follow_up=follow_up,
                    name=upload.name[:255],
                    content_type=upload.content_type or "",
                    size=upload.size,
                )
                upload.seek(0)
                saved_name = None
                candidate_name = None

                # A pre-existing UUID candidate is never cleaned up by this batch.
                # Generate another key rather than relying on get_available_name()
                # and later mistaking its candidate for the key actually written.
                for _ in range(8):
                    file_id = uuid4().hex
                    # Keep the persisted key independent of the user filename and
                    # short enough for the model's max_length; display/download
                    # names remain in the attachment.name field.
                    storage_leaf = f"{batch_id}/{file_id}"
                    candidate_name = field.generate_filename(attachment, storage_leaf)
                    if not storage.exists(candidate_name):
                        break
                else:
                    raise AttachmentCompensationError(
                        "Could not allocate a unique attachment key after repeated collisions."
                    )

                try:
                    saved_name = storage.save(
                        candidate_name,
                        upload,
                        max_length=field.max_length,
                    )
                except Exception as storage_error:
                    try:
                        _cleanup_failed_upload_candidate(
                            storage,
                            candidate_name,
                            upload,
                        )
                    except AttachmentCompensationError as cleanup_error:
                        raise cleanup_error from storage_error
                    raise

                # Do not register the candidate: a storage backend may have
                # returned a different actual key after a concurrent collision.
                saved_names.append(saved_name)
                attachment.file = saved_name
                attachment.save(force_insert=True)
                attachments.append(attachment)

            record_operation(
                request=request,
                instance=follow_up,
                action="custom",
                action_label="上传跟进附件",
                metadata={
                    "attachment_ids": [attachment.pk for attachment in attachments],
                    "file_names": [attachment.name for attachment in attachments],
                },
            )
    except Exception as operation_error:
        try:
            _cleanup_confirmed_uploads(storage, saved_names)
        except AttachmentCompensationError as cleanup_error:
            raise cleanup_error from operation_error
        raise

    return attachments


def _capture_storage_file(storage, name):
    backup = tempfile.TemporaryFile(mode="w+b")
    try:
        with storage.open(name, "rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                backup.write(chunk)
        backup.flush()
        backup.seek(0)
        return backup
    except Exception:
        backup.close()
        raise


def _storage_matches_backup(storage, name, backup):
    try:
        if not storage.exists(name):
            return False
        return _storage_digest(storage, name) == _digest_stream(backup)
    except Exception:
        return False


def _restore_deleted_file(*, storage, file_name, backup, attachment_pk, field):
    """Restore file bytes after a failed delete transaction; repair its key if needed."""
    if _storage_matches_backup(storage, file_name, backup):
        return file_name

    if storage.exists(file_name):
        storage.delete(file_name)

    backup.seek(0)
    candidate_name = storage.get_available_name(file_name, max_length=field.max_length)
    try:
        restored_name = storage.save(
            candidate_name,
            File(backup, name=Path(file_name).name),
            max_length=field.max_length,
        )
    except Exception:
        try:
            if storage.exists(candidate_name):
                storage.delete(candidate_name)
        except Exception:
            logger.exception("Could not remove a partial attachment restore.")
        raise

    if not _storage_matches_backup(storage, restored_name, backup):
        raise AttachmentCompensationError("Restored attachment bytes did not match the backup.")

    if restored_name != file_name:
        updated = FollowUpAttachment.objects.filter(pk=attachment_pk).update(file=restored_name)
        if updated != 1:
            raise AttachmentCompensationError(
                "Attachment file was restored under a new key, but its database reference was not updated."
            )
    return restored_name


def _preserve_recovery_copy(*, backup, file_name, attachment_pk, follow_up_id, cause, restore_error):
    """Persist a private recovery copy and manifest before the temporary file closes."""
    recovery_dir = Path(settings.MEDIA_ROOT).resolve() / ".private-attachment-recovery"
    recovery_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    if os.name != "nt":
        os.chmod(recovery_dir, 0o700)

    recovery_id = uuid4().hex
    backup_path = recovery_dir / f"{recovery_id}.bin"
    manifest_path = recovery_dir / f"{recovery_id}.json"
    backup.seek(0)
    digest = hashlib.sha256()
    with backup_path.open("xb") as destination:
        for chunk in iter(lambda: backup.read(1024 * 1024), b""):
            destination.write(chunk)
            digest.update(chunk)
        destination.flush()
        os.fsync(destination.fileno())
    if os.name != "nt":
        os.chmod(backup_path, 0o600)

    manifest = {
        "recovery_id": recovery_id,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "attachment_id": attachment_pk,
        "follow_up_id": follow_up_id,
        "original_storage_key": file_name,
        "sha256": digest.hexdigest(),
        "backup_path": str(backup_path),
        "cause_type": type(cause).__name__,
        "restore_error_type": type(restore_error).__name__,
    }
    manifest_tmp = recovery_dir / f".{recovery_id}.json.tmp"
    with manifest_tmp.open("x", encoding="utf-8") as manifest_file:
        json.dump(manifest, manifest_file, ensure_ascii=False, indent=2)
        manifest_file.flush()
        os.fsync(manifest_file.fileno())
    os.replace(manifest_tmp, manifest_path)
    if os.name != "nt":
        os.chmod(manifest_path, 0o600)

    logger.critical(
        "Attachment recovery copy retained: backup=%s manifest=%s",
        backup_path,
        manifest_path,
    )
    return backup_path, manifest_path


def _raise_with_recovery_copy(*, backup, file_name, attachment_pk, follow_up_id, cause, restore_error):
    try:
        backup_path, manifest_path = _preserve_recovery_copy(
            backup=backup,
            file_name=file_name,
            attachment_pk=attachment_pk,
            follow_up_id=follow_up_id,
            cause=cause,
            restore_error=restore_error,
        )
    except Exception as persist_error:
        logger.critical(
            "Attachment compensation and durable recovery-copy persistence both failed; "
            "temporary backup cannot be retained. attachment_id=%s storage_key=%s",
            attachment_pk,
            file_name,
            exc_info=True,
        )
        raise AttachmentCompensationError(
            "Attachment compensation failed and the temporary recovery copy could not be persisted."
        ) from persist_error

    raise AttachmentCompensationError(
        "Attachment compensation failed; recovery copy retained at "
        f"{backup_path} with manifest {manifest_path}."
    ) from restore_error


def delete_follow_up_attachment(*, request, follow_up, attachment):
    """Delete with a row lock, durable transaction, and explicit file compensation.

    Storage and the relational database cannot share one atomic transaction. A
    private temporary backup is made while holding a durable DB transaction and
    the attachment row lock. Storage/row/audit failures are compensated before
    that row lock is released; DB failures are contained by a savepoint. A
    PostgreSQL session advisory lock remains held through a durable-commit
    failure and its compensation. If restoration also fails, the backup is
    persisted under MEDIA_ROOT/.private-attachment-recovery with a JSON manifest
    and a critical log entry. The storage backend and private MEDIA_ROOT still
    need operational monitoring and sufficient disk space for this recovery path.
    """
    field = FollowUpAttachment._meta.get_field("file")
    storage = field.storage
    attachment_pk = attachment.pk
    file_name = None
    backup = None
    compensation_attempted = False

    def restore_or_preserve(cause):
        try:
            _restore_deleted_file(
                storage=storage,
                file_name=file_name,
                backup=backup,
                attachment_pk=attachment_pk,
                field=field,
            )
        except Exception as restore_error:
            _raise_with_recovery_copy(
                backup=backup,
                file_name=file_name,
                attachment_pk=attachment_pk,
                follow_up_id=follow_up.pk,
                cause=cause,
                restore_error=restore_error,
            )

    try:
        # The PostgreSQL session lock stays held after transaction rollback/commit
        # failure, covering the interval in which the row lock no longer exists.
        with _serialized_attachment_delete(attachment_pk):
            try:
                # durable=True refuses an application-level outer transaction that
                # could roll back after the physical file has been removed. Django's
                # TestCase wrapper remains supported by Django's durable atomic.
                with transaction.atomic(durable=True):
                    try:
                        locked_attachment = FollowUpAttachment.objects.select_for_update().get(
                            pk=attachment_pk,
                            follow_up_id=follow_up.pk,
                        )
                    except FollowUpAttachment.DoesNotExist as exc:
                        raise Http404 from exc

                    file_name = locked_attachment.file.name
                    attachment_name = locked_attachment.name
                    backup = _capture_storage_file(storage, file_name)

                    try:
                        storage.delete(file_name)
                    except Exception as storage_error:
                        compensation_attempted = True
                        restore_or_preserve(storage_error)
                        raise

                    try:
                        # A savepoint keeps the outer transaction usable after a
                        # database/audit error, so restoration occurs before the
                        # row lock is released.
                        with transaction.atomic():
                            locked_attachment.delete()
                            record_operation(
                                request=request,
                                instance=follow_up,
                                action="custom",
                                action_label="删除跟进附件",
                                metadata={
                                    "attachment_id": attachment_pk,
                                    "file_name": attachment_name,
                                },
                            )
                    except Exception as database_error:
                        compensation_attempted = True
                        restore_or_preserve(database_error)
                        raise
            except Exception as transaction_error:
                # This path covers failure while entering/committing the durable
                # transaction. The session lock above excludes another delete
                # until commit-failure compensation finishes.
                if backup is not None and file_name and not compensation_attempted:
                    compensation_attempted = True
                    restore_or_preserve(transaction_error)
                raise
    finally:
        if backup is not None:
            backup.close()
