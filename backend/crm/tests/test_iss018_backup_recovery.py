import json
import os
import sqlite3
import stat
import unittest
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from crm.services.backup_recovery import (
    BackupRecoveryError,
    create_consistent_backup,
    ensure_secure_backup_directory,
    prune_backup_archives,
    restore_consistent_backup,
)
from crm.services.private_media import build_private_media_manifest, compare_private_media_manifest


class ISS018BackupRecoveryTests(SimpleTestCase):
    def _make_fixture(self, root):
        root = Path(root)
        database = root / "source.sqlite3"
        media = root / "media"
        media.mkdir()
        (media / "followups").mkdir()
        (media / "followups" / "invoice.pdf").write_bytes(b"invoice-private-bytes")
        (media / "sku.png").write_bytes(b"sku-image-private-bytes")
        connection = sqlite3.connect(database)
        try:
            connection.executescript(
                """
                CREATE TABLE orders (id INTEGER PRIMARY KEY, order_no TEXT, total_amount DECIMAL);
                CREATE TABLE inventory (id INTEGER PRIMARY KEY, sku TEXT, quantity DECIMAL);
                CREATE TABLE attachments (id INTEGER PRIMARY KEY, order_id INTEGER, path TEXT);
                INSERT INTO orders VALUES (1, 'SO-ISS018-001', '5000.00');
                INSERT INTO inventory VALUES (1, 'SKU-ISS018-001', '42.00');
                INSERT INTO attachments VALUES (1, 1, 'followups/invoice.pdf');
                """
            )
            connection.commit()
        finally:
            connection.close()
        return database, media

    def _make_archive(self, root, backup_id="test"):
        database, media = self._make_fixture(root)
        return Path(
            create_consistent_backup(
                database=database,
                media_root=media,
                output_dir=Path(root) / "backup",
                backup_id=backup_id,
                quiesced=True,
            )["archive"]
        )

    def test_backup_requires_an_explicit_write_quiescence_confirmation(self):
        with TemporaryDirectory() as root:
            database, media = self._make_fixture(root)
            with self.assertRaisesRegex(BackupRecoveryError, "quiesced"):
                create_consistent_backup(database=database, media_root=media, output_dir=Path(root) / "backup")

    def test_single_archive_restore_preserves_rows_amount_inventory_and_media_relation(self):
        with TemporaryDirectory() as root:
            database, media = self._make_fixture(root)
            output = Path(root) / "backup"
            result = create_consistent_backup(
                database=database,
                media_root=media,
                output_dir=output,
                backup_id="iss018-drill",
                quiesced=True,
            )
            archive = Path(result["archive"])
            self.assertTrue(archive.is_file())
            with zipfile.ZipFile(archive) as source:
                names = set(source.namelist())
                self.assertIn("database.sqlite3", names)
                self.assertIn("media/followups/invoice.pdf", names)
                self.assertIn("manifest.json", names)
                manifest = json.loads(source.read("manifest.json"))
            self.assertEqual(manifest["consistency"]["method"], "application-quiesced-sqlite-backup-and-media-archive")
            self.assertEqual(manifest["media"], build_private_media_manifest(media))

            restored = Path(root) / "restored"
            restore = restore_consistent_backup(archive=archive, target_dir=restored)
            self.assertEqual(restore["status"], "PASS")
            connection = sqlite3.connect(restored / "database.sqlite3")
            try:
                self.assertEqual(connection.execute("SELECT total_amount FROM orders WHERE id=1").fetchone()[0], 5000)
                self.assertEqual(connection.execute("SELECT quantity FROM inventory WHERE id=1").fetchone()[0], 42)
                path = connection.execute("SELECT path FROM attachments WHERE id=1").fetchone()[0]
            finally:
                connection.close()
            self.assertEqual(path, "followups/invoice.pdf")
            self.assertTrue((restored / "media" / path).is_file())
            self.assertEqual(compare_private_media_manifest(manifest["media"], restored / "media"), [])
            result_report = Path(root) / ".restored.restore-result.json"
            self.assertEqual(json.loads(result_report.read_text())["status"], "PASS")

    def test_media_change_during_copy_discards_archive(self):
        with TemporaryDirectory() as root:
            database, media = self._make_fixture(root)
            from crm.services.backup_recovery import _snapshot_sqlite as original_snapshot

            def snapshot_then_change(source, destination):
                original_snapshot(source, destination)
                (Path(media) / "new-file.txt").write_text("changed during backup", encoding="utf-8")

            with patch("crm.services.backup_recovery._snapshot_sqlite", side_effect=snapshot_then_change):
                with self.assertRaisesRegex(BackupRecoveryError, "MEDIA_ROOT changed"):
                    create_consistent_backup(
                        database=database,
                        media_root=media,
                        output_dir=Path(root) / "backup",
                        backup_id="changed",
                        quiesced=True,
                    )
            self.assertFalse((Path(root) / "backup" / "erp-backup-changed.zip").exists())

    def test_restore_rejects_tampered_media(self):
        with TemporaryDirectory() as root:
            database, media = self._make_fixture(root)
            archive = Path(
                create_consistent_backup(
                    database=database,
                    media_root=media,
                    output_dir=Path(root) / "backup",
                    backup_id="tamper",
                    quiesced=True,
                )["archive"]
            )
            tampered = Path(root) / "tampered.zip"
            with zipfile.ZipFile(archive) as source, zipfile.ZipFile(tampered, "w", zipfile.ZIP_DEFLATED) as target:
                for info in source.infolist():
                    target.writestr(info.filename, b"tampered" if info.filename == "media/sku.png" else source.read(info))
            if os.name != "nt":
                os.chmod(tampered, 0o600)
            with self.assertRaisesRegex(BackupRecoveryError, "CRC|media manifest mismatch"):
                restore_consistent_backup(archive=tampered, target_dir=Path(root) / "restored")

    def test_non_empty_target_is_unchanged_and_failure_report_is_a_sibling(self):
        with TemporaryDirectory() as root:
            archive = self._make_archive(root, "collision")
            target = Path(root) / "restored"
            target.mkdir()
            keep = target / "keep.txt"
            keep.write_text("must remain", encoding="utf-8")
            existing_report = target / "restore-result.json"
            existing_report.write_text("do not overwrite", encoding="utf-8")
            with self.assertRaisesRegex(BackupRecoveryError, "already exists"):
                restore_consistent_backup(archive=archive, target_dir=target)
            self.assertEqual(keep.read_text(encoding="utf-8"), "must remain")
            self.assertEqual(existing_report.read_text(encoding="utf-8"), "do not overwrite")
            sibling_report = target.parent / ".restored.restore-result.json"
            self.assertEqual(json.loads(sibling_report.read_text(encoding="utf-8"))["status"], "FAILED")

    def test_explicit_failure_report_can_be_outside_target(self):
        with TemporaryDirectory() as root:
            archive = self._make_archive(root, "explicit-report")
            target = Path(root) / "restored"
            target.mkdir()
            (target / "keep.txt").write_text("unchanged", encoding="utf-8")
            report = Path(root) / "reports" / "restore.json"
            with self.assertRaises(BackupRecoveryError):
                restore_consistent_backup(archive=archive, target_dir=target, result_file=report)
            self.assertEqual((target / "keep.txt").read_text(encoding="utf-8"), "unchanged")
            self.assertEqual(json.loads(report.read_text(encoding="utf-8"))["status"], "FAILED")

    def test_existing_empty_target_is_rejected_without_deletion(self):
        with TemporaryDirectory() as root:
            archive = self._make_archive(root, "empty-collision")
            target = Path(root) / "restored"
            target.mkdir()
            with self.assertRaisesRegex(BackupRecoveryError, "already exists"):
                restore_consistent_backup(archive=archive, target_dir=target)
            self.assertTrue(target.is_dir())
            self.assertEqual(list(target.iterdir()), [])

    def test_disk_write_failure_leaves_no_target_or_staging_directory(self):
        with TemporaryDirectory() as root:
            archive = self._make_archive(root, "disk-failure")
            target = Path(root) / "restored"
            with patch("crm.services.backup_recovery.shutil.copyfileobj", side_effect=OSError("disk full")):
                with self.assertRaisesRegex(OSError, "disk full"):
                    restore_consistent_backup(archive=archive, target_dir=target)
            self.assertFalse(target.exists())
            self.assertEqual([path for path in Path(root).glob(".restored.restore-*") if path.is_dir()], [])
            self.assertEqual(json.loads((Path(root) / ".restored.restore-result.json").read_text())["status"], "FAILED")

    def test_archive_path_traversal_is_rejected_before_target_commit(self):
        with TemporaryDirectory() as root:
            archive = Path(root) / "traversal.zip"
            with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as target:
                target.writestr("../escaped.txt", "must not be extracted")
            if os.name != "nt":
                os.chmod(archive, 0o600)
            restore_target = Path(root) / "restored"
            with self.assertRaisesRegex(BackupRecoveryError, "Unsafe archive member"):
                restore_consistent_backup(archive=archive, target_dir=restore_target)
            self.assertFalse(restore_target.exists())
            self.assertFalse((Path(root).parent / "escaped.txt").exists())

    def test_backup_permissions_are_strict_on_posix_or_explicitly_pending_on_windows(self):
        with TemporaryDirectory() as root:
            backup_dir = Path(root) / "backup"
            access = ensure_secure_backup_directory(backup_dir)
            if os.name == "posix":
                self.assertEqual(stat.S_IMODE(backup_dir.stat().st_mode), 0o700)
            else:
                self.assertEqual(access["status"], "WINDOWS_ACL_PENDING")
            archive = self._make_archive(root, "permissions")
            if os.name == "posix":
                self.assertEqual(stat.S_IMODE(archive.stat().st_mode), 0o600)
            restored = Path(root) / "restored"
            restore_consistent_backup(archive=archive, target_dir=restored)
            if os.name == "posix":
                self.assertEqual(stat.S_IMODE(restored.stat().st_mode), 0o700)
                self.assertEqual(stat.S_IMODE((restored / "database.sqlite3").stat().st_mode), 0o600)
                self.assertEqual(stat.S_IMODE((restored / "media").stat().st_mode), 0o700)
                self.assertEqual(stat.S_IMODE((restored / "media" / "followups" / "invoice.pdf").stat().st_mode), 0o600)
                self.assertEqual(stat.S_IMODE((Path(root) / ".restored.restore-result.json").stat().st_mode), 0o600)

    @unittest.skipUnless(os.name == "posix", "POSIX mode check only")
    def test_existing_world_accessible_backup_directory_requires_explicit_tightening(self):
        with TemporaryDirectory() as root:
            backup_dir = Path(root) / "backup"
            backup_dir.mkdir(mode=0o755)
            with self.assertRaisesRegex(BackupRecoveryError, "group/other"):
                ensure_secure_backup_directory(backup_dir)
            ensure_secure_backup_directory(backup_dir, tighten=True)
            self.assertEqual(stat.S_IMODE(backup_dir.stat().st_mode), 0o700)

    @unittest.skipUnless(os.name == "nt", "Windows ACL check only")
    @override_settings(APP_STAGE="production")
    def test_windows_production_requires_external_ntfs_acl_verification(self):
        with TemporaryDirectory() as root:
            with self.assertRaisesRegex(BackupRecoveryError, "NTFS ACL"):
                ensure_secure_backup_directory(Path(root) / "backup")

    def test_requested_encryption_failure_is_recorded_as_failed(self):
        with TemporaryDirectory() as root:
            database, media = self._make_fixture(root)
            status = Path(root) / "status.json"
            with patch("crm.services.backup_recovery.shutil.which", return_value=None):
                with self.assertRaisesRegex(BackupRecoveryError, "age executable"):
                    create_consistent_backup(
                        database=database,
                        media_root=media,
                        output_dir=Path(root) / "backup",
                        backup_id="encryption-required",
                        quiesced=True,
                        encrypted_output=Path(root) / "offsite.age",
                        age_recipient="age1testrecipient",
                        status_file=status,
                    )
            self.assertEqual(json.loads(status.read_text())["status"], "FAILED")

    @override_settings(DATABASES={"default": {"ENGINE": "django.db.backends.postgresql", "NAME": "not-connected"}})
    def test_postgresql_backup_is_fail_closed_without_bound_snapshot(self):
        with TemporaryDirectory() as root:
            database, media = self._make_fixture(root)
            with self.assertRaisesRegex(BackupRecoveryError, "refuses PostgreSQL"):
                create_consistent_backup(database=database, media_root=media, output_dir=Path(root) / "backup", quiesced=True)

    def test_retention_plan_defaults_to_seven_daily_four_weekly_three_monthly_without_deleting(self):
        with TemporaryDirectory() as root:
            root = Path(root)
            base = datetime(2026, 10, 27, tzinfo=timezone.utc)
            for index in range(12):
                created = (base - timedelta(days=index)).isoformat().replace("+00:00", "Z")
                archive = root / f"erp-backup-{index:02d}.zip"
                manifest = {"created_at": created, "schema_version": 1, "backup_id": str(index)}
                with zipfile.ZipFile(archive, "w") as target:
                    target.writestr("manifest.json", json.dumps(manifest))
            result = prune_backup_archives(root)
            self.assertFalse(result["apply"])
            # The tiers are a union: the newest file for the next weekly
            # bucket is retained in addition to the seven daily files.
            self.assertEqual(len(result["kept"]), 8)
            self.assertEqual(len(result["removed"]), 4)
            self.assertEqual(len(list(root.glob("*.zip"))), 12)
