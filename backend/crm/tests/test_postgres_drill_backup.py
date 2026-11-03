"""Real PostgreSQL tests, enabled only for an explicitly owned temp cluster."""

import json
import os
import socket
import subprocess
import sys
import threading
import time
import unittest
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from unittest.mock import patch

import psycopg
from psycopg import sql
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
        cls.drill._manage("migrate", "--noinput", "--verbosity", "0")
        cls.fixture = json.loads(cls.drill._manage("shell", "--no-imports", "-c",
                                  "from crm.tests.iss018_drill_fixture import seed; seed()"))
        with cls.drill._connect(cls.drill.source, autocommit=True) as connection:
            connection.execute("CREATE TABLE fixture (id serial PRIMARY KEY, amount numeric NOT NULL)")
            connection.execute("INSERT INTO fixture (amount) VALUES (42.25)")
        cls.drill.media_write("followups/synthetic.txt", b"isolated synthetic attachment")

    def _business_snapshot(self, database):
        tables = ("auth_user", "crm_customer", "crm_supplier", "crm_product", "crm_sku", "crm_quote",
                  "crm_quoteitem", "crm_order", "crm_orderitem", "crm_purchaseorder", "crm_purchaseorderitem",
                  "crm_purchasecostallocation", "crm_goodsreceipt", "crm_inventorymovement", "crm_inventoryreservation",
                  "crm_paymentplan", "crm_transaction", "crm_followup", "crm_followupattachment", "crm_operationlog",
                  "crm_csvimportpreviewaudit", "crm_csvimportbatch", "crm_csvimportrowaudit")
        with self.drill._connect(database) as connection:
            rows = {table: connection.execute(sql.SQL("SELECT * FROM {} ORDER BY id").format(sql.Identifier(table))).fetchall()
                    for table in tables}
            sequences = connection.execute("SELECT sequencename,last_value FROM pg_sequences WHERE schemaname='public' ORDER BY sequencename").fetchall()
            foreign_keys = connection.execute("SELECT conrelid::regclass::text,conname,convalidated FROM pg_constraint WHERE contype='f' AND connamespace='public'::regnamespace ORDER BY 1,2").fetchall()
            triggers = connection.execute("SELECT tgrelid::regclass::text,tgname,tgenabled FROM pg_trigger WHERE NOT tgisinternal ORDER BY 1,2").fetchall()
        return rows, sequences, foreign_keys, triggers

    def _audit_rejects_mutation(self, database):
        for table in ("crm_operationlog", "crm_csvimportbatch", "crm_csvimportrowaudit", "crm_csvimportpreviewaudit"):
            for statement in ("UPDATE {} SET id=id", "DELETE FROM {}"):
                with self.subTest(table=table, operation=statement), self.drill._connect(database) as connection:
                    with self.assertRaises(psycopg.Error):
                        with connection.transaction():
                            connection.execute(sql.SQL(statement).format(sql.Identifier(table)))
                            raise AssertionError("audit mutation unexpectedly succeeded")
        for table in ("crm_csvimportbatch", "crm_csvimportrowaudit", "crm_csvimportpreviewaudit"):
            with self.subTest(table=table, operation="TRUNCATE"), self.drill._connect(database) as connection:
                with self.assertRaises(psycopg.Error):
                    with connection.transaction():
                        connection.execute(sql.SQL("TRUNCATE TABLE {} CASCADE").format(sql.Identifier(table)))
                        raise AssertionError("audit truncate unexpectedly succeeded")

    def _http_check(self, restored):
        sessions = json.loads(self.drill._manage_database(restored["database"], restored["media"],
            "shell", "--no-imports", "-c", "from crm.tests.iss018_drill_fixture import sessions; sessions()"))
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        backend = Path(__file__).resolve().parents[2]
        env = self.drill._environment(restored["database"], restored["media"])
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        process = subprocess.Popen([sys.executable, str(backend / "manage.py"), "runserver", f"127.0.0.1:{port}", "--noreload"],
                                   cwd=backend, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=flags)

        def get(path, session=None):
            headers = {"Cookie": "sessionid=" + session} if session else {}
            try:
                with urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{port}{path}", headers=headers), timeout=3) as response:
                    return response.status, response.read(), response.headers.get("Cache-Control", "")
            except urllib.error.HTTPError as exc:
                return exc.code, exc.read(), exc.headers.get("Cache-Control", "")

        try:
            for _ in range(100):
                if process.poll() is not None:
                    raise AssertionError("isolated application server exited before startup")
                try:
                    anonymous = get("/api/media/" + self.fixture["attachment"])
                    break
                except urllib.error.URLError:
                    time.sleep(0.1)
            else:
                raise AssertionError("isolated application server did not start")
            owner = sessions["iss018-drill-owner"]
            denied = sessions["iss018-drill-denied"]
            attachment = get("/api/media/" + self.fixture["attachment"], owner)
            image = get("/api/media/" + self.fixture["image"], owner)
            outsider = get("/api/media/" + self.fixture["attachment"], denied)
            public = get("/media/" + self.fixture["attachment"])
            self.assertIn(anonymous[0], (401, 403))
            self.assertIn(outsider[0], (403, 404))
            self.assertEqual(public[0], 404)
            self.assertEqual(attachment[0], 200)
            self.assertEqual(attachment[1], b"synthetic private file\n")
            self.assertEqual(attachment[2], "private, no-store")
            self.assertEqual(image[0], 200)
            self.assertTrue(image[1].startswith(b"GIF87a"))
            return {"authorized_attachment": attachment[0], "historical_image": image[0],
                    "anonymous": anonymous[0], "unauthorized": outsider[0], "old_public": public[0]}
        finally:
            process.terminate()
            process.wait(timeout=10)

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

        source_state = self._business_snapshot(self.drill.source)
        started = time.monotonic()
        backup = self.drill.backup(probe=probe)
        backup_seconds = round(time.monotonic() - started, 3)
        for thread in threads:
            thread.join(timeout=5)
        self.assertTrue(writer_done.is_set())
        started = time.monotonic()
        restored = self.drill.restore(archive=backup["archive"], expected_sha256=backup["sha256"],
                                      current_app_sha=self.drill.app_sha)
        restore_seconds = round(time.monotonic() - started, 3)
        self.assertNotEqual(restored["database"], self.drill.source)
        self.assertNotEqual(Path(restored["media"]), self.drill.media)
        with self.drill._connect(restored["database"]) as connection:
            self.assertEqual(str(connection.execute("SELECT amount FROM fixture WHERE id=1").fetchone()[0]), "42.25")
        self.assertEqual((Path(restored["media"]) / "followups/synthetic.txt").read_bytes(),
                         b"isolated synthetic attachment")
        self.assertEqual(self._business_snapshot(restored["database"]), source_state)
        for key in ("attachment", "image"):
            self.assertTrue((Path(restored["media"]) / self.fixture[key]).is_file())
        self._audit_rejects_mutation(restored["database"])
        http = self._http_check(restored)
        print("ISS018_PG_DRILL " + json.dumps({"source": self.drill.source, "target": restored["database"],
              "sha256": backup["sha256"], "app_sha": self.drill.app_sha, "versions": backup["manifest"]["versions"],
              "media": backup["manifest"]["media"], "migrations": len(backup["manifest"]["migrations"]),
              "counts": {table: len(rows) for table, rows in source_state[0].items()}, "http": http,
              "backup_seconds": backup_seconds, "restore_seconds": restore_seconds}, sort_keys=True))

        with self.assertRaisesRegex(BackupRecoveryError, "SHA256"):
            self.drill.restore(archive=backup["archive"], expected_sha256="0" * 64,
                               current_app_sha=self.drill.app_sha)
        with self.assertRaisesRegex(BackupRecoveryError, "version mismatch"):
            self.drill.restore(archive=backup["archive"], expected_sha256=backup["sha256"],
                               current_app_sha="0" * 40)

        with self.assertRaises(BackupRecoveryError):
            self.drill._environment("postgres", self.drill.media)
        tampered = self.drill.root / "tampered-manifest-test.zip"
        with zipfile.ZipFile(backup["archive"]) as source, zipfile.ZipFile(tampered, "w") as target:
            for info in source.infolist():
                content = source.read(info)
                if info.filename == "manifest.json":
                    manifest = json.loads(content)
                    manifest["app_sha"] = "0" * 40
                    content = json.dumps(manifest).encode("utf-8")
                target.writestr(info.filename, content)
        if os.name != "nt":
            os.chmod(tampered, 0o600)
        with self.assertRaisesRegex(BackupRecoveryError, "SHA256"):
            self.drill.restore(archive=tampered, expected_sha256=backup["sha256"], current_app_sha=self.drill.app_sha)
        with self.assertRaisesRegex(BackupRecoveryError, "version mismatch"):
            self.drill.restore(archive=tampered, expected_sha256=_sha256(tampered), current_app_sha=self.drill.app_sha)

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
