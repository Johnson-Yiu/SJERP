"""Real PostgreSQL tests, enabled only for an explicitly owned temp cluster."""

import json
import os
import threading
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import psycopg
from django.test import SimpleTestCase

from crm.services.backup_recovery import BackupRecoveryError, _sha256
from crm.services.postgres_drill_backup import IsolatedPostgresDrill


@unittest.skipUnless(os.getenv("ISS018_DRILL_ROOT"), "requires an explicitly owned PostgreSQL 17 drill cluster")
class PostgresDrillBackupTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        root = Path(os.environ["ISS018_DRILL_ROOT"]).resolve(strict=True)
        secret_file = Path(os.environ["ISS018_DRILL_PASSWORD_FILE"]).resolve(strict=True)
        if secret_file.parent != root:
            raise RuntimeError("Drill credential must be inside the task-owned temporary root")
        cls.drill = IsolatedPostgresDrill(
            task_root=root, pg_bin=root / "pgsql" / "bin", port=int(os.environ["ISS018_DRILL_PORT"]),
            user="iss018_drill_admin", password=secret_file.read_text(encoding="ascii").strip(),
            app_sha=os.environ["ISS018_DRILL_APP_SHA"],
        )
        with cls.drill._connect(cls.drill.source, autocommit=True) as connection:
            connection.execute("CREATE TABLE django_migrations (id serial PRIMARY KEY, app text NOT NULL, name text NOT NULL)")
            connection.execute("INSERT INTO django_migrations (app, name) VALUES ('synthetic', '0001')")
            connection.execute("CREATE TABLE fixture (id serial PRIMARY KEY, amount numeric NOT NULL)")
            connection.execute("INSERT INTO fixture (amount) VALUES (42.25)")
        cls.drill.media_write("followups/synthetic.txt", b"isolated synthetic attachment")

    def test_backup_restore_consistency_and_failure_boundaries(self):
        writer_done = threading.Event()
        threads = []

        def probe(drill):
            with drill._connect(drill.source, autocommit=True) as connection:
                connection.execute("SET lock_timeout = '200ms'")
                with self.assertRaises(psycopg.errors.LockNotAvailable):
                    connection.execute("UPDATE fixture SET amount=99 WHERE id=1")

            def writer():
                drill.media_write("followups/synthetic.txt", b"isolated synthetic attachment")
                writer_done.set()

            thread = threading.Thread(target=writer, daemon=True)
            threads.append(thread)
            thread.start()
            self.assertFalse(writer_done.wait(0.2), "controlled media writer passed the backup gate")

        backup = self.drill.backup(probe=probe)
        for thread in threads:
            thread.join(timeout=5)
        self.assertTrue(writer_done.is_set())
        restored = self.drill.restore(archive=backup["archive"], expected_sha256=backup["sha256"],
                                      current_app_sha=self.drill.app_sha)
        self.assertNotEqual(restored["database"], self.drill.source)
        self.assertNotEqual(Path(restored["media"]), self.drill.media)
        with self.drill._connect(restored["database"]) as connection:
            self.assertEqual(str(connection.execute("SELECT amount FROM fixture WHERE id=1").fetchone()[0]), "42.25")
        self.assertEqual((Path(restored["media"]) / "followups/synthetic.txt").read_bytes(),
                         b"isolated synthetic attachment")

        with self.assertRaisesRegex(BackupRecoveryError, "SHA256"):
            self.drill.restore(archive=backup["archive"], expected_sha256="0" * 64,
                               current_app_sha=self.drill.app_sha)
        with self.assertRaisesRegex(BackupRecoveryError, "version mismatch"):
            self.drill.restore(archive=backup["archive"], expected_sha256=backup["sha256"],
                               current_app_sha="0" * 40)

        missing = self.drill.root / "missing-media-test.zip"
        with zipfile.ZipFile(backup["archive"]) as source, zipfile.ZipFile(missing, "w") as target:
            for info in source.infolist():
                if info.filename != "media/followups/synthetic.txt":
                    target.writestr(info.filename, source.read(info))
        if os.name != "nt":
            os.chmod(missing, 0o600)
        with self.assertRaisesRegex(BackupRecoveryError, "Media manifest mismatch"):
            self.drill.restore(archive=missing, expected_sha256=_sha256(missing), current_app_sha=self.drill.app_sha)

        corrupt = self.drill.root / "bad-database-test.zip"
        with zipfile.ZipFile(backup["archive"]) as source, zipfile.ZipFile(corrupt, "w") as target:
            manifest = json.loads(source.read("manifest.json"))
            import hashlib
            bad_dump = b"not a postgres custom dump"
            manifest["database_sha256"] = hashlib.sha256(bad_dump).hexdigest()
            for info in source.infolist():
                content = bad_dump if info.filename == "database.dump" else source.read(info)
                if info.filename == "manifest.json":
                    content = json.dumps(manifest).encode("utf-8")
                target.writestr(info.filename, content)
        if os.name != "nt":
            os.chmod(corrupt, 0o600)
        owned_before = set(self.drill._owned_targets)
        with self.assertRaisesRegex(BackupRecoveryError, "pg_restore failed"):
            self.drill.restore(archive=corrupt, expected_sha256=_sha256(corrupt), current_app_sha=self.drill.app_sha)
        self.assertEqual(self.drill._owned_targets, owned_before)

        archives_before = set(self.drill.root.glob("iss018-pg-*.zip"))
        run_tool = self.drill._run

        def fail_dump(name, *args):
            if name == "pg_dump" and "--format=custom" in args:
                raise BackupRecoveryError("injected backup failure")
            return run_tool(name, *args)

        with patch.object(self.drill, "_run", side_effect=fail_dump):
            with self.assertRaises(BackupRecoveryError):
                self.drill.backup()
        self.assertEqual(set(self.drill.root.glob("iss018-pg-*.zip")), archives_before)
        with self.drill._connect(self.drill.source) as connection:
            self.assertEqual(str(connection.execute("SELECT amount FROM fixture WHERE id=1").fetchone()[0]), "42.25")
