from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from crm.services.backup_recovery import BackupRecoveryError
from crm.services.postgres_drill_backup import IsolatedPostgresDrill


class PostgresDrillIdentityTests(SimpleTestCase):
    def test_checkout_identity_includes_templates(self):
        drill = IsolatedPostgresDrill.__new__(IsolatedPostgresDrill)
        drill.app_sha = "a" * 40

        def result(args, **kwargs):
            if args[1:3] == ["rev-parse", "HEAD"]:
                return SimpleNamespace(stdout=drill.app_sha)
            self.assertIn("backend", args)
            self.assertIn("templates", args)
            return SimpleNamespace(stdout=" M templates/quotation/changed.xlsx\n")

        with patch("crm.services.postgres_drill_backup.subprocess.run", side_effect=result):
            with self.assertRaises(BackupRecoveryError):
                drill._assert_application()

    def test_clean_checkout_is_allowed_and_wrong_sha_is_rejected(self):
        drill = IsolatedPostgresDrill.__new__(IsolatedPostgresDrill)
        drill.app_sha = "a" * 40
        for actual, rejected in ((drill.app_sha, False), ("b" * 40, True)):
            with self.subTest(rejected=rejected):
                with patch("crm.services.postgres_drill_backup.subprocess.run", side_effect=[
                    SimpleNamespace(stdout=actual), SimpleNamespace(stdout="")
                ]):
                    if rejected:
                        with self.assertRaises(BackupRecoveryError):
                            drill._assert_application()
                    else:
                        drill._assert_application()
