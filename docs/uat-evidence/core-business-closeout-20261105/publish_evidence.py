"""Publish normalized disposable-test logs and a byte-verifiable manifest."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

root = Path(__file__).resolve().parent
repo = root.parents[2]
logs = []
for original in sorted(root.glob("*.log")):
    if original.name.endswith(".published.log"):
        continue
    raw = original.read_bytes()
    value = raw.decode("utf-8-sig", errors="replace")
    value = re.sub(r"(?i)(postgres(?:ql)?://[^:/\s]+:)[^@\s]+@", r"\1[REDACTED]@", value)
    value = re.sub(r"(/api/__test__/isolation/)[a-f0-9]+", r"\1[REDACTED]", value)
    value = re.sub(r"(?i)((?:DJANGO_SECRET_KEY|POSTGRES_PASSWORD|PGPASSWORD)\s*[:=]\s*)[^\s]+", r"\1[REDACTED]", value)
    value = re.sub(r"(?i)(['\"]token['\"]\s*:\s*['\"])[^'\"]+", r"\1[REDACTED]", value)
    value = "\n".join(line.rstrip() for line in value.splitlines()).rstrip() + "\n"
    published = root / (original.stem + ".published.log")
    published.write_text(value, encoding="utf-8", newline="\n")
    logs.append({"original": original.name, "original_sha256": hashlib.sha256(raw).hexdigest(), "original_size": len(raw), "published": published.name})
files = []
for file in sorted(root.rglob("*")):
    if not file.is_file() or "__pycache__" in file.parts or file.name == "manifest.json" or any(part.startswith("browser-runtime") for part in file.relative_to(root).parts):
        continue
    if file.suffix not in {".py", ".md", ".json", ".png"} and not file.name.endswith(".published.log"):
        continue
    data = file.read_bytes()
    # Git text normalization is LF on Windows and Linux; binary downloads are
    # embedded in the response JSON as text or compared by SHA in tests.
    if file.suffix != ".png":
        data = data.replace(b"\r\n", b"\n")
    files.append({"path": file.relative_to(root).as_posix(), "bytes": len(data), "sha256_git_lf": hashlib.sha256(data).hexdigest()})
head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
(root / "manifest.json").write_text(json.dumps({"baseline": "bcdcb57545f121b8a4102f352c74008b47372035", "source_checkpoint": head, "normalization": "text LF; PNG bytes unchanged; only ephemeral auth redaction; no business expectation rewriting", "logs": logs, "files": files}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
print(json.dumps({"published_logs": len(logs), "evidence_files": len(files)}))
