"""Read-only missed-backup check based on independently signed recovery evidence."""
from datetime import datetime, timezone
from pathlib import Path

from .operations_copy import digest
from .operations_receipt import verify_receipt


def check_backup_freshness(*, archive, restore_receipt, receipt_verification, maximum_backup_age_seconds, now=None):
    if type(maximum_backup_age_seconds) is not int or maximum_backup_age_seconds <= 0:
        raise ValueError("A positive backup freshness threshold is required")
    path = Path(archive)
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise ValueError("A specific regular backup archive is required")
    now = now or datetime.now(timezone.utc)
    sha = digest(path)
    payload = verify_receipt(restore_receipt, encrypted_sha256=sha, now=now, **receipt_verification)
    if path.stat().st_mtime_ns != payload["archive_mtime_ns"]:
        raise ValueError("Backup timestamp changed since verified restore")
    observed = datetime.fromtimestamp(payload["archive_mtime_ns"] / 1_000_000_000, timezone.utc)
    age = (now - observed).total_seconds()
    if age < 0 or age > maximum_backup_age_seconds:
        raise RuntimeError("Backup is missing its expected freshness window")
    return {"status": "OK", "archive_sha256": sha, "age_seconds": int(age),
            "scope": "signed restore evidence; external alert delivery not verified"}
