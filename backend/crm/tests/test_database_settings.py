import os
import subprocess
import sys
from pathlib import Path

from django.test import SimpleTestCase


class DatabaseSettingsTests(SimpleTestCase):
    """Exercise database selection in isolated interpreter processes."""

    backend_dir = Path(__file__).resolve().parents[2]

    def load_engine(self, stage, database_url=None):
        env = os.environ.copy()
        env.update({
            "DJANGO_SETTINGS_MODULE": "config.settings",
            "APP_STAGE": stage,
            "DJANGO_DEBUG": "false" if stage != "development" else "true",
        })
        env.pop("DATABASE_URL", None)
        if database_url is not None:
            env["DATABASE_URL"] = database_url
        script = """
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
from django.conf import settings
print(settings.DATABASES['default']['ENGINE'])
"""
        return subprocess.run(
            [sys.executable, "-c", script],
            cwd=self.backend_dir,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

    def assert_engine(self, stage, database_url, expected):
        result = self.load_engine(stage, database_url)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), expected)

    def assert_rejected(self, stage, database_url, message):
        result = self.load_engine(stage, database_url)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(message, result.stderr)

    def test_development_without_database_url_uses_sqlite(self):
        self.assert_engine("development", None, "django.db.backends.sqlite3")

    def test_development_postgresql_url_is_supported(self):
        self.assert_engine("development", "postgresql://user:password@localhost:5432/app", "django.db.backends.postgresql")

    def test_staging_postgresql_url_is_supported(self):
        self.assert_engine("staging", "postgresql://user:password@localhost:5432/app", "django.db.backends.postgresql")

    def test_production_postgresql_url_is_supported(self):
        self.assert_engine("production", "postgresql://user:password@localhost:5432/app", "django.db.backends.postgresql")

    def test_staging_without_database_url_fails_fast(self):
        self.assert_rejected("staging", None, "DATABASE_URL is required for staging/production.")

    def test_production_without_database_url_fails_fast(self):
        self.assert_rejected("production", None, "DATABASE_URL is required for staging/production.")

    def test_staging_sqlite_url_is_rejected(self):
        self.assert_rejected("staging", "sqlite:///staging.sqlite3", "DATABASE_URL must use PostgreSQL for staging/production.")

    def test_production_sqlite_url_is_rejected(self):
        self.assert_rejected("production", "sqlite:///production.sqlite3", "DATABASE_URL must use PostgreSQL for staging/production.")
