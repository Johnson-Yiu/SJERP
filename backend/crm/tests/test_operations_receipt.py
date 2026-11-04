import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from unittest import TestCase, mock
import zipfile

from crm.services.operations_copy import digest
from crm.services.operations_receipt import _openssl, public_key_fingerprint, restore_and_sign, verify_receipt


class ReceiptIssuanceTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.temp = tempfile.TemporaryDirectory(prefix="sunjack-receipt-test-")
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root = Path(cls.temp.name)
        cls.openssl = os.environ.get("OPS_TEST_OPENSSL") or shutil.which("openssl")
        if not cls.openssl:
            raise RuntimeError("OpenSSL is required for signed receipt tests")
        keys = cls.root / "keys"
        keys.mkdir()
        cls.private, cls.public = keys / "private.pem", keys / "public.pem"
        subprocess.run([cls.openssl, "genpkey", "-algorithm", "EC", "-pkeyopt", "ec_paramgen_curve:P-256", "-out", str(cls.private)], check=True, capture_output=True)
        cls.private.chmod(0o600)
        cls.public.write_bytes(_openssl(cls.openssl, "pkey", "-in", cls.private, "-pubout"))
        cls.fingerprint = public_key_fingerprint(cls.openssl, cls.public)

    def setUp(self):
        self.temp_case = tempfile.TemporaryDirectory(prefix="sunjack-receipt-case-")
        self.addCleanup(self.temp_case.cleanup)
        self.root_case = Path(self.temp_case.name)
        self.ciphertext = self.root_case / "synthetic.gpg"
        self.ciphertext.write_bytes(b"synthetic encrypted file")
        self.plaintext = self.root_case / "synthetic.zip"
        with zipfile.ZipFile(self.plaintext, "w") as archive:
            archive.writestr("manifest.json", json.dumps({"app_sha": "a" * 40, "system_identifier": "12345"}))
        self.service = mock.Mock(system_identifier="67890")
        self.service.restore.return_value = {"verified": True, "audit_truncate_rejected": True,
                                             "database": "sunjack_restore_" + "c" * 32}

    def call(self):
        def simulated_decrypt(_source, destination, **_kwargs):
            shutil.copyfile(self.plaintext, destination)
        with mock.patch("crm.services.operations_receipt.crypt_file", side_effect=simulated_decrypt):
            return restore_and_sign(self.service, encrypted_archive=self.ciphertext, encrypted_sha256=digest(self.ciphertext),
                plaintext_sha256=digest(self.plaintext), media_parent=self.root_case,
                gpg_executable="unused-simulated-gpg", encryption_key=b"x" * 32,
                openssl_executable=self.openssl, signing_key=self.private)

    def test_signs_only_after_verified_restore_and_real_signature_verifies(self):
        receipt, restored = self.call()
        self.assertTrue(restored["verified"])
        self.service.restore.assert_called_once()
        payload = verify_receipt(receipt, encrypted_sha256=digest(self.ciphertext), executable=self.openssl,
            public_key=self.public, pinned_fingerprint=self.fingerprint, max_age_seconds=3600)
        self.assertEqual(payload["source_system_identifier"], "12345")
        self.assertEqual(payload["target_system_identifier"], "67890")

    def test_failed_restore_never_signs_receipt(self):
        self.service.restore.side_effect = RuntimeError("synthetic restore failure")
        with mock.patch("crm.services.operations_receipt._openssl") as signer:
            with self.assertRaisesRegex(RuntimeError, "restore failure"):
                self.call()
            signer.assert_not_called()

    def test_unverified_audit_never_signs_receipt(self):
        self.service.restore.return_value["audit_truncate_rejected"] = False
        with mock.patch("crm.services.operations_receipt._openssl") as signer:
            with self.assertRaisesRegex(RuntimeError, "audit verification") as raised:
                self.call()
            signer.assert_not_called()
            self.assertTrue(any("target retained" in note.lower() for note in raised.exception.__notes__))

    def test_archive_changed_during_restore_never_gets_signed(self):
        def mutate_archive(**_kwargs):
            self.ciphertext.write_bytes(b"changed synthetic archive")
            return {"verified": True, "audit_truncate_rejected": True, "database": "sunjack_restore_" + "c" * 32}
        self.service.restore.side_effect = mutate_archive
        with mock.patch("crm.services.operations_receipt._openssl") as signer:
            with self.assertRaisesRegex(RuntimeError, "changed during restore"):
                self.call()
            signer.assert_not_called()

    def test_cleanup_failure_preserves_restore_error(self):
        scratch = self.root_case / "synthetic-staging"
        scratch.mkdir()
        temporary = mock.Mock(name=str(scratch))
        temporary.name = str(scratch)
        temporary.cleanup.side_effect = PermissionError("synthetic cleanup failure")
        self.service.restore.side_effect = RuntimeError("synthetic primary failure")
        with mock.patch("crm.services.operations_receipt.tempfile.TemporaryDirectory", return_value=temporary):
            with self.assertRaisesRegex(RuntimeError, "primary failure") as raised:
                self.call()
        self.assertTrue(any("Temporary plaintext cleanup failed: PermissionError" in note for note in raised.exception.__notes__))

    def test_cleanup_failure_after_restore_does_not_return_receipt(self):
        scratch = self.root_case / "synthetic-staging"
        scratch.mkdir()
        temporary = mock.Mock(name=str(scratch))
        temporary.name = str(scratch)
        temporary.cleanup.side_effect = PermissionError("synthetic cleanup failure")
        with mock.patch("crm.services.operations_receipt.tempfile.TemporaryDirectory", return_value=temporary):
            with self.assertRaises(PermissionError) as raised:
                self.call()
        self.assertTrue(any("restored target retained" in note.lower() for note in raised.exception.__notes__))
