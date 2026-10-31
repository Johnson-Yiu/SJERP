"""Unit tests for fail-closed isolated runtime identity validation."""

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from test_support.isolated_runtime import IsolationError, verify_isolated_runtime


class IsolatedRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="sunjack-isolation-test-")
        self.root = Path(self.temp.name) / "run"
        self.root.mkdir()
        self.run_id = "unit-run"
        self.token = "unit-token"
        (self.root / ".sunjack-playwright-isolation.json").write_text(
            json.dumps({"runId": self.run_id, "token": self.token, "root": str(self.root.resolve())}), encoding="utf-8"
        )
        self.database = self.root / "db.sqlite3"
        self.media = self.root / "media"
        self.media.mkdir()
        self.environ = {
            "APP_STAGE": "development",
            "ISOLATED_TEST_ROOT": str(self.root),
            "ISOLATED_TEST_RUN_ID": self.run_id,
            "ISOLATED_TEST_TOKEN": self.token,
            "ISOLATED_TEST_DATABASE": str(self.database),
            "ISOLATED_TEST_MEDIA_ROOT": str(self.media),
        }

    def tearDown(self):
        self.temp.cleanup()

    def settings(self, database=None, media=None, engine="django.db.backends.sqlite3"):
        return SimpleNamespace(
            APP_STAGE="development",
            RBAC_ENFORCEMENT=False,
            MEDIA_STORAGE_BACKEND="django.core.files.storage.FileSystemStorage",
            DATABASES={"default": {"ENGINE": engine, "NAME": str(database or self.database)}},
            MEDIA_ROOT=str(media or self.media),
        )

    def test_accepts_only_marked_temp_database_and_media(self):
        result = verify_isolated_runtime(self.environ, self.settings())
        self.assertEqual(result["runId"], self.run_id)
        self.assertEqual(Path(result["database"]), self.database.resolve())

    def test_refuses_preexisting_database_before_migrations(self):
        self.database.write_bytes(b"not a database this run created")
        with self.assertRaisesRegex(IsolationError, "already exists before this run's migrations"):
            verify_isolated_runtime(self.environ, self.settings())

    def test_rejects_database_outside_run_directory(self):
        outside_database = Path(self.temp.name) / "other.sqlite3"
        with self.assertRaisesRegex(IsolationError, "outside this run's isolation root"):
            verify_isolated_runtime(self.environ, self.settings(database=outside_database))

    def test_rejects_declared_database_outside_run_directory_before_django_checks(self):
        environ = {**self.environ, "ISOLATED_TEST_DATABASE": str(Path(self.temp.name) / "other.sqlite3")}
        with self.assertRaisesRegex(IsolationError, "not this run's isolated SQLite file"):
            verify_isolated_runtime(environ)

    def test_rejects_non_sqlite_engine(self):
        with self.assertRaisesRegex(IsolationError, "isolated SQLite backend"):
            verify_isolated_runtime(self.environ, self.settings(engine="django.db.backends.postgresql"))

    def test_rejects_formal_rbac_in_development_browser_runtime(self):
        settings = self.settings()
        settings.RBAC_ENFORCEMENT = True
        with self.assertRaisesRegex(IsolationError, "Formal RBAC must remain disabled"):
            verify_isolated_runtime(self.environ, settings)

    def test_accepts_only_explicit_iss055_isolated_rbac_mode(self):
        environ = {**self.environ, "ISOLATED_TEST_RBAC_MODE": "iss055", "DEVELOPMENT_SUPERADMIN": "0"}
        settings = self.settings()
        settings.RBAC_ENFORCEMENT = True
        result = verify_isolated_runtime(environ, settings)
        self.assertTrue(result["rbacEnforcement"])

    def test_iss055_mode_rejects_development_superadmin(self):
        environ = {**self.environ, "ISOLATED_TEST_RBAC_MODE": "iss055", "DEVELOPMENT_SUPERADMIN": "1"}
        settings = self.settings()
        settings.RBAC_ENFORCEMENT = True
        with self.assertRaisesRegex(IsolationError, "disable the development superadmin"):
            verify_isolated_runtime(environ, settings)

    def test_unknown_isolated_rbac_mode_is_rejected(self):
        environ = {**self.environ, "ISOLATED_TEST_RBAC_MODE": "unrestricted"}
        with self.assertRaisesRegex(IsolationError, "allowlisted ISS-055"):
            verify_isolated_runtime(environ, self.settings())

    def test_rejects_media_root_outside_run_directory(self):
        outside_media = Path(self.temp.name) / "other-media"
        with self.assertRaisesRegex(IsolationError, "MEDIA_ROOT outside this run's isolation root"):
            verify_isolated_runtime(self.environ, self.settings(media=outside_media))

    def test_rejects_external_media_storage_backend(self):
        settings = self.settings()
        settings.MEDIA_STORAGE_BACKEND = "storages.backends.s3.S3Storage"
        with self.assertRaisesRegex(IsolationError, "local filesystem media storage"):
            verify_isolated_runtime(self.environ, settings)

    def test_rejects_additional_database_connections(self):
        settings = self.settings()
        settings.DATABASES["reporting"] = {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": "external-reporting",
        }
        with self.assertRaisesRegex(IsolationError, "additional database connections"):
            verify_isolated_runtime(self.environ, settings)

    def test_rejects_marker_from_another_run(self):
        self.environ["ISOLATED_TEST_RUN_ID"] = "different-run"
        with self.assertRaisesRegex(IsolationError, "does not match"):
            verify_isolated_runtime(self.environ)


if __name__ == "__main__":
    unittest.main()
