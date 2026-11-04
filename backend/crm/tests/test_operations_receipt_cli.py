import contextlib
import io
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest import TestCase, mock

import operations_backup


class ReceiptCliTests(TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="sunjack-receipt-cli-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.key = self.root / "synthetic-key"
        self.key.write_bytes(b"synthetic-encryption-key-for-test")
        self.receipt = self.root / "receipt.json"
        self.config = self.root / "config.json"
        self.config.write_text(json.dumps({
            "connection": {"host": "127.0.0.1", "port": 9999, "user": "synthetic", "dbname": "synthetic"},
            "pg_bin": str(self.root), "expected_database": "synthetic", "expected_system_identifier": "1234", "app_sha": "a" * 40,
            "archive": str(self.root / "synthetic.gpg"), "expected_sha256": "b" * 64, "encrypted_sha256": "c" * 64,
            "media_parent": str(self.root), "encryption": {"key_file": str(self.key), "executable": str(self.root / "gpg")},
            "receipt_signing": {"private_key": str(self.root / "signing-key"), "executable": str(self.root / "openssl")},
            "receipt_output": str(self.receipt),
        }), encoding="utf-8")

    def invoke(self, effect):
        stdout = io.StringIO()
        with mock.patch.object(sys, "argv", ["operations_backup.py", "restore-encrypted-verify", "--config", str(self.config)]), \
             mock.patch("crm.services.operations_postgres.MaintenanceBackup"), \
             mock.patch("crm.services.operations_receipt.restore_and_sign", side_effect=effect) as restore, \
             contextlib.redirect_stdout(stdout):
            status = operations_backup.main()
        return status, json.loads(stdout.getvalue()), restore

    def test_only_successful_restore_publishes_receipt(self):
        signed = {"payload": {"synthetic": True}, "signature": "synthetic-signature"}
        status, result, restore = self.invoke(lambda *_args, **_kwargs: (signed, {"database": "sunjack_restore_synthetic", "verified": True}))
        self.assertEqual(status, 0)
        self.assertEqual(result["status"], "VERIFIED")
        self.assertEqual(json.loads(self.receipt.read_text(encoding="utf-8")), signed)
        if os.name == "posix":
            self.assertEqual(stat.S_IMODE(self.receipt.stat().st_mode), 0o600)
        restore.assert_called_once()

    @unittest.skipUnless(os.name == "posix", "POSIX group publication requires Linux/POSIX")
    def test_configured_group_receipt_is_0640_and_uses_the_current_group(self):
        import grp

        group = grp.getgrgid(os.getegid()).gr_name
        config = json.loads(self.config.read_text(encoding="utf-8"))
        config["receipt_read_group"] = group
        self.config.write_text(json.dumps(config), encoding="utf-8")
        signed = {"payload": {"synthetic": True}, "signature": "synthetic-signature"}

        status, result, restore = self.invoke(lambda *_args, **_kwargs: (signed, {"database": "sunjack_restore_synthetic", "verified": True}))

        info = self.receipt.stat()
        self.assertEqual(status, 0)
        self.assertEqual(result["status"], "VERIFIED")
        self.assertEqual(info.st_gid, os.getegid())
        self.assertEqual(stat.S_IMODE(info.st_mode), 0o640)
        self.assertEqual(json.loads(self.receipt.read_text(encoding="utf-8")), signed)
        restore.assert_called_once()

    def test_unknown_or_unsupported_receipt_group_fails_before_restore(self):
        config = json.loads(self.config.read_text(encoding="utf-8"))
        config["receipt_read_group"] = "sunjack-no-such-receipt-group-" + "f" * 16
        self.config.write_text(json.dumps(config), encoding="utf-8")

        status, result, restore = self.invoke(AssertionError("invalid group must fail before restore"))

        self.assertEqual(status, 1)
        self.assertEqual(result["status"], "FAILED")
        self.assertFalse(self.receipt.exists())
        self.assertEqual(list(self.root.glob(".sunjack-receipt-*.partial")), [])
        restore.assert_not_called()

    @unittest.skipUnless(os.name == "posix", "POSIX descriptor permission failure requires Linux/POSIX")
    def test_group_permission_failure_never_publishes_receipt(self):
        import grp

        config = json.loads(self.config.read_text(encoding="utf-8"))
        config["receipt_read_group"] = grp.getgrgid(os.getegid()).gr_name
        self.config.write_text(json.dumps(config), encoding="utf-8")
        signed = {"payload": {"synthetic": True}, "signature": "synthetic-signature"}
        with mock.patch("crm.services.operations_receipt.os.fchmod", side_effect=PermissionError("synthetic mode failure")), \
             mock.patch("crm.services.operations_receipt.os.link") as link:
            status, result, restore = self.invoke(lambda *_args, **_kwargs: (signed, {"database": "sunjack_restore_synthetic", "verified": True}))

        self.assertEqual(status, 1)
        self.assertEqual(result["status"], "FAILED")
        self.assertFalse(self.receipt.exists())
        self.assertEqual(list(self.root.glob(".sunjack-receipt-*.partial")), [])
        link.assert_not_called()
        restore.assert_called_once()

    def test_link_publication_failure_cleans_staging_and_does_not_publish(self):
        signed = {"payload": {"synthetic": True}, "signature": "synthetic-signature"}
        with mock.patch("crm.services.operations_receipt.os.link", side_effect=OSError("synthetic publication failure")):
            status, result, restore = self.invoke(lambda *_args, **_kwargs: (signed, {"database": "sunjack_restore_synthetic", "verified": True}))

        self.assertEqual(status, 1)
        self.assertEqual(result["status"], "FAILED")
        self.assertFalse(self.receipt.exists())
        self.assertEqual(list(self.root.glob(".sunjack-receipt-*.partial")), [])
        restore.assert_called_once()

    def test_failed_restore_and_existing_receipt_never_overwrite(self):
        status, result, restore = self.invoke(RuntimeError("synthetic recovery failure"))
        self.assertEqual(status, 1)
        self.assertEqual(result["status"], "FAILED")
        self.assertFalse(self.receipt.exists())
        self.receipt.write_bytes(b"existing")
        status, result, restore = self.invoke(AssertionError("must not restore"))
        self.assertEqual(status, 1)
        self.assertEqual(self.receipt.read_bytes(), b"existing")
        restore.assert_not_called()
