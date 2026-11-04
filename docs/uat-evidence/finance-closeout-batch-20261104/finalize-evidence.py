"""Publish test output with only disposable credentials and whitespace redacted."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

root = Path(__file__).resolve().parent
repo = root.parents[2]
patterns = [
    (r"(?i)(['\"](?:token|password|secret_key)['\"]\s*:\s*['\"])[^'\"]+", r"\1[REDACTED]"),
    (r"(/api/__test__/isolation/)[a-f0-9]+", r"\1[REDACTED]"),
    (r"(?i)(postgres(?:ql)?://[^:/\s]+:)[^@\s]+@", r"\1[REDACTED]@"),
]
logs = []
for source in sorted(root.glob("*.log")):
    if ".redacted." in source.name:
        continue
    text = source.read_text(encoding="utf-8-sig", errors="replace")
    for expression, replacement in patterns:
        text = re.sub(expression, replacement, text)
    text = "\n".join(line.rstrip() for line in text.splitlines()).rstrip() + "\n"
    dest = root / (source.stem.replace(".private", "") + ".redacted.log")
    dest.write_text(text, encoding="utf-8", newline="\n")
    logs.append({"original": source.name, "original_sha256": hashlib.sha256(source.read_bytes()).hexdigest(), "published": dest.name})
extensions = {".png", ".pdf", ".csv", ".json", ".md", ".py"}
files = []
for item in sorted(root.rglob("*")):
    if not item.is_file() or item.name in {"evidence-manifest.json", "fixture.json"} or "artifacts" in item.parts or "__pycache__" in item.parts:
        continue
    if item.suffix not in extensions and not item.name.endswith(".redacted.log"):
        continue
    data = item.read_bytes()
    files.append({"path": item.relative_to(root).as_posix(), "size": len(data), "sha256": hashlib.sha256(data).hexdigest()})
head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
(root / "evidence-manifest.json").write_text(json.dumps({"source_head": head, "logs": logs, "files": files}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(json.dumps({"source_head": head, "published_logs": len(logs), "evidence_files": len(files)}))
