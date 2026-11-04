"""The drill SHA must cover quotation templates used by its synthetic fixture."""
import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

repository = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(repository / "backend"))
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["APP_STAGE"] = "development"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()
from crm.services.backup_recovery import BackupRecoveryError
from crm.services.postgres_drill_backup import IsolatedPostgresDrill


class DrillTemplateIdentityTests(unittest.TestCase):
    def test_clean_application_and_matching_sha_is_allowed(self):
        drill = IsolatedPostgresDrill.__new__(IsolatedPostgresDrill)
        drill.app_sha = "a" * 40
        with patch("crm.services.postgres_drill_backup.subprocess.run",
                   side_effect=[SimpleNamespace(stdout=drill.app_sha + "\n"), SimpleNamespace(stdout="")]):
            drill._assert_application()

    def test_wrong_commit_sha_is_rejected(self):
        drill = IsolatedPostgresDrill.__new__(IsolatedPostgresDrill)
        drill.app_sha = "a" * 40
        with patch("crm.services.postgres_drill_backup.subprocess.run",
                   side_effect=[SimpleNamespace(stdout="b" * 40 + "\n"), SimpleNamespace(stdout="")]):
            with self.assertRaises(BackupRecoveryError):
                drill._assert_application()

    def test_modified_quote_template_must_reject_reported_commit_sha(self):
        drill = IsolatedPostgresDrill.__new__(IsolatedPostgresDrill)
        drill.app_sha = "a" * 40

        def git_result(args, **kwargs):
            if args[1:3] == ["rev-parse", "HEAD"]:
                return SimpleNamespace(stdout=drill.app_sha + "\n")
            if args[1] == "status":
                # Simulate a modified application template: git sees it only
                # if the adapter includes its path in its status pathspec.
                return SimpleNamespace(stdout=" M templates/quotation/changed.xlsx\n" if "templates" in args else "")
            raise AssertionError(args)

        with patch("crm.services.postgres_drill_backup.subprocess.run", side_effect=git_result):
            with self.assertRaises(BackupRecoveryError):
                drill._assert_application()


if __name__ == "__main__":
    unittest.main(verbosity=2)
