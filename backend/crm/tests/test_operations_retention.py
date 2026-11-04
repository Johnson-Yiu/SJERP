from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
from unittest import TestCase
import uuid
import base64
import os
import shutil
import subprocess

from crm.services.operations_copy import digest
from crm.services.operations_retention import prune_verified
from crm.services.operations_receipt import _canonical, _openssl, public_key_fingerprint
from crm.services.operations_monitor import check_backup_freshness


class RetentionTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.keydir = tempfile.TemporaryDirectory(prefix="sunjack-receipt-test-key-")
        cls.addClassCleanup(cls.keydir.cleanup)
        cls.openssl = os.environ.get("OPS_TEST_OPENSSL") or shutil.which("openssl")
        if not cls.openssl:
            raise RuntimeError("OpenSSL is required for signed receipt tests")
        cls.private = Path(cls.keydir.name) / "private.pem"
        cls.public = Path(cls.keydir.name) / "public.pem"
        subprocess.run([cls.openssl, "genpkey", "-algorithm", "EC", "-pkeyopt", "ec_paramgen_curve:P-256", "-out", str(cls.private)], check=True, capture_output=True)
        cls.private.chmod(0o600)
        cls.public.write_bytes(_openssl(cls.openssl, "pkey", "-in", cls.private, "-pubout"))
        cls.verification = {"executable": cls.openssl, "public_key": str(cls.public),
                            "pinned_fingerprint": public_key_fingerprint(cls.openssl, cls.public), "max_age_seconds": 86400}

    def signed(self, ciphertext_sha, *, archive_mtime_ns=None, verified_at=None):
        payload = {"version": 1, "cipher_sha256": ciphertext_sha, "plaintext_sha256": "b" * 64,
                   "app_sha": "a" * 40, "source_system_identifier": "12345", "target_system_identifier": "67890",
                   "restored_database": "sunjack_restore_" + "c" * 32,
                   "archive_mtime_ns": archive_mtime_ns or self.receipts[0]["restore_receipt"]["payload"]["archive_mtime_ns"],
                   "verified_at": (verified_at or self.now).isoformat(), "audit_truncate_rejected": True}
        signature = _openssl(self.openssl, "dgst", "-sha256", "-sign", self.private, data=_canonical(payload))
        return {"payload": payload, "signature": base64.b64encode(signature).decode("ascii")}

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="sunjack-retention-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "owned"
        self.root.mkdir(mode=0o700)
        self.owner = uuid.uuid4().hex
        (self.root / ".sunjack-backup-owner").write_text(self.owner, encoding="ascii")
        (self.root / ".sunjack-backup-owner").chmod(0o600)
        self.now = datetime.now(timezone.utc)
        self.receipts = []
        for age in (1, 2, 3):
            path = self.root / ("backup-" + uuid.uuid4().hex + ".gpg")
            path.write_bytes(b"SYNTHETIC-CIPHERTEXT" + bytes([age]))
            timestamp = (self.now-timedelta(days=age)).timestamp()
            os.utime(path, (timestamp, timestamp))
            mtime_ns = path.stat().st_mtime_ns
            replica = Path(self.temp.name) / path.name
            replica.write_bytes(path.read_bytes())
            self.receipts.append({"name": path.name, "sha256": digest(path), "restore_verified_sha256": digest(path), "replica": str(replica),
                                  "restore_receipt": self.signed(digest(path), archive_mtime_ns=mtime_ns),
                                  "created_at": datetime.fromtimestamp(mtime_ns / 1_000_000_000, timezone.utc).isoformat()})

    def invoke(self, **kwargs):
        return prune_verified(self.root, owner_id=self.owner, receipts=self.receipts,
                              keep=1, minimum_age_seconds=86400, now=self.now, receipt_verification=self.verification, **kwargs)

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

    def test_digest_without_restore_verification_never_authorizes_pruning(self):
        self.receipts[0].pop("restore_receipt")
        with self.assertRaises(ValueError):
            self.invoke(execute=True)
        self.assertTrue(all((self.root / r["name"]).exists() for r in self.receipts))

    def test_self_declared_digest_does_not_prove_a_restore(self):
        # These files and their declared digests match, but no decryption or
        # database restore ever happened.  No backup may be removed.
        for receipt in self.receipts:
            receipt.pop("restore_receipt")
        with self.assertRaises(ValueError):
            self.invoke(execute=True)
        self.assertTrue(all((self.root / r["name"]).exists() for r in self.receipts))

    def test_tampered_wrong_archive_expired_and_untrusted_key_refused(self):
        valid = self.receipts[0]["restore_receipt"]
        cases = []
        changed = {"payload": {**valid["payload"], "app_sha": "d" * 40}, "signature": valid["signature"]}
        cases.append(changed)
        cases.append(self.signed("0" * 64))
        cases.append(self.signed(self.receipts[0]["sha256"], verified_at=self.now-timedelta(days=2)))
        cases.append({"payload": valid["payload"], "signature": base64.b64encode(b"x" * 64).decode()})
        cases.append({"payload": {**valid["payload"], "archive_mtime_ns": 1}, "signature": valid["signature"]})
        for receipt in cases:
            with self.subTest(receipt=receipt):
                self.receipts[0]["restore_receipt"] = receipt
                with self.assertRaises(ValueError):
                    self.invoke(execute=True)
                self.assertTrue(all((self.root / r["name"]).exists() for r in self.receipts))

    def test_monitor_detects_missed_schedule_and_does_not_accept_tampering(self):
        record = self.receipts[0]
        verification = {**self.verification, "max_age_seconds": 7 * 86400}
        options = {"archive": self.root / record["name"], "restore_receipt": record["restore_receipt"],
                   "receipt_verification": verification, "maximum_backup_age_seconds": 2 * 86400}
        self.assertEqual(check_backup_freshness(**options, now=self.now)["status"], "OK")
        with self.assertRaisesRegex(RuntimeError, "freshness"):
            check_backup_freshness(**options, now=self.now+timedelta(days=2))
        options["restore_receipt"] = self.receipts[1]["restore_receipt"]
        with self.assertRaises(ValueError):
            check_backup_freshness(**options, now=self.now)

    def test_receipt_signed_by_another_real_key_is_rejected(self):
        attacker = self.root / "synthetic-attacker.pem"
        subprocess.run([self.openssl, "genpkey", "-algorithm", "EC", "-pkeyopt", "ec_paramgen_curve:P-256", "-out", str(attacker)], check=True, capture_output=True)
        payload = self.receipts[0]["restore_receipt"]["payload"]
        signature = _openssl(self.openssl, "dgst", "-sha256", "-sign", attacker, data=_canonical(payload))
        self.receipts[0]["restore_receipt"] = {"payload": payload, "signature": base64.b64encode(signature).decode("ascii")}
        with self.assertRaises(ValueError):
            self.invoke(execute=True)
        self.assertTrue(all((self.root / r["name"]).exists() for r in self.receipts))
