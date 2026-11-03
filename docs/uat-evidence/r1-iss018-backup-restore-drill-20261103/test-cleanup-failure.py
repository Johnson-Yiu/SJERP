"""Synthetic test of diagnostic preservation when owned-root cleanup fails."""
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

repository = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(repository / "backend"))
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["APP_STAGE"] = "development"
import isolated_postgres_drill as command


class CleanupFailureTests(unittest.TestCase):
    def test_original_failure_and_owned_leftover_are_reported(self):
        root = Path(tempfile.mkdtemp(prefix="sunjack-iss018-pg17-"))
        output = io.StringIO()
        try:
            args = ["isolated_postgres_drill.py", "--postgres-bin", str(root / "missing-bin")]
            with patch.object(sys, "argv", args), patch.object(command.tempfile, "mkdtemp", return_value=str(root)), \
                    patch.object(command.shutil, "rmtree", side_effect=PermissionError("simulated lock")), \
                    patch.object(command.time, "sleep"), contextlib.redirect_stderr(output):
                code = command.main()
            result = json.loads(output.getvalue())
            self.assertEqual(code, 1)
            self.assertEqual(result["status"], "FAILED")
            self.assertIn("FileNotFoundError", result["error"])
            self.assertIn("simulated lock", result["cleanup_error"])
            self.assertEqual(result["leftover_root"], str(root))
            self.assertFalse((root / "secret").exists())
            print("SIMULATED_CLEANUP_FAILURE " + json.dumps(result, sort_keys=True))
        finally:
            # This test never created files in its own explicitly created root.
            root.rmdir()


if __name__ == "__main__":
    unittest.main(verbosity=2)
