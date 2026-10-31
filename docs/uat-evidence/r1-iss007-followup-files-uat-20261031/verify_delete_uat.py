"""Snapshot and verify only the synthetic ISS-007 attachment-delete fixture."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import django

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.conf import settings  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402

from crm.models import FollowUpAttachment, OperationLog  # noqa: E402
from test_support.isolated_runtime import verify_isolated_runtime  # noqa: E402


TARGET_NAME = "ISS007-delete-target.txt"
TARGET_BYTES = b"ISS007 disposable delete target\n"
TARGET_SHA256 = hashlib.sha256(TARGET_BYTES).hexdigest()
REPLACEMENT_NAME = "ISS007-delete-target-replacement.txt"
REPLACEMENT_BYTES = b"ISS007 synthetic replacement body\n"
REPLACEMENT_SHA256 = hashlib.sha256(REPLACEMENT_BYTES).hexdigest()
EXPECTED_INITIAL_NAMES = {
    "ISS007-legacy-history.txt",
    "ISS007-preview.txt",
    "ISS007-download.bin",
    TARGET_NAME,
}
EXPECTED_FINAL_NAMES = {
    "ISS007-legacy-history.txt",
    "ISS007-preview.txt",
    "ISS007-download.bin",
    REPLACEMENT_NAME,
}


def attachment_snapshot(follow_up_id: int) -> list[dict]:
    media_root = Path(settings.MEDIA_ROOT).resolve(strict=True)
    result = []
    for attachment in FollowUpAttachment.objects.filter(follow_up_id=follow_up_id).order_by("id"):
        file_path = Path(attachment.file.path)
        resolved = file_path.resolve(strict=True)
        try:
            relative = resolved.relative_to(media_root).as_posix()
        except ValueError as exc:
            raise AssertionError(f"Attachment escaped isolated MEDIA_ROOT: {resolved}") from exc
        if file_path.is_symlink() or not resolved.is_file():
            raise AssertionError(f"Synthetic attachment is not a regular file: {resolved}")
        raw = resolved.read_bytes()
        result.append({
            "id": attachment.pk,
            "name": attachment.name,
            "file": attachment.file.name,
            "relativePath": relative,
            "sizeInDatabase": attachment.size,
            "sizeOnDisk": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
        })
    return result


def main() -> None:
    identity = verify_isolated_runtime(settings=settings, database_must_exist=True)
    if not settings.RBAC_ENFORCEMENT or settings.DEVELOPMENT_SUPERADMIN or not settings.AUDIT_LOG_ENABLED:
        raise RuntimeError("Unexpected isolated test security/audit settings.")
    evidence_dir = Path(os.environ["ISS007_UAT_EVIDENCE_DIR"]).resolve()
    fixture = json.loads((evidence_dir / "fixture.json").read_text(encoding="utf-8"))
    follow_up_id = int(fixture["followUpId"])
    target = Path(os.environ["ISOLATED_TEST_MEDIA_ROOT"]).resolve(strict=True)
    mode = sys.argv[1] if len(sys.argv) > 1 else ""

    if mode == "snapshot":
        records = attachment_snapshot(follow_up_id)
        names = [entry["name"] for entry in records]
        if len(names) != len(set(names)) or set(names) != EXPECTED_INITIAL_NAMES:
            raise AssertionError(f"Pre-delete synthetic attachment set differs: {names}")
        target_entry = next(entry for entry in records if entry["name"] == TARGET_NAME)
        if target_entry["sizeInDatabase"] != len(TARGET_BYTES) or target_entry["sizeOnDisk"] != len(TARGET_BYTES) or target_entry["sha256"] != TARGET_SHA256:
            raise AssertionError(f"Delete target is not the expected 32-byte synthetic file: {target_entry}")
        payload = {
            "phase": "before-delete",
            "runId": identity["runId"],
            "database": identity["database"],
            "mediaRoot": str(target),
            "followUpId": follow_up_id,
            "attachments": records,
        }
        (evidence_dir / "before-delete-snapshot.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    if mode != "verify":
        raise SystemExit("Usage: verify_delete_uat.py snapshot|verify")

    before = json.loads((evidence_dir / "before-delete-snapshot.json").read_text(encoding="utf-8"))
    before_records = before["attachments"]
    target_before = next(entry for entry in before_records if entry["name"] == TARGET_NAME)
    stored_target = Path(identity["mediaRoot"]) / target_before["relativePath"]
    if stored_target.exists():
        raise AssertionError(f"Deleted synthetic target still exists on disk: {stored_target}")
    if FollowUpAttachment.objects.filter(pk=target_before["id"], follow_up_id=follow_up_id).exists():
        raise AssertionError("Deleted synthetic target database row still exists.")

    after_records = attachment_snapshot(follow_up_id)
    after_names = [entry["name"] for entry in after_records]
    if len(after_names) != len(set(after_names)) or set(after_names) != EXPECTED_FINAL_NAMES:
        raise AssertionError(f"Post-delete/replacement attachment set differs: {after_names}")
    expected_unchanged = {entry["name"]: entry for entry in before_records if entry["name"] != TARGET_NAME}
    actual_unchanged = {entry["name"]: entry for entry in after_records if entry["name"] in expected_unchanged}
    if actual_unchanged != expected_unchanged:
        raise AssertionError(f"Other synthetic/history-style attachments changed: {actual_unchanged}")
    replacement = next(entry for entry in after_records if entry["name"] == REPLACEMENT_NAME)
    if replacement["sha256"] != REPLACEMENT_SHA256 or replacement["sizeInDatabase"] != len(REPLACEMENT_BYTES) or replacement["sizeOnDisk"] != len(REPLACEMENT_BYTES):
        raise AssertionError(f"Replacement attachment does not match the new synthetic bytes: {replacement}")

    operator_username = fixture["operatorUsername"]
    operator = get_user_model().objects.get(username=operator_username)
    logs = list(OperationLog.objects.filter(
        entity="crm.followup",
        object_id=str(follow_up_id),
        action_label="删除跟进附件",
        metadata__file_name=TARGET_NAME,
    ).select_related("operator"))
    if len(logs) != 1:
        raise AssertionError(f"Expected exactly one delete audit row for the target; got {len(logs)}.")
    log = logs[0]
    if log.operator_id != operator.pk or log.operator.username != operator_username:
        raise AssertionError("Delete audit row does not retain the authenticated synthetic operator.")
    if str(log.metadata.get("attachment_id")) != str(target_before["id"]):
        raise AssertionError(f"Delete audit attachment ID mismatch: {log.metadata}")
    if log.request_method != "DELETE" or f"/attachments/{target_before['id']}/" not in log.request_path:
        raise AssertionError(f"Delete audit HTTP request identity mismatch: {log.request_method} {log.request_path}")

    payload = {
        "phase": "after-delete-and-replacement",
        "runId": identity["runId"],
        "database": identity["database"],
        "mediaRoot": identity["mediaRoot"],
        "deletedTarget": {
            "id": target_before["id"],
            "name": TARGET_NAME,
            "databaseRowExists": False,
            "diskFileExists": False,
            "sha256BeforeDelete": target_before["sha256"],
        },
        "deleteAudit": {
            "id": log.pk,
            "operatorUsername": log.operator.username,
            "operatorDisplayName": fixture["operatorDisplayName"],
            "operatorIsSuperuser": operator.is_superuser,
            "actionLabel": log.action_label,
            "requestMethod": log.request_method,
            "requestPath": log.request_path,
            "metadata": log.metadata,
        },
        "remainingAttachments": after_records,
        "unmodifiedExistingAttachments": sorted(expected_unchanged),
        "replacement": replacement,
    }
    (evidence_dir / "after-delete-verification.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
