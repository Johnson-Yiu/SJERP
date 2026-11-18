"""Verify a fixed release commit against its reviewed source inventory."""

import argparse
import json
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = "docs/deployment/alex-source-inventory.json"
COMMIT_RE = re.compile(r"[0-9a-f]{40}")


class SourceInventoryError(ValueError):
    """The selected commit does not satisfy the declared release inventory."""


def git(*args, repo=ROOT):
    return subprocess.run(
        ["git", *args], cwd=repo, check=False, capture_output=True,
        text=True, encoding="utf-8",
    )


def verify_source(commit, policy_path=None, *, repo=ROOT):
    if not COMMIT_RE.fullmatch(commit):
        raise SourceInventoryError("Use the complete lowercase source SHA, not a branch name.")
    resolved = git("rev-parse", "--verify", commit + "^{commit}", repo=repo)
    if resolved.returncode or resolved.stdout.strip() != commit:
        raise SourceInventoryError("The selected source commit is not available in this checkout.")

    if policy_path is None:
        source = git("show", f"{commit}:{POLICY_PATH}", repo=repo)
        if source.returncode:
            raise SourceInventoryError(f"The selected commit has no release inventory: {POLICY_PATH}")
        raw_policy = source.stdout
    else:
        # Explicit external policies remain useful when auditing an older release.
        raw_policy = Path(policy_path).read_text(encoding="utf-8")
    try:
        policy = json.loads(raw_policy)
    except (TypeError, json.JSONDecodeError) as exc:
        raise SourceInventoryError("The release inventory is not valid JSON.") from exc
    if not isinstance(policy, dict) or any(
        not isinstance(policy.get(key), dict)
        for key in ("required_commits", "reviewed_blobs", "required_text")
    ):
        raise SourceInventoryError("The release inventory must declare commits, blobs and text checks.")
    if not policy["required_commits"] or not policy["reviewed_blobs"]:
        raise SourceInventoryError("The release inventory must not omit required commits or reviewed files.")

    failures = []
    for label, required in policy["required_commits"].items():
        if not isinstance(required, str) or not COMMIT_RE.fullmatch(required):
            failures.append(f"{label}: invalid required commit")
            continue
        available = git("cat-file", "-e", required + "^{commit}", repo=repo)
        if available.returncode:
            failures.append(f"{label}: required history unavailable; fetch full history for {required}")
            continue
        result = git("merge-base", "--is-ancestor", required, commit, repo=repo)
        if result.returncode:
            failures.append(f"{label}: missing required commit {required}")
    for path, expected in policy["reviewed_blobs"].items():
        result = git("rev-parse", "--verify", f"{commit}:{path}", repo=repo)
        if result.returncode or result.stdout.strip() != expected:
            failures.append(f"{path}: content differs from the reviewed version")
    for path, required in policy["required_text"].items():
        if not isinstance(required, list) or not required or any(
            not isinstance(text, str) or not text for text in required
        ):
            failures.append(f"{path}: invalid required text checks")
            continue
        result = git("show", f"{commit}:{path}", repo=repo)
        if result.returncode or any(text not in result.stdout for text in required):
            failures.append(f"{path}: missing required release behavior")
    if failures:
        raise SourceInventoryError("\n".join(failures))
    return policy


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("commit", help="the full deployment source SHA")
    parser.add_argument(
        "policy", nargs="?", type=Path,
        help="optional external audit policy; by default read the policy from the selected commit",
    )
    args = parser.parse_args()
    try:
        verify_source(args.commit, args.policy)
    except (OSError, SourceInventoryError) as exc:
        parser.exit(1, f"{exc}\n")
    print(f"{args.commit}: ALEX source inventory verified")


if __name__ == "__main__":
    main()
