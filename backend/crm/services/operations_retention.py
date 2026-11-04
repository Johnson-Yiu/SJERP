"""Explicit receipt-driven retention; no directory-wide discovery or wildcard deletion."""
from datetime import datetime, timezone
from pathlib import Path
import re

from .operations_copy import digest


def prune_verified(root, *, owner_id, receipts, keep, minimum_age_seconds, now=None, execute=False):
    root = Path(root)
    if not re.fullmatch(r"[0-9a-f]{32}", owner_id):
        raise ValueError("Explicit backup ownership is required")
    if root.is_symlink() or not root.is_dir() or (root / ".sunjack-backup-owner").is_symlink():
        raise ValueError("Unsafe retention root")
    if (root / ".sunjack-backup-owner").read_text(encoding="ascii").strip() != owner_id:
        raise ValueError("Backup ownership mismatch")
    if type(keep) is not int or keep < 1 or type(minimum_age_seconds) is not int or minimum_age_seconds < 0:
        raise ValueError("Retention must preserve at least one backup")
    now = now or datetime.now(timezone.utc)
    verified = []
    names = set()
    for receipt in receipts:
        name = receipt["name"]
        if not re.fullmatch(r"backup-[0-9a-f]{32}\.gpg", name) or name in names:
            raise ValueError("Invalid or duplicate owned backup name")
        names.add(name)
        path = root / name
        expected = receipt["sha256"]
        created = datetime.fromisoformat(receipt["created_at"])
        if created.tzinfo is None or created > now or not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise ValueError("Invalid trusted receipt")
        if path.is_symlink() or not path.is_file() or digest(path) != expected:
            raise ValueError("Owned backup verification failed; nothing pruned")
        # Independent copy must exist outside the retention root. This does not
        # assert independent geographic or hardware failure domains.
        replica = Path(receipt["replica"])
        if not replica.is_absolute() or replica.is_symlink() or root.resolve() in replica.resolve().parents or replica.resolve() == path.resolve():
            raise ValueError("A separately located verified copy is required")
        if not replica.is_file() or digest(replica) != expected:
            raise ValueError("Independent copy verification failed; nothing pruned")
        verified.append((created, path, replica, expected))
    verified.sort(key=lambda entry: (entry[0], entry[1].name), reverse=True)
    candidates = [entry for entry in verified[keep:] if (now-entry[0]).total_seconds() >= minimum_age_seconds]
    removed = []
    if execute:
        for _, path, replica, expected in candidates:
            # Recheck immediately before each deletion; never touch replicas.
            if path.is_symlink() or replica.is_symlink() or digest(path) != expected or digest(replica) != expected:
                raise RuntimeError("Retention inputs changed; pruning stopped")
            path.unlink()
            removed.append(path.name)
    return {"candidates": [entry[1].name for entry in candidates], "removed": removed,
            "dry_run": not execute, "independent_failure_domain_verified": False}
