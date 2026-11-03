"""Subprocess-level acceptance; requires explicitly supplied PostgreSQL 17 binaries."""

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

from django.test import SimpleTestCase


@unittest.skipUnless(os.environ.get("ISS018_COMMAND_PG_BIN"), "requires local PostgreSQL 17 binaries")
class IsolatedPostgresCommandTests(SimpleTestCase):
    def invoke(self, fault=None):
        script = Path(__file__).resolve().parents[2] / "isolated_postgres_drill.py"
        args = [sys.executable, str(script), "--postgres-bin", os.environ["ISS018_COMMAND_PG_BIN"]]
        if fault:
            args.extend(("--test-fault", fault))
        run = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
        output = run.stderr if fault else run.stdout
        self.assertTrue(output.strip(), (run.returncode, run.stdout, run.stderr))
        result = json.loads(output.strip().splitlines()[-1])
        self.assertEqual(result["cleanup"], "complete")
        if fault:
            self.assertNotEqual(run.returncode, 0, (run.stdout, run.stderr))
            self.assertEqual(result["status"], "FAILED")
            self.assertTrue(result["source_unchanged"])
        else:
            self.assertEqual(run.returncode, 0, (run.stdout, run.stderr))
            self.assertEqual(result["status"], "PASS")
            self.assertGreater(result["row_count"], 0)
        print("COMMAND_CASE " + json.dumps({"case": fault or "success", "exit": run.returncode,
                                           "result": result}, sort_keys=True))
        return result

    def test_success(self):
        self.invoke()

    def test_checksum(self):
        self.assertIn("SHA256 mismatch", self.invoke("checksum")["error"])

    def test_missing_media(self):
        self.assertIn("Media manifest mismatch", self.invoke("missing-media")["error"])

    def test_corrupt_archive(self):
        self.assertIn("BadZipFile", self.invoke("corrupt")["error"])

    def test_incompatible_version(self):
        self.assertIn("version mismatch", self.invoke("version")["error"])

    def test_failed_restore_tool(self):
        self.assertIn("pg_restore failed", self.invoke("tool")["error"])

    def test_wrong_environment(self):
        self.assertIn("only use a database created by this drill", self.invoke("environment")["error"])
