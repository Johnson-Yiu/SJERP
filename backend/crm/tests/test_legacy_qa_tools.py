import os
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings


class LegacyQaToolSafetyTests(SimpleTestCase):
    def test_business_flow_command_is_retired(self):
        with self.assertRaisesRegex(CommandError, "is retired"):
            call_command("run_business_flow_checks")

    def test_edge_business_flow_command_is_retired(self):
        with self.assertRaisesRegex(CommandError, "is retired"):
            call_command("run_edge_business_flow_checks")

    @override_settings(
        APP_STAGE="production",
        DATABASES={"default": {"ENGINE": "django.db.backends.postgresql", "NAME": "business"}},
    )
    def test_seed_demo_rejects_deployed_stage(self):
        from crm.management.commands.seed_demo import Command

        with self.assertRaisesRegex(CommandError, "APP_STAGE=development"):
            Command()._assert_safe_runtime()

    @override_settings(
        APP_STAGE="development",
        DATABASES={"default": {"ENGINE": "django.db.backends.postgresql", "NAME": "business"}},
    )
    def test_seed_demo_rejects_non_sqlite_database(self):
        from crm.management.commands.seed_demo import Command

        with self.assertRaisesRegex(CommandError, "非 SQLite"):
            Command()._assert_safe_runtime()

    @override_settings(
        APP_STAGE="development",
        DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": "shared.sqlite3"}},
    )
    def test_seed_demo_rejects_explicit_database_without_isolation_identity(self):
        from crm.management.commands.seed_demo import Command

        with patch.dict(os.environ, {"DATABASE_URL": "sqlite:///shared.sqlite3"}, clear=False):
            with self.assertRaisesRegex(CommandError, "未标记的 DATABASE_URL"):
                Command()._assert_safe_runtime()
