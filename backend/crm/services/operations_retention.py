"""Explicit receipt-driven retention; no directory-wide discovery or wildcard deletion."""
from datetime import datetime, timezone
import os
from pathlib import Path
import re

from .operations_copy import digest
from .operations_receipt import verify_receipt


def prune_verified(root, *, owner_id, receipts, keep, minimum_age_seconds, receipt_verification=None, now=None, execute=False):
    root = Path(root)
    if not re.fullmatch(r"[0-9a-f]{32}", owner_id):
        raise ValueError("Explicit backup ownership is required")
    if not root.is_absolute() or any(path.is_symlink() for path in (root, *root.parents)) or not root.is_dir() or (root / ".sunjack-backup-owner").is_symlink():
        raise ValueError("Unsafe retention root")
    if os.name == "posix":
        root_info = root.stat()
        marker_info = (root / ".sunjack-backup-owner").stat()
        if root_info.st_uid != os.geteuid() or marker_info.st_uid != os.geteuid() or root_info.st_mode & 0o022 or marker_info.st_mode & 0o022:
            raise ValueError("Retention directory and owner marker must be exclusively controlled")
    if (root / ".sunjack-backup-owner").read_text(encoding="ascii").strip() != owner_id:
        raise ValueError("Backup ownership mismatch")
    if type(keep) is not int or keep < 1 or type(minimum_age_seconds) is not int or minimum_age_seconds < 0:
        raise ValueError("Retention must preserve at least one backup")
    now = now or datetime.now(timezone.utc)
    if not isinstance(receipt_verification, dict) or set(receipt_verification) != {"executable", "public_key", "pinned_fingerprint", "max_age_seconds"}:
        raise ValueError("Independently configured receipt verification is required")
    verified = []
    names = set()
    for receipt in receipts:
        name = receipt["name"]
        if not re.fullmatch(r"backup-[0-9a-f]{32}\.gpg", name) or name in names:
            raise ValueError("Invalid or duplicate owned backup name")
        names.add(name)
        path = root / name
        expected = receipt["sha256"]
        payload = verify_receipt(receipt.get("restore_receipt"), encrypted_sha256=expected, now=now, **receipt_verification)
        created = datetime.fromisoformat(receipt["created_at"])
        if created.tzinfo is None or created > now or not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise ValueError("Invalid trusted receipt")
        if path.is_symlink() or not path.is_file() or digest(path) != expected:
            raise ValueError("Owned backup verification failed; nothing pruned")
        observed_time = datetime.fromtimestamp(payload["archive_mtime_ns"] / 1_000_000_000, timezone.utc)
        if path.stat().st_mtime_ns != payload["archive_mtime_ns"] or created != observed_time:
            raise ValueError("Archive timestamp differs from signed restore evidence")
        # Independent copy must exist outside the retention root. This does not
        # assert independent geographic or hardware failure domains.
        replica = Path(receipt["replica"])
        if not replica.is_absolute() or replica.is_symlink() or root.resolve() in replica.resolve().parents or replica.resolve() == path.resolve():
            raise ValueError("A separately located verified copy is required")
        if not replica.is_file() or digest(replica) != expected:
            raise ValueError("Independent copy verification failed; nothing pruned")
        verified.append((created, path, replica, expected, receipt["restore_receipt"]))
    verified.sort(key=lambda entry: (entry[0], entry[1].name), reverse=True)
    candidates = [entry for entry in verified[keep:] if (now-entry[0]).total_seconds() >= minimum_age_seconds]
    removed = []
    if execute:
        for _, path, replica, expected, restore_receipt in candidates:
            # Recheck immediately before each deletion; never touch replicas.
            if path.is_symlink() or replica.is_symlink() or digest(path) != expected or digest(replica) != expected:
                raise RuntimeError("Retention inputs changed; pruning stopped")
            payload = verify_receipt(restore_receipt, encrypted_sha256=expected, now=now, **receipt_verification)
            if path.stat().st_mtime_ns != payload["archive_mtime_ns"]:
                raise RuntimeError("Archive timestamp changed; pruning stopped")
            path.unlink()
            removed.append(path.name)
    return {"candidates": [entry[1].name for entry in candidates], "removed": removed,
            "dry_run": not execute, "independent_failure_domain_verified": False}
