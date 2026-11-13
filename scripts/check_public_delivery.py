"""Read Git objects and report rule IDs and locations without matched values."""
import argparse
from collections import Counter
import json
from pathlib import PurePosixPath
import re
import subprocess

RULES = {
    "private-key": rb"-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----",
    "github-token": rb"\b(?:gh[pousr]_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{82})\b",
    "aws-access-id": rb"\bAKIA[0-9A-Z]{16}\b",
}
CONNECTION = re.compile(rb"\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis)://[^\s:/@]+:[^\s/@]+@[^\s/]+", re.I)
BUSINESS = {".csv", ".tsv", ".xls", ".xlsx", ".pdf", ".docx", ".zip", ".7z", ".gz", ".png", ".jpg", ".jpeg", ".webp", ".log", ".har"}
DATABASE = re.compile(r"\.(?:sqlite3?|db)(?:-(?:wal|shm|journal))?$|\.(?:sql|pgdump|dump)(?:\.gz)?$", re.I)


def git(*args, cwd=None):
    return subprocess.check_output(["git", *args], cwd=cwd, stderr=subprocess.DEVNULL)


def commit(root, revision):
    return git("rev-parse", "--verify", "--end-of-options", revision + "^{commit}", cwd=root).decode().strip()


def scope(root, args):
    if not (args.range or args.public_history):
        head = commit(root, args.candidate or "HEAD")
        return {"mode": "candidate", "head": head}, [head]
    if git("rev-parse", "--is-shallow-repository", cwd=root).strip() != b"false":
        raise ValueError("History is shallow. Fetch complete history first.")
    if args.public_history:
        remote = args.remote or "origin"
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]*", remote):
            raise ValueError("Invalid remote name.")
        prefix = "refs/remotes/" + remote + "/"
        refs = git("for-each-ref", "--format=%(refname) %(objectname) %(symref)", prefix, cwd=root)
        heads = {}
        for line in refs.decode().splitlines():
            name, oid, symbolic = line.split(" ", 2)
            if not symbolic:
                heads[safe_path(name)] = oid
        if not heads:
            raise ValueError("No fetched tracking branches for the selected remote.")
        commits = subprocess.check_output(
            ["git", "rev-list", "--stdin"], cwd=root,
            input=("\n".join(set(heads.values())) + "\n").encode(), stderr=subprocess.DEVNULL,
        )
        return {"mode": "public-history", "refs": heads}, commits.decode().splitlines()
    parts = args.range.split("..")
    if len(parts) != 2 or not all(parts):
        raise ValueError("Use an explicit BASE..HEAD range.")
    base, head = (commit(root, part) for part in parts)
    git("merge-base", "--is-ancestor", base, head, cwd=root)
    commits = git("rev-list", base + ".." + head, "--", cwd=root).decode().splitlines()
    return {"mode": "range", "base": base, "head": head}, commits


def objects(root, mode, commits):
    seen = set()
    for revision in commits:
        if mode == "candidate":
            output = git("ls-tree", "-rz", revision, "--", cwd=root)
            records = []
            for entry in output.split(b"\0")[:-1]:
                header, path = entry.split(b"\t", 1)
                _, kind, oid = header.split()
                if kind == b"blob":
                    records.append((oid, path))
        else:
            # Compare every selected commit to its first parent. Treat renames
            # as deletion/addition so destination paths are always scanned.
            parents = git("rev-list", "--parents", "-n", "1", revision, cwd=root).split()
            endpoints = [parents[1].decode(), revision] if len(parents) > 1 else ["--root", revision]
            output = git("diff-tree", "--no-commit-id", "--no-renames", "--no-abbrev",
                         "--diff-filter=AMT", "-r", "-z", *endpoints, "--", cwd=root)
            entries = iter(output.split(b"\0")[:-1])
            records = []
            for header, path in zip(entries, entries):
                _, mode_bits, _, oid, _ = header.split()
                if mode_bits != b"160000":
                    records.append((oid, path))
        for oid, path in records:
            if (oid, path) not in seen:
                seen.add((oid, path))
                yield oid, path.decode("utf-8", "replace")


def safe_path(path):
    data = path.encode("utf-8")
    for pattern in (*RULES.values(), CONNECTION):
        data = re.sub(pattern, b"[redacted]", data)
    return data.decode("utf-8")


def scan(root, entries, limit):
    counts = Counter()
    findings = []
    with subprocess.Popen(["git", "cat-file", "--batch"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, cwd=root) as batch:
        for oid, path in entries:
            batch.stdin.write(oid + b"\n")
            batch.stdin.flush()
            header = batch.stdout.readline().split()
            if len(header) != 3:
                raise RuntimeError("Git object missing or unreadable")
            _, kind, size = header
            size = int(size)
            data = batch.stdout.read(size) if size <= limit else None
            if data is None:
                for start in range(0, size, 1024 * 1024):
                    batch.stdout.read(min(1024 * 1024, size - start))
            if batch.stdout.read(1) != b"\n":
                raise RuntimeError("Git object stream ended unexpectedly")
            if kind != b"blob":
                continue
            counts["blobs"] += 1
            binary = data is not None and b"\0" in data[:8192]
            counts["oversize" if data is None else "binary" if binary else "text"] += 1
            suffix = PurePosixPath(path).suffix.lower()
            checks = []
            if DATABASE.search(path) or (data or b"").startswith(b"SQLite format 3\0"):
                checks.append(("block", "database-file", None))
            if suffix in BUSINESS:
                counts["manual_business_review"] += 1
            if data is not None and not binary:
                for rule, pattern in RULES.items():
                    for match in re.finditer(pattern, data):
                        checks.append(("block", rule, data.count(b"\n", 0, match.start()) + 1))
                for match in CONNECTION.finditer(data):
                    checks.append(("review", "connection-with-password", data.count(b"\n", 0, match.start()) + 1))
            for severity, rule, line in checks:
                findings.append({"severity": severity, "rule": rule, "blob": oid.decode(), "path": safe_path(path), "line": line})
    return counts, findings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--candidate")
    selection.add_argument("--range")
    selection.add_argument("--public-history", action="store_true")
    parser.add_argument("--remote", help="Tracking namespace for --public-history (default: origin)")
    args = parser.parse_args()
    if args.remote and not args.public_history:
        parser.error("--remote requires --public-history")
    for revision in (args.candidate, args.range):
        if revision and revision.startswith("-"):
            parser.error("Expected a Git revision or range")
    try:
        root = git("rev-parse", "--show-toplevel").decode().strip()
        coverage, commits = scope(root, args)
        coverage["commits"] = len(commits)
        counts, findings = scan(root, objects(root, coverage["mode"], commits), 4 * 1024 * 1024)
    except ValueError as error:
        print(json.dumps({"status": "incomplete", "error": str(error)}))
        return 2
    except (RuntimeError, subprocess.CalledProcessError, OSError):
        print(json.dumps({"status": "incomplete", "error": "Check Git repository, revisions, tracking refs and complete history."}))
        return 2
    print(json.dumps({"scope": coverage, "counts": counts, "findings": findings}, ensure_ascii=True))
    return int(any(item["severity"] == "block" for item in findings))


if __name__ == "__main__":
    raise SystemExit(main())
