"""Reproduce the fixed baseline's self-declared receipt flaw using synthetic files."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import tempfile
import types
import uuid

from crm.services.operations_copy import digest

baseline = "8087f2c68b19a302a25e814ec8ce6113d91d4750"
source = subprocess.run(["git", "show", baseline + ":backend/crm/services/operations_retention.py"],
                        capture_output=True, text=True, check=True).stdout
module = types.ModuleType("crm.services.synthetic_legacy_retention")
module.__package__ = "crm.services"
exec(compile(source, "synthetic_baseline_operations_retention.py", "exec"), module.__dict__)
with tempfile.TemporaryDirectory(prefix="sunjack-legacy-receipt-repro-") as temporary:
    root = Path(temporary) / "owned"
    root.mkdir()
    owner = uuid.uuid4().hex
    (root / ".sunjack-backup-owner").write_text(owner, encoding="ascii")
    now = datetime.now(timezone.utc)
    receipts = []
    for age in (1, 2, 3):
        source_file = root / ("backup-" + uuid.uuid4().hex + ".gpg")
        source_file.write_bytes(b"SYNTHETIC NO RESTORE EVER OCCURRED" + bytes([age]))
        replica = Path(temporary) / source_file.name
        replica.write_bytes(source_file.read_bytes())
        sha = digest(source_file)
        receipts.append({"name": source_file.name, "sha256": sha, "restore_verified_sha256": sha,
                         "created_at": (now-timedelta(days=age)).isoformat(), "replica": str(replica)})
    result = module.prune_verified(root, owner_id=owner, receipts=receipts, keep=1,
                                   minimum_age_seconds=86400, now=now, execute=True)
    if len(result["removed"]) != 2:
        raise AssertionError("Baseline behavior did not reproduce")
    print(json.dumps({"baseline": baseline, "synthetic_files_only": True,
                      "real_restore_performed": False, "self_declared_digests_accepted": True,
                      "owned_synthetic_backups_deleted": len(result["removed"])}))
