from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
from unittest import TestCase
import uuid

from crm.services.operations_copy import digest
from crm.services.operations_retention import prune_verified


class RetentionTests(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="sunjack-retention-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "owned"
        self.root.mkdir()
        self.owner = uuid.uuid4().hex
        (self.root / ".sunjack-backup-owner").write_text(self.owner, encoding="ascii")
        self.now = datetime.now(timezone.utc)
        self.receipts = []
        for age in (1, 2, 3):
            path = self.root / ("backup-" + uuid.uuid4().hex + ".gpg")
            path.write_bytes(b"SYNTHETIC-CIPHERTEXT" + bytes([age]))
            replica = Path(self.temp.name) / path.name
            replica.write_bytes(path.read_bytes())
            self.receipts.append({"name": path.name, "sha256": digest(path), "replica": str(replica),
                                  "created_at": (self.now-timedelta(days=age)).isoformat()})

    def invoke(self, **kwargs):
        return prune_verified(self.root, owner_id=self.owner, receipts=self.receipts,
                              keep=1, minimum_age_seconds=86400, now=self.now, **kwargs)

    def test_default_dry_run_then_prune_preserves_newest_and_all_replicas(self):
        self.assertEqual(len(self.invoke()["candidates"]), 2)
        self.assertTrue(all((self.root / r["name"]).exists() for r in self.receipts))
        result = self.invoke(execute=True)
        self.assertEqual(len(result["removed"]), 2)
        self.assertTrue((self.root / self.receipts[0]["name"]).exists())
        self.assertTrue(all(Path(r["replica"]).exists() for r in self.receipts))

    def test_missing_or_corrupt_replica_refuses_before_any_deletion(self):
        Path(self.receipts[-1]["replica"]).write_bytes(b"CORRUPT")
        with self.assertRaises(ValueError):
            self.invoke(execute=True)
        self.assertTrue(all((self.root / r["name"]).exists() for r in self.receipts))

    def test_unknown_files_and_wrong_owner_not_deleted(self):
        unknown = self.root / "unknown-business-file"
        unknown.write_bytes(b"PRESERVE")
        self.owner = uuid.uuid4().hex
        with self.assertRaises(ValueError):
            self.invoke(execute=True)
        self.assertEqual(unknown.read_bytes(), b"PRESERVE")

    def test_single_backup_never_pruned(self):
        self.receipts = self.receipts[:1]
        self.assertEqual(self.invoke(execute=True)["removed"], [])
