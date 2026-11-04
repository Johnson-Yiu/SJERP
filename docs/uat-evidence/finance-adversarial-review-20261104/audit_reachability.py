"""Reproducible finite source inventory, not proof about arbitrary plugins."""
import hashlib
import json
from pathlib import Path
import re

repo = Path(__file__).resolve().parents[3]
rows = []
for file in sorted((repo / "backend").rglob("*.py")):
    relative = file.relative_to(repo).as_posix()
    if any(part in {"tests", "migrations", "__pycache__", ".venv"} for part in file.parts):
        continue
    text = file.read_text(encoding="utf-8-sig")
    hits = [{"line": line, "text": value.strip()} for line, value in enumerate(text.splitlines(), 1)
            if re.search(r"FinanceFact|FinanceInstruction|finance_closeout|bulk_create|admin\.site\.register", value)]
    if hits:
        rows.append({"file": relative, "sha256_git_lf": hashlib.sha256(file.read_bytes().replace(b"\r\n", b"\n")).hexdigest(), "hits": hits})
out = Path(__file__).resolve().parent / "reachability.json"
out.write_text(json.dumps({"scope": "tracked/current backend Python except tests/migrations; finite static inventory", "files": rows}, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
print(json.dumps({"indexed_files": len(rows)}))
