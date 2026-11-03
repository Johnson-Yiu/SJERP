"""Run the previous unmodified PG drill inside a new CLI-owned cluster.

This is a local synthetic regression harness, not a production backup entry.
Pass the same arguments as backend/isolated_postgres_drill.py.
"""
import os
import runpy
import subprocess
import sys
from pathlib import Path

repository = Path(__file__).resolve().parents[3]
backend = repository / "backend"
if os.environ.get("APP_STAGE", "development").strip().lower() != "development":
    raise SystemExit("This synthetic regression requires development stage")
if os.environ.get("DATABASE_URL") and not os.environ["DATABASE_URL"].startswith("sqlite://"):
    raise SystemExit("This synthetic regression requires isolated SQLite parent settings")
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
sys.path.insert(0, str(backend))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()
from crm.services.postgres_drill_backup import IsolatedPostgresDrill

original_backup = IsolatedPostgresDrill.backup


def run_existing_then_backup(drill, **kwargs):
    env = os.environ.copy()
    env.update(ISS018_DRILL_ROOT=str(drill.root), ISS018_DRILL_PASSWORD_FILE=str(drill.root / "secret"),
               ISS018_DRILL_PORT=str(drill.port), ISS018_DRILL_APP_SHA=drill.app_sha,
               DATABASE_URL="sqlite:///:memory:")
    run = subprocess.run([sys.executable, str(backend / "manage.py"), "test",
                          "crm.tests.test_postgres_drill_backup", "--verbosity", "2"],
                         cwd=backend, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace",
                         timeout=600)
    # The fixture prints only synthetic business results. Never print credentials.
    for output in (run.stdout, run.stderr):
        print(output.replace(drill._password, "[REDACTED]"), end="", flush=True)
    print(f"EXISTING_DRILL_EXIT={run.returncode}", flush=True)
    if run.returncode:
        raise RuntimeError(f"Existing isolated PostgreSQL regression failed: exit {run.returncode}")
    return original_backup(drill, **kwargs)


IsolatedPostgresDrill.backup = run_existing_then_backup
runpy.run_path(str(backend / "isolated_postgres_drill.py"), run_name="__main__")
