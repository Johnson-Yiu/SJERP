"""Behavioral regressions for lost fixes and mandatory release checks."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import check_pilot_release_source as inventory
import build_pilot_release as builder


class ReleaseSourceInventoryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="sjerp-inventory-test-")
        self.root = Path(self.temporary.name)
        self.addCleanup(self.temporary.cleanup)
        self.git("init", "--quiet")
        self.git("config", "user.name", "Release inventory test")
        self.git("config", "user.email", "release-test@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        self.write("page.txt", "reviewed table layout\n")
        self.anchor = self.commit("reviewed feature")
        digest = self.git("rev-parse", f"{self.anchor}:page.txt")
        self.policy = {
            "required_commits": {"reviewed feature": self.anchor},
            "reviewed_blobs": {"page.txt": digest},
            "required_text": {"page.txt": ["reviewed table layout"]},
        }
        self.write(inventory.POLICY_PATH, json.dumps(self.policy))
        self.good = self.commit("freeze reviewed inventory")

    def git(self, *args):
        return subprocess.check_output(["git", *args], cwd=self.root, text=True).strip()

    def write(self, path, content):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    def commit(self, message):
        self.git("add", "--all")
        self.git("commit", "--quiet", "-m", message)
        return self.git("rev-parse", "HEAD")

    def overwritten_commit(self):
        self.write("page.txt", "old narrow layout\n")
        return self.commit("later overwrite of an accepted feature")

    def test_reviewed_commit_passes(self):
        self.assertEqual(inventory.verify_source(self.good, repo=self.root), self.policy)

    def test_later_overwrite_fails_even_when_fix_remains_an_ancestor(self):
        bad = self.overwritten_commit()
        self.git("merge-base", "--is-ancestor", self.anchor, bad)
        with self.assertRaisesRegex(inventory.SourceInventoryError, "content differs"):
            inventory.verify_source(bad, repo=self.root)

    def test_uncommitted_policy_cannot_approve_overwritten_source(self):
        bad = self.overwritten_commit()
        self.write(inventory.POLICY_PATH, json.dumps({
            "required_commits": {}, "reviewed_blobs": {}, "required_text": {},
        }))
        with self.assertRaisesRegex(inventory.SourceInventoryError, "content differs"):
            inventory.verify_source(bad, repo=self.root)

    def test_missing_history_is_reported_instead_of_being_treated_as_pass(self):
        self.policy["required_commits"]["unavailable"] = "1" * 40
        self.write(inventory.POLICY_PATH, json.dumps(self.policy))
        candidate = self.commit("inventory requiring unavailable history")
        with self.assertRaisesRegex(inventory.SourceInventoryError, "required history unavailable"):
            inventory.verify_source(candidate, repo=self.root)

    def test_branch_name_is_not_a_frozen_release(self):
        with self.assertRaisesRegex(inventory.SourceInventoryError, "complete lowercase source SHA"):
            inventory.verify_source("HEAD", repo=self.root)

    def test_build_rejects_lost_fix_before_creating_output_or_running_npm(self):
        bad = self.overwritten_commit()
        output = self.root / "release-output"
        with patch.object(builder, "ROOT", self.root), patch.object(
            builder.shutil, "which", side_effect=AssertionError("npm must not run")
        ):
            with self.assertRaisesRegex(inventory.SourceInventoryError, "content differs"):
                builder.build(bad, output, offline=True)
        self.assertFalse(output.exists())
        self.assertEqual(list(self.root.glob(".sjerp-release-*")), [])

    def test_build_requires_checkout_to_match_the_selected_commit(self):
        self.write("notes.txt", "later accepted work\n")
        self.commit("later checkout")
        with patch.object(builder, "ROOT", self.root):
            with self.assertRaisesRegex(ValueError, "exact requested source commit"):
                builder.build(self.good, self.root / "release-output", offline=True)

    def test_build_rejects_local_tracked_changes(self):
        self.write("page.txt", "uncommitted overwrite\n")
        with patch.object(builder, "ROOT", self.root):
            with self.assertRaisesRegex(ValueError, "tracked files have local changes"):
                builder.build(self.good, self.root / "release-output", offline=True)

    def release(self, info_commit=None):
        directory = self.root / "bundle"
        info = directory / "frontend/dist/release-info.json"
        info.parent.mkdir(parents=True)
        info.write_text(json.dumps({"commit": info_commit or self.good}), encoding="utf-8")
        manifest = {"commit": self.good, "files": builder.file_records(directory)}
        content = json.dumps(manifest).encode("utf-8")
        (directory / builder.MANIFEST).write_bytes(content)
        return directory, hashlib.sha256(content).hexdigest()

    def test_verified_bundle_matches_expected_source_and_trusted_manifest(self):
        directory, digest = self.release()
        builder.verify(directory, expected_commit=self.good, manifest_sha256=digest)

    def test_verifier_rejects_different_deployment_commit(self):
        directory, digest = self.release()
        with self.assertRaisesRegex(ValueError, "expected deployment commit"):
            builder.verify(directory, expected_commit=self.anchor, manifest_sha256=digest)

    def test_verifier_rejects_an_untrusted_manifest(self):
        directory, _ = self.release()
        with self.assertRaisesRegex(ValueError, "trusted SHA-256"):
            builder.verify(directory, expected_commit=self.good, manifest_sha256="0" * 64)

    def test_verifier_rejects_inconsistent_browser_version_even_with_valid_hashes(self):
        directory, digest = self.release(info_commit=self.anchor)
        with self.assertRaisesRegex(ValueError, "Browser release information"):
            builder.verify(directory, expected_commit=self.good, manifest_sha256=digest)


if __name__ == "__main__":
    unittest.main()
