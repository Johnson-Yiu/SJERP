"""Export exact Git identity and backend/templates objects for offline backup."""
import argparse
import hashlib
from pathlib import Path
import subprocess


def git(*args, **kwargs):
    return subprocess.run(["git", *args], check=True, **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("commit")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    commit = git("rev-parse", "--verify", args.commit + "^{commit}",
                 capture_output=True, text=True).stdout.strip()
    tree = git("rev-parse", commit + "^{tree}", capture_output=True, text=True).stdout.strip()
    entries = git("ls-tree", "-rtz", commit, capture_output=True).stdout.split(b"\0")
    objects = {commit.encode(), tree.encode()}
    for entry in filter(None, entries):
        metadata, path = entry.split(b"\t", 1)
        _, kind, object_id = metadata.split()
        if kind == b"tree" or path in {b".gitignore", b".gitattributes"} or path.startswith((b"backend/", b"templates/")):
            objects.add(object_id)
    with args.output.open("xb") as handle:
        git("pack-objects", "--stdout", input=b"\n".join(sorted(objects)) + b"\n", stdout=handle)
    with args.output.open("rb") as handle:
        print(commit, hashlib.file_digest(handle, "sha256").hexdigest())


if __name__ == "__main__":
    main()
