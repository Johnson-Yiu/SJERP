"""Publish an isolated run without exposing temporary sessions or secrets.

The source must be a task-owned evidence directory. Existing files are never
removed or overwritten. Original byte hashes are retained for comparison.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[3]
REPORT = Path(__file__).resolve().parent
TEXT = {".log", ".json", ".txt", ".md"}
BINARY = {".png", ".jpg", ".jpeg", ".xlsx", ".pdf", ".csv"}
TOKEN = re.compile(r"\b[0-9a-f]{48}\b")
ASSIGN = re.compile(r"(?i)((?:sessionid|csrfmiddlewaretoken|authorization|password|secret_key)\s*['\"]?\s*[:=]\s*['\"])([^'\"\s,}]+)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--name", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,49}", args.name):
        parser.error("name must be a lowercase directory name")
    source = args.source.resolve(strict=True)
    if not source.is_dir() or not source.is_relative_to((ROOT / ".tmp").resolve()) or "docs/uat-evidence/" not in source.as_posix().lower():
        raise SystemExit("source must be an existing task evidence directory")
    dest = REPORT / args.name
    dest.mkdir(exist_ok=False)
    items, omitted = [], []
    for p in sorted(source.rglob("*")):
        if p.is_symlink():
            raise RuntimeError(f"symlink refused: {p}")
        if not p.is_file():
            continue
        relative = p.relative_to(source)
        if p.suffix.lower() not in TEXT | BINARY:
            omitted.append({"path": relative.as_posix(), "reason": "database, archive or unsupported binary retained only locally"})
            continue
        raw = p.read_bytes()
        if p.suffix.lower() in TEXT:
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                omitted.append({"path": relative.as_posix(), "reason": "non-UTF-8 text requires manual review"})
                continue
            text, n1 = TOKEN.subn("[redacted ephemeral isolation token]", text)
            text, n2 = ASSIGN.subn(r"\1[redacted]", text)
            published = ("\n".join(line.rstrip() for line in text.splitlines()).rstrip() + "\n").encode("utf-8")
            redactions = n1 + n2
        else:
            if p.suffix.lower() == ".csv":
                content = raw.decode("utf-8-sig", errors="replace")
                if TOKEN.search(content) or ASSIGN.search(content):
                    omitted.append({"path": relative.as_posix(), "reason": "CSV requires manual secret review; original retained locally"})
                    continue
            published, redactions = raw, 0
        target = dest / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(published)
        items.append({"path": relative.as_posix(), "bytes": len(raw), "raw_sha256": hashlib.sha256(raw).hexdigest(),
                      "published_sha256": hashlib.sha256(published).hexdigest(), "redactions": redactions})
    manifest = {"source": str(source), "raw_retained_locally": True, "items": items, "omitted": omitted,
                "scope": "Synthetic evidence only; skipped databases and archives may contain temporary sessions."}
    (dest / "publication-manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"published": len(items), "omitted": len(omitted), "redactions": sum(x["redactions"] for x in items)}))


if __name__ == "__main__":
    main()
