from pathlib import Path
import tempfile
from unittest import TestCase, mock
import json
import subprocess
import sys

from crm.services.operations_copy import digest, verified_copy


class VerifiedCopyTests(TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="sunjack-operations-copy-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "source"
        self.source.write_bytes(b"synthetic backup" * 100000)
        self.target = self.root / "copy"
        self.sha = digest(self.source)

    def test_verified_copy_and_source_preserved(self):
        result = verified_copy(self.source, self.target, self.sha)
        self.assertEqual(digest(self.target), self.sha)
        self.assertEqual(digest(self.source), self.sha)
        self.assertFalse(result["independent_failure_domain_verified"])

    def test_existing_destination_never_overwritten_or_removed(self):
        self.target.write_bytes(b"existing")
        with self.assertRaises(FileExistsError):
            verified_copy(self.source, self.target, self.sha)
        self.assertEqual(self.target.read_bytes(), b"existing")

    def test_wrong_and_partial_digest_rejected_before_creation(self):
        for value in ("0" * 64, self.sha[:32]):
            with self.assertRaises(ValueError):
                verified_copy(self.source, self.target, value)
            self.assertFalse(self.target.exists())

    def test_copy_verification_failure_cleans_only_owned_copy(self):
        with mock.patch("crm.services.operations_copy.digest", side_effect=[self.sha, "0" * 64]):
            with self.assertRaises(ValueError):
                verified_copy(self.source, self.target, self.sha)
        self.assertFalse(self.target.exists())
        self.assertEqual(digest(self.source), self.sha)

    def test_fsync_failure_removes_incomplete_copy(self):
        with mock.patch("crm.services.operations_copy.os.fsync", side_effect=OSError("synthetic failure")):
            with self.assertRaises(OSError):
                verified_copy(self.source, self.target, self.sha)
        self.assertFalse(self.target.exists())
        self.assertEqual(digest(self.source), self.sha)

    def test_cleanup_failure_preserves_primary_error_and_partial_file(self):
        with mock.patch("crm.services.operations_copy.os.fsync", side_effect=OSError("primary")), mock.patch.object(Path, "unlink", side_effect=PermissionError("cleanup")):
            with self.assertRaisesRegex(OSError, "primary") as raised:
                verified_copy(self.source, self.target, self.sha)
        self.assertIn("Copy cleanup failed: PermissionError", raised.exception.__notes__)
        self.assertTrue(self.target.exists())
        self.assertEqual(digest(self.source), self.sha)

    def test_actual_cli_success_and_repeated_destination_refused(self):
        command = [sys.executable, str(Path(__file__).resolve().parents[2] / "operations_copy.py"),
                   "--source", str(self.source), "--destination", str(self.target), "--sha256", self.sha]
        first = subprocess.run(command, capture_output=True, text=True, timeout=30)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(json.loads(first.stdout)["status"], "VERIFIED_COPY")
        repeated = subprocess.run(command, capture_output=True, text=True, timeout=30)
        self.assertEqual(repeated.returncode, 1)
        self.assertEqual(json.loads(repeated.stdout)["error_type"], "FileExistsError")
        self.assertEqual(digest(self.target), self.sha)
