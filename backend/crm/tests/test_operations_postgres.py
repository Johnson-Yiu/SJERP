from pathlib import Path
import tempfile
from unittest import TestCase, mock

from crm.services.operations_postgres import MaintenanceBackup


class MaintenanceSafetyTests(TestCase):
    def setUp(self):
        self.service = MaintenanceBackup(connection_options={"host": "127.0.0.1", "port": 9999, "user": "synthetic", "dbname": "synthetic"}, pg_bin="/explicit/tools", expected_database="synthetic",
                                         expected_system_identifier="1234", app_sha="a" * 40)

    def test_unproved_media_fence_refuses_before_database_connection(self):
        with tempfile.TemporaryDirectory(prefix="sunjack-backup-rejection-") as folder:
            root = Path(folder)
            with mock.patch.object(self.service, "connect") as connect:
                with self.assertRaises((RuntimeError, FileNotFoundError)):
                    self.service.backup(media_root=root, destination=root / "must-not-exist")
                connect.assert_not_called()
                self.assertFalse((root / "must-not-exist").exists())

    def test_restore_wrong_digest_refuses_before_database_connection(self):
        with tempfile.TemporaryDirectory(prefix="sunjack-restore-rejection-") as folder:
            root = Path(folder)
            source = root / "invalid.zip"
            source.write_bytes(b"SYNTHETIC-NOT-A-BACKUP")
            with mock.patch.object(self.service, "connect") as connect:
                with self.assertRaises(ValueError):
                    self.service.restore(archive=source, expected_sha256="0" * 64, media_parent=root)
                connect.assert_not_called()
                self.assertEqual(list(root.iterdir()), [source])

    def test_wrong_instance_identity_refused(self):
        connection = mock.Mock()
        connection.execute.return_value.fetchone.return_value = ("synthetic", "9999", 170011)
        with self.assertRaisesRegex(RuntimeError, "identity"):
            self.service.identity(connection)
