from pathlib import Path
import tempfile
from unittest import TestCase, mock
import os

from crm.services.operations_copy import digest
from crm.services.operations_crypto import crypt_file


class CryptoSafetyTests(TestCase):
    def test_tool_failure_preserves_source_and_removes_only_new_output(self):
        with tempfile.TemporaryDirectory(prefix="sunjack-crypto-test-") as folder:
            root = Path(folder)
            source, tool, target = root / "source", root / "tool", root / "target"
            source.write_bytes(b"synthetic")
            tool.touch()
            tool.with_name("gpgconf.exe" if os.name == "nt" else "gpgconf").touch()
            with mock.patch("crm.services.operations_crypto.subprocess.run") as run:
                run.side_effect = [mock.Mock(returncode=2), mock.Mock(returncode=0)]
                with self.assertRaisesRegex(RuntimeError, "operation failed"):
                    crypt_file(source, target, executable=tool, key=b"x" * 32, expected_sha256=digest(source))
                self.assertFalse(target.exists())
                self.assertEqual(source.read_bytes(), b"synthetic")
                arguments = run.call_args_list[0]
                self.assertNotIn("x" * 32, str(arguments.args))
                self.assertEqual(arguments.kwargs["input"], b"x" * 32 + b"\n")

    def test_invalid_key_and_existing_output_refused(self):
        with tempfile.TemporaryDirectory(prefix="sunjack-crypto-test-") as folder:
            root = Path(folder)
            source, tool, target = root / "source", root / "tool", root / "target"
            source.write_bytes(b"synthetic")
            tool.touch()
            tool.with_name("gpgconf.exe" if os.name == "nt" else "gpgconf").touch()
            target.write_bytes(b"preserve")
            with self.assertRaises(ValueError):
                crypt_file(source, target, executable=tool, key=b"short", expected_sha256=digest(source))
            with self.assertRaises(FileExistsError):
                crypt_file(source, target, executable=tool, key=b"x" * 32, expected_sha256=digest(source))
            self.assertEqual(target.read_bytes(), b"preserve")
