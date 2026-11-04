from pathlib import Path
import tempfile
from unittest import TestCase, mock
import stat
import zipfile
from crm.services.operations_copy import digest

from crm.services.operations_postgres import MaintenanceBackup, publish_archive


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

    def test_archive_symlink_refused_before_any_database_operation(self):
        with tempfile.TemporaryDirectory(prefix="sunjack-restore-link-") as folder:
            root = Path(folder)
            source = root / "unsafe.zip"
            member = zipfile.ZipInfo("media/linked")
            member.create_system = 3
            member.external_attr = (stat.S_IFLNK | 0o777) << 16
            with zipfile.ZipFile(source, "w") as archive:
                archive.writestr(member, "../../must-not-exist")
            with mock.patch.object(self.service, "connect") as connect:
                with self.assertRaisesRegex(ValueError, "Archive links"):
                    self.service.restore(archive=source, expected_sha256=digest(source), media_parent=root)
                connect.assert_not_called()

    def test_failed_backup_never_publishes_success_filename(self):
        with tempfile.TemporaryDirectory(prefix="sunjack-publication-") as folder:
            destination = Path(folder) / "backup.zip"
            with self.assertRaisesRegex(RuntimeError, "synthetic commit failure"):
                with publish_archive(destination) as stream:
                    stream.write(b"synthetic archive")
                    self.assertFalse(destination.exists())
                    raise RuntimeError("synthetic commit failure")
            self.assertFalse(destination.exists())
            self.assertEqual(list(Path(folder).iterdir()), [])

    def test_success_publication_never_overwrites_existing_backup(self):
        with tempfile.TemporaryDirectory(prefix="sunjack-publication-") as folder:
            destination = Path(folder) / "backup.zip"
            destination.write_bytes(b"preserve")
            with self.assertRaises(FileExistsError):
                with publish_archive(destination) as stream:
                    stream.write(b"new archive")
            self.assertEqual(destination.read_bytes(), b"preserve")
            self.assertEqual(list(Path(folder).iterdir()), [destination])
