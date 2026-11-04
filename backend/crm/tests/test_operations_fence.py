import os
from pathlib import Path
import subprocess
import tempfile
from unittest import TestCase, mock

from crm.services.operations_fence import verify_offline_postgres, verify_readonly_filesystem


class OfflineFenceTests(TestCase):
    def test_actual_writable_temporary_directory_never_qualifies(self):
        with tempfile.TemporaryDirectory(prefix="sunjack-fence-") as root:
            with self.assertRaises((RuntimeError, subprocess.SubprocessError, FileNotFoundError)):
                verify_readonly_filesystem(root)

    def test_offline_database_requires_clean_shutdown_identity_and_version(self):
        with tempfile.TemporaryDirectory(prefix="sunjack-offline-fence-") as temporary:
            root = Path(temporary)
            (root / "PG_VERSION").write_text("17", encoding="ascii")
            with mock.patch("crm.services.operations_fence.verify_readonly_filesystem", return_value={"filesystem": "synthetic"}), mock.patch("crm.services.operations_fence.subprocess.run") as run:
                run.return_value.stdout = "Database cluster state: shut down\nDatabase system identifier: 123456\n"
                self.assertEqual(verify_offline_postgres(root, "synthetic-tool")["system_identifier"], "123456")
                run.return_value.stdout = "Database cluster state: in production\nDatabase system identifier: 123456\n"
                with self.assertRaisesRegex(RuntimeError, "clean primary shutdown"):
                    verify_offline_postgres(root, "synthetic-tool")
                (root / "postmaster.pid").write_text("123", encoding="ascii")
                run.reset_mock()
                with self.assertRaisesRegex(RuntimeError, "shutdown is unproven"):
                    verify_offline_postgres(root, "synthetic-tool")
                run.assert_not_called()
