"""Capture reproducible integration checks without touching business databases."""
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import zipfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
env = os.environ.copy()
env.update(APP_STAGE="development", DATABASE_URL="sqlite:///:memory:",
           MEDIA_ROOT=tempfile.mkdtemp(prefix="rule-gap-integration-media-"),
           PYTHONUTF8="1", PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
env.update(ISOLATED_TEST_PYTHON=sys.executable)
mode = sys.argv[1] if len(sys.argv) > 1 else "environment"
if mode == "chrome":
    env.update(ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT=str(HERE), PLAYWRIGHT_CHANNEL="chrome")
else:
    # Node's parallel-worktree self-test owns distinct repository/evidence roots.
    env.pop("ISOLATED_PLAYWRIGHT_EVIDENCE_ROOT", None)
commands = {
    "environment": [(ROOT, [sys.executable, "-m", "pip", "check"])],
    "node": [(ROOT / "frontend", ["node", "--test"])],
    "backend": [(ROOT / "backend", [sys.executable, "manage.py", "check"]),
                (ROOT / "backend", [sys.executable, "manage.py", "makemigrations", "--check", "--dry-run"]),
                (ROOT / "backend", [sys.executable, "manage.py", "test", "--verbosity", "2", "--noinput"])],
    "frontend": [(ROOT / "frontend", ["node", "--test"]),
                 (ROOT / "frontend", ["node", "--test", "tests/detail-drawer-typography.spec.js"]),
                 (ROOT / "frontend", ["node", "node_modules/vitest/vitest.mjs", "run", "tests", "--environment", "jsdom", "--exclude", "tests/detail-drawer-typography.spec.js"]),
                 (ROOT / "frontend", ["node", "node_modules/vite/bin/vite.js", "build"])],
    "chrome": [(ROOT / "frontend", ["node", "scripts/run-isolated-browser-tests.mjs", "--business-test", "independent-bank-fee-real.spec.js"]),
               (ROOT / "frontend", ["node", "scripts/run-isolated-browser-tests.mjs", "--business-test", "iss039-amount-allocation-real.spec.js"])],
}
if mode not in commands:
    raise SystemExit("Expected environment, backend, frontend, node or chrome")
pins = []
for line in (ROOT / "backend/requirements.lock").read_text().splitlines():
    if line.strip() and not line.startswith("#"):
        name, expected = line.strip().split("==")
        actual = importlib.metadata.version(name)
        pins.append({"name": name, "expected": expected, "actual": actual})
        if actual != expected:
            raise SystemExit(f"Lock mismatch: {name}")
metadata = {"python": platform.python_version(), "executable": sys.executable,
            "database": env["DATABASE_URL"], "media_root": env["MEDIA_ROOT"], "pins": pins}
results = []
with zipfile.ZipFile(HERE / f"{mode}-raw.zip", "w", zipfile.ZIP_DEFLATED) as archive:
    archive.writestr("environment.json", json.dumps(metadata, indent=2))
    for index, (cwd, command) in enumerate(commands[mode], 1):
        print("RUN", command, flush=True)
        result = subprocess.run(command, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        archive.writestr(f"{index}-raw.log", result.stdout)
        record = {"argv": command, "cwd": str(cwd), "exit": result.returncode}
        results.append(record)
        archive.writestr(f"{index}-command.json", json.dumps(record))
        print(result.stdout.decode("utf-8", errors="replace")[-4000:], flush=True)
        print("EXIT", result.returncode, flush=True)
    archive.writestr("results.json", json.dumps(results, indent=2))
sys.exit(any(row["exit"] != 0 for row in results))
