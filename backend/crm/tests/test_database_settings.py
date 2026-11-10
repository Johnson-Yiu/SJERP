import os
import subprocess
import sys
from pathlib import Path

from django.test import SimpleTestCase


class DatabaseSettingsTests(SimpleTestCase):
    """Exercise database selection in isolated interpreter processes."""

    backend_dir = Path(__file__).resolve().parents[2]

    SAFE_TEST_SECRET = "test-only-secret-that-is-not-used-outside-the-test-suite-0123456789"

    def load_process(self, stage, database_url=None, extra=None, script=None):
        env = os.environ.copy()
        env.update({
            "DJANGO_SETTINGS_MODULE": "config.settings",
            "PYTHONIOENCODING": "utf-8",
            "APP_STAGE": stage,
            "DJANGO_DEBUG": "false" if stage != "development" else "true",
            "DJANGO_SECRET_KEY": self.SAFE_TEST_SECRET,
            "DJANGO_ALLOWED_HOSTS": "erp.test.local" if stage != "development" else "localhost,127.0.0.1",
            "CORS_ALLOWED_ORIGINS": "" if stage != "development" else "http://localhost:5191",
            "CSRF_TRUSTED_ORIGINS": "" if stage != "development" else "http://localhost:5191",
            "DEVELOPMENT_SUPERADMIN": "false" if stage != "development" else "true",
            "RBAC_ENFORCEMENT": "true" if stage != "development" else "false",
            "SECURE_SSL_REDIRECT": "true" if stage == "production" else "false",
            "SESSION_COOKIE_SECURE": "true" if stage != "development" else "false",
            "CSRF_COOKIE_SECURE": "true" if stage != "development" else "false",
            "SECURE_HSTS_SECONDS": "31536000" if stage == "production" else "0",
        })
        env.pop("DATABASE_URL", None)
        env.pop("MEDIA_ROOT", None)
        if stage != "development":
            # Deployed stages require an explicit absolute persistent media
            # path; use an isolated value for settings-only subprocess tests.
            env["MEDIA_ROOT"] = str(self.backend_dir / "test-media-production")
        if database_url is not None:
            env["DATABASE_URL"] = database_url
        if extra:
            env.update(extra)
        script = script or """
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
            encoding="utf-8",
            check=False,
        )

    def load_engine(self, stage, database_url=None):
        return self.load_process(stage, database_url)

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

    def test_production_defaults_are_secure_and_use_session_challenge(self):
        result = self.load_process(
            "production",
            "postgresql://user:password@db.internal:5432/sunjack_production",
            script="""
import json
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
from django.conf import settings
print(json.dumps({
    'debug': settings.DEBUG,
    'development_superadmin': settings.DEVELOPMENT_SUPERADMIN,
    'rbac_enforcement': settings.RBAC_ENFORCEMENT,
    'ssl_redirect': settings.SECURE_SSL_REDIRECT,
    'session_secure': settings.SESSION_COOKIE_SECURE,
    'csrf_secure': settings.CSRF_COOKIE_SECURE,
    'hsts': settings.SECURE_HSTS_SECONDS,
    'media_root': str(settings.MEDIA_ROOT),
    'auth_classes': settings.REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'],
}))
""",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('"debug": false', result.stdout)
        self.assertIn('"development_superadmin": false', result.stdout)
        self.assertIn('"rbac_enforcement": true', result.stdout)
        self.assertIn('"ssl_redirect": true', result.stdout)
        self.assertIn('"session_secure": true', result.stdout)
        self.assertIn('"csrf_secure": true', result.stdout)
        self.assertIn('"hsts": 31536000', result.stdout)
        self.assertIn('test-media-production', result.stdout)
        self.assertIn('crm.authentication.SessionAuthenticationWithChallenge', result.stdout)
        self.assertNotIn(self.SAFE_TEST_SECRET, result.stdout)

    def test_deployed_stage_requires_explicit_media_root(self):
        result = self.load_process(
            "production",
            "postgresql://user:password@db.internal:5432/sunjack_production",
            extra={"MEDIA_ROOT": ""},
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("MEDIA_ROOT is required outside development", result.stderr)

    def test_deployed_stage_rejects_relative_media_root(self):
        result = self.load_process(
            "production",
            "postgresql://user:password@db.internal:5432/sunjack_production",
            extra={"MEDIA_ROOT": "media-production"},
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("MEDIA_ROOT must be an absolute path", result.stderr)

    def test_media_root_cannot_overlap_static_root(self):
        result = self.load_process(
            "production",
            "postgresql://user:password@db.internal:5432/sunjack_production",
            extra={"MEDIA_ROOT": str(self.backend_dir / "staticfiles")},
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("MEDIA_ROOT and STATIC_ROOT must be separate", result.stderr)

    def test_production_rejects_debug_enabled(self):
        result = self.load_process(
            "production",
            "postgresql://user:password@db.internal:5432/sunjack_production",
            extra={"DJANGO_DEBUG": "true"},
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("DJANGO_DEBUG must be false outside development.", result.stderr)

    def test_production_rejects_development_superadmin(self):
        result = self.load_process(
            "production",
            "postgresql://user:password@db.internal:5432/sunjack_production",
            extra={"DEVELOPMENT_SUPERADMIN": "true"},
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("DEVELOPMENT_SUPERADMIN must be false outside development.", result.stderr)

    def test_production_rejects_disabled_rbac(self):
        result = self.load_process(
            "production",
            "postgresql://user:password@db.internal:5432/sunjack_production",
            extra={"RBAC_ENFORCEMENT": "false"},
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("RBAC_ENFORCEMENT must be true outside development.", result.stderr)

    def test_production_rejects_wildcard_hosts_and_http_origins(self):
        wildcard = self.load_process(
            "production",
            "postgresql://user:password@db.internal:5432/sunjack_production",
            extra={"DJANGO_ALLOWED_HOSTS": "*"},
        )
        self.assertNotEqual(wildcard.returncode, 0)
        self.assertIn("DJANGO_ALLOWED_HOSTS must contain explicit hosts outside development.", wildcard.stderr)

        insecure_origin = self.load_process(
            "production",
            "postgresql://user:password@db.internal:5432/sunjack_production",
            extra={"CORS_ALLOWED_ORIGINS": "http://erp.example.test"},
        )
        self.assertNotEqual(insecure_origin.returncode, 0)
        self.assertIn("must use HTTPS outside development.", insecure_origin.stderr)
