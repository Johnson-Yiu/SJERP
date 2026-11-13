import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from check_public_delivery import DATABASE, RULES
import re


class RulesTest(unittest.TestCase):
    def test_synthetic_token(self):
        pattern = RULES["github-token"]
        self.assertIsNotNone(re.search(pattern, b"gh" + b"p_" + b"A" * 36))
        self.assertIsNone(re.search(pattern, b"gh" + b"p_PLACEHOLDER"))

    def test_database_sidecars(self):
        self.assertIsNotNone(DATABASE.search("local/test.sqlite3-wal"))
        self.assertIsNone(DATABASE.search("docs/test.sqlite3.md"))



class GitWorkflowTest(unittest.TestCase):
    def test_scan_workflows(self):
        script = Path(os.environ.get("SEC1_TEST_SCRIPT", Path(__file__).with_name("check_public_delivery.py"))).resolve()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / "repo"
            repo.mkdir()
            backend = repo / "backend"
            backend.mkdir()

            def git(*args):
                return subprocess.check_output(["git", "-C", str(repo), *args], stderr=subprocess.DEVNULL).decode().strip()

            def scan(cwd, *args):
                result = subprocess.run([sys.executable, str(script), *args], cwd=cwd, capture_output=True)
                self.assertNotIn(secret.encode(), result.stdout + result.stderr)
                return result.returncode, json.loads(result.stdout)

            git("init")
            git("config", "user.name", "Synthetic")
            git("config", "user.email", "synthetic@example.invalid")
            secret = "gh" + "p_" + "Q" * 36
            (repo / "fixture.txt").write_text("ordinary synthetic data")
            (backend / "normal.txt").write_text("ordinary file")
            git("add", ".")
            git("commit", "-m", "base")
            base = git("rev-parse", "HEAD")
            self.assertEqual(scan(repo, "--candidate", base)[0], 0)
            git("mv", "fixture.txt", "fixture.db")
            (repo / "reused.sqlite").write_bytes((repo / "fixture.db").read_bytes())
            (repo / "token.txt").write_text(secret)
            git("add", ".")
            git("commit", "-m", "synthetic findings")
            git("rm", "token.txt")
            git("commit", "-m", "remove intermediate token")
            worktree = root / "linked"
            git("worktree", "add", "--detach", str(worktree), "HEAD")
            checks = [
                ("subdirectory", lambda: self.assertEqual(scan(repo), scan(backend))),
                ("worktree", lambda: self.assertEqual(scan(repo), scan(worktree / "backend"))),
                ("range", lambda: self.assertEqual(
                    {item["path"] for item in scan(repo, "--range", base + "..HEAD")[1]["findings"]},
                    {"fixture.db", "reused.sqlite", "token.txt"},
                )),
            ]
            git("remote", "add", "origin", "https://example.invalid/repo")
            git("remote", "add", "empty", "https://example.invalid/repo")
            git("update-ref", "refs/remotes/origin/main", "HEAD")
            git("update-ref", "refs/remotes/explicit/main", "HEAD")
            for remote, expected in [([], 1), (["--remote", "explicit"], 1), (["--remote", "missing"], 2), (["--remote", "empty"], 2)]:
                checks.append((str(remote), lambda remote=remote, expected=expected: self.assertEqual(
                    scan(repo, "--public-history", *remote)[0], expected,
                )))
            shallow = root / "shallow"
            git("clone", "--depth", "1", repo.as_uri(), str(shallow))
            checks.append(("shallow", lambda: self.assertEqual(scan(shallow, "--public-history")[0], 2)))
            checks.append(("blocked range", lambda: self.assertEqual(scan(repo, "--range", base + "..HEAD")[0], 1)))
            for name, check in checks:
                with self.subTest(name=name):
                    check()
