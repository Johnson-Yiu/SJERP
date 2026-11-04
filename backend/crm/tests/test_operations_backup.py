import contextlib
import io
import json
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase, mock

from crm.services.operations_copy import digest
import operations_backup


class EncryptedBackupPublicationTests(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="sunjack-encrypted-backup-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.destination_dir = self.root / "backups"
        self.destination_dir.mkdir()
        self.media_root = self.root / "media"
        self.media_root.mkdir()
        self.key_dir = self.root / "separate-key-store"
        self.key_dir.mkdir()
        self.key_file = self.key_dir / "backup.key"
        self.key_file.write_bytes(b"k" * 32)
        self.tool_dir = self.root / "tools"
        self.tool_dir.mkdir()
        self.executable = self.tool_dir / "gpg"
        self.executable.touch()
        self.destination = self.destination_dir / "backup-synthetic.gpg"
        self.config_path = self.root / "config.json"
        self.config_path.write_text(json.dumps({
            "connection": {"host": "127.0.0.1", "port": 5432, "user": "synthetic", "dbname": "synthetic"},
            "pg_bin": str(self.tool_dir),
            "expected_database": "synthetic",
            "expected_system_identifier": "1234",
            "app_sha": "a" * 40,
            "media_root": str(self.media_root),
            "destination": str(self.destination),
            "encryption": {"key_file": str(self.key_file), "executable": str(self.executable)},
        }), encoding="utf-8")
        self.plaintext = b"synthetic database and private media archive"
        self.service = mock.Mock()

        def backup(*, destination, **kwargs):
            path = Path(destination)
            path.write_bytes(self.plaintext)
            return {"sha256": digest(path), "bytes": len(self.plaintext)}

        self.service.backup.side_effect = backup

    def invoke(self, crypto_side_effect):
        stdout = io.StringIO()
        with mock.patch.object(sys, "argv", ["operations_backup.py", "backup", "--config", str(self.config_path)]), \
             mock.patch("crm.services.operations_postgres.MaintenanceBackup", return_value=self.service), \
             mock.patch("crm.services.operations_crypto.crypt_file", side_effect=crypto_side_effect), \
             contextlib.redirect_stdout(stdout):
            status = operations_backup.main()
        return status, json.loads(stdout.getvalue())

    def test_roundtrip_decryption_failure_does_not_publish_or_leave_ciphertext(self):
        calls = []

        def crypto(source, destination, *, decrypt=False, **kwargs):
            calls.append((Path(source), Path(destination), decrypt))
            if decrypt:
                raise RuntimeError("injected decrypt failure")
            Path(destination).write_bytes(b"synthetic ciphertext")
            return {"sha256": "b" * 64, "bytes": 20, "operation": "encrypt"}

        status, result = self.invoke(crypto)
        self.assertEqual(status, 1)
        self.assertEqual(result["status"], "FAILED")
        self.assertFalse(self.destination.exists())
        self.assertEqual(list(self.destination_dir.iterdir()), [])
        self.assertEqual(self.service.backup.call_count, 1, result)
        self.assertEqual([call[2] for call in calls], [False, True])

    def test_roundtrip_digest_mismatch_does_not_publish_or_leave_ciphertext(self):
        def crypto(source, destination, *, decrypt=False, **kwargs):
            if decrypt:
                Path(destination).write_bytes(b"wrong plaintext")
                raise ValueError("Decrypted plaintext digest mismatch")
            Path(destination).write_bytes(b"synthetic ciphertext")
            return {"sha256": "b" * 64, "bytes": 20, "operation": "encrypt"}

        status, result = self.invoke(crypto)
        self.assertEqual(status, 1)
        self.assertEqual(result["status"], "FAILED")
        self.assertFalse(self.destination.exists())
        self.assertEqual(list(self.destination_dir.iterdir()), [])

    def test_existing_final_destination_is_preserved_and_backup_is_not_started(self):
        self.destination.write_bytes(b"prior verified archive")
        status, result = self.invoke(mock.Mock(side_effect=AssertionError("crypto must not run")))
        self.assertEqual(status, 1)
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(self.destination.read_bytes(), b"prior verified archive")
        self.service.backup.assert_not_called()

    def test_destination_created_during_publish_is_not_overwritten(self):
        def crypto(source, destination, *, decrypt=False, **kwargs):
            if decrypt:
                Path(destination).write_bytes(self.plaintext)
                return {"sha256": digest(destination), "bytes": len(self.plaintext), "operation": "decrypt"}
            Path(destination).write_bytes(b"verified synthetic ciphertext")
            return {"sha256": digest(destination), "bytes": Path(destination).stat().st_size, "operation": "encrypt"}

        real_link = operations_backup.os.link

        def create_competing_destination(source, destination, *, follow_symlinks=True):
            Path(destination).write_bytes(b"concurrent destination")
            return real_link(source, destination, follow_symlinks=follow_symlinks)

        with mock.patch("operations_backup.os.link", side_effect=create_competing_destination):
            status, result = self.invoke(crypto)
        self.assertEqual(status, 1)
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(self.destination.read_bytes(), b"concurrent destination")
        self.assertEqual(list(self.destination_dir.iterdir()), [self.destination])

    def test_collision_with_unowned_staging_name_is_preserved(self):
        token = "f" * 32
        staging = self.destination_dir / f".sunjack-encrypted-{token}.partial"
        staging.write_bytes(b"unowned pre-existing ciphertext")
        with mock.patch("operations_backup.uuid.uuid4", return_value=SimpleNamespace(hex=token)):
            status, result = self.invoke(mock.Mock(side_effect=FileExistsError("exclusive staging collision")))
        self.assertEqual(status, 1)
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(staging.read_bytes(), b"unowned pre-existing ciphertext")
        self.assertFalse(self.destination.exists())

    def test_verified_ciphertext_is_published_and_staging_name_removed(self):
        def crypto(source, destination, *, decrypt=False, **kwargs):
            if decrypt:
                Path(destination).write_bytes(self.plaintext)
                return {"sha256": digest(destination), "bytes": len(self.plaintext), "operation": "decrypt"}
            Path(destination).write_bytes(b"verified synthetic ciphertext")
            return {"sha256": digest(destination), "bytes": Path(destination).stat().st_size, "operation": "encrypt"}

        status, result = self.invoke(crypto)
        self.assertEqual(status, 0)
        self.assertEqual(result["status"], "VERIFIED")
        self.assertTrue(result["encryption_roundtrip_verified"])
        self.assertEqual(self.destination.read_bytes(), b"verified synthetic ciphertext")
        self.assertEqual(list(self.destination_dir.iterdir()), [self.destination])
