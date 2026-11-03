"""Read-only comparison of this interpreter with this worktree's runtime lock."""
import importlib.metadata
import json
from pathlib import Path
import platform
import sys

lock = Path(__file__).resolve().parents[3] / "backend" / "requirements.lock"
rows = []
for line in lock.read_text(encoding="utf-8").splitlines():
    if "==" not in line or line.startswith("#"):
        continue
    name, expected = line.strip().split("==")
    actual = importlib.metadata.version(name)
    rows.append({"name": name, "expected": expected, "actual": actual, "matches": actual == expected})
print(json.dumps({"executable": sys.executable, "implementation": platform.python_implementation(), "version": platform.python_version(), "lock": str(lock), "pins": rows}, indent=2))
assert platform.python_implementation() == "CPython" and platform.python_version() == "3.12.16"
assert len(rows) == 16 and all(row["matches"] for row in rows)
