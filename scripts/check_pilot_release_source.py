"""Check a release source against the reviewed ALEX pilot baseline and inventory."""
import argparse
import json
from pathlib import Path
import re
import subprocess


def git(*args, check=True):
    return subprocess.run(["git", *args], check=check, capture_output=True, text=True, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("commit", help="the full deployment source SHA")
    parser.add_argument("policy", type=Path)
    args = parser.parse_args()
    policy = json.loads(args.policy.read_text(encoding="utf-8"))
    if not re.fullmatch(r"[0-9a-f]{40}", args.commit):
        parser.error("use the complete source SHA, not a branch name")
    if git("rev-parse", "--verify", args.commit + "^{commit}").stdout.strip() != args.commit:
        parser.error("invalid source commit")
    failures = []
    for label, required in policy["required_commits"].items():
        result = git("merge-base", "--is-ancestor", required, args.commit, check=False)
        if result.returncode:
            failures.append(f"{label}: missing required commit {required}")
    for path, expected in policy["reviewed_blobs"].items():
        result = git("rev-parse", "--verify", f"{args.commit}:{path}", check=False)
        if result.returncode or result.stdout.strip() != expected:
            failures.append(f"{path}: content differs from the reviewed version")
    for path, required in policy["required_text"].items():
        result = git("show", f"{args.commit}:{path}", check=False)
        if result.returncode or any(text not in result.stdout for text in required):
            failures.append(f"{path}: missing required release behavior")
    if failures:
        parser.exit(1, "\n".join(failures) + "\n")
    print(f"{args.commit}: ALEX source inventory verified")


if __name__ == "__main__":
    main()
