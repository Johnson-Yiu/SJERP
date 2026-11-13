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


def git(*args):
    return subprocess.check_output(["git", *args])


def objects(args):
    if args.range or args.public_history:
        revisions = ["--remotes=sjerp"] if args.public_history else [args.range]
        output = git("rev-list", "--objects", "--missing=error", *revisions, "--")
        for line in output.splitlines():
            oid, sep, name = line.partition(b" ")
            if sep:
                yield oid, name.decode("utf-8", "replace")
        return
    for entry in git("ls-tree", "-rz", args.candidate or "HEAD", "--").split(b"\0"):
        if entry:
            header, name = entry.split(b"\t", 1)
            _, kind, oid = header.split()
            if kind == b"blob":
                yield oid, name.decode("utf-8", "replace")


def safe_path(path):
    data = path.encode("utf-8")
    for pattern in (*RULES.values(), CONNECTION):
        data = re.sub(pattern, b"[redacted]", data)
    return data.decode("utf-8")


def scan(entries, limit):
    counts = Counter()
    findings = []
    with subprocess.Popen(["git", "cat-file", "--batch"], stdin=subprocess.PIPE, stdout=subprocess.PIPE) as batch:
        for oid, path in entries:
            batch.stdin.write(oid + b"\n")
            batch.stdin.flush()
            _, kind, size = batch.stdout.readline().split()
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
    args = parser.parse_args()
    for revision in (args.candidate, args.range):
        if revision and revision.startswith("-"):
            parser.error("Expected a Git revision or range")
    counts, findings = scan(objects(args), 4 * 1024 * 1024)
    print(json.dumps({"counts": counts, "findings": findings}, ensure_ascii=True))
    return int(any(item["severity"] == "block" for item in findings))


if __name__ == "__main__":
    raise SystemExit(main())
