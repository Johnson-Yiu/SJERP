import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import OperationalError
from django.test import SimpleTestCase


class LocalRuntimeCheckTests(SimpleTestCase):
    def test_readiness_rejects_wrong_target_pending_migrations_and_overprivileged_role(self):
        command = "crm.management.commands.check_local_runtime"
        target = {"HOST": "localhost", "PORT": "5432", "NAME": "runtime_a", "USER": "runtime_user"}
        with TemporaryDirectory() as folder:
            media = Path(folder) / "media"
            media.mkdir()
            expected = {f"SJERP_EXPECTED_DB_{key}": value for key, value in target.items()}
            expected["SJERP_EXPECTED_MEDIA_ROOT"] = str(media)
            with (
                self.settings(APP_STAGE="staging", MEDIA_ROOT=media),
                patch.dict(os.environ, expected),
                patch(command + ".connections") as connections,
                patch(command + ".MigrationExecutor") as executor,
            ):
                database = connections.__getitem__.return_value
                database.settings_dict = target.copy()
                cursor = database.cursor.return_value.__enter__.return_value
                cursor.fetchone.side_effect = [(target["NAME"], target["USER"]), (False, False, True)]
                executor.return_value.migration_plan.return_value = []
                call_command("check_local_runtime", skip_checks=True)
                executor.return_value.loader.check_consistent_history.assert_called_once_with(database)

                with patch.dict(os.environ, SJERP_EXPECTED_DB_NAME="runtime_b"):
                    with self.assertRaisesMessage(CommandError, "Configured database NAME differs"):
                        call_command("check_local_runtime", skip_checks=True)
                with self.settings(MEDIA_ROOT=media / "missing"):
                    with self.assertRaisesMessage(CommandError, "private media directory differs"):
                        call_command("check_local_runtime", skip_checks=True)

                cursor.fetchone.side_effect = [(target["NAME"], target["USER"])]
                executor.return_value.migration_plan.return_value = [object()]
                with self.assertRaisesMessage(CommandError, "Database migrations are pending"):
                    call_command("check_local_runtime", skip_checks=True)

                executor.return_value.migration_plan.return_value = []
                cursor.fetchone.side_effect = [(target["NAME"], target["USER"]), (False, True, True)]
                with self.assertRaisesMessage(CommandError, "violates the audit table privilege boundary"):
                    call_command("check_local_runtime", skip_checks=True)
                cursor.fetchone.side_effect = [("runtime_b", target["USER"])]
                with self.assertRaisesMessage(CommandError, "Connected PostgreSQL database or role differs"):
                    call_command("check_local_runtime", skip_checks=True)
                database.cursor.side_effect = OperationalError("synthetic")
                with self.assertRaisesMessage(CommandError, "Database readiness check failed (OperationalError)"):
                    call_command("check_local_runtime", skip_checks=True)
