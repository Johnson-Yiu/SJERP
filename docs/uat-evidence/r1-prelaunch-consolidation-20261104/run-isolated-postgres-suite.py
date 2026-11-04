"""Run the Django PostgreSQL suite only in a newly created ISS-018 drill cluster."""
import os
import runpy
import subprocess
import sys
from pathlib import Path

repository = Path(__file__).resolve().parents[3]
backend = repository / "backend"
if os.environ.get("APP_STAGE", "development").strip().lower() != "development":
    raise SystemExit("Isolated regression requires development stage")
if os.environ.get("DATABASE_URL") and not os.environ["DATABASE_URL"].startswith("sqlite://"):
    raise SystemExit("Parent process requires isolated SQLite settings")
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
sys.path.insert(0, str(backend))
import django
django.setup()
from crm.services.postgres_drill_backup import IsolatedPostgresDrill

original_backup = IsolatedPostgresDrill.backup


def run_tests_then_backup(drill, **kwargs):
    drill._assert_cluster()
    # Django tests can write temporary uploads. Never point them at the source
    # media whose before/after manifest the enclosing drill is checking.
    test_media = drill.root / "media-postgres-suite"
    test_media.mkdir(mode=0o700)
    env = drill._environment(drill.source, test_media)
    for name in ("ISS018_DRILL_ROOT", "ISS018_DRILL_PASSWORD_FILE", "ISS018_DRILL_PORT",
                 "ISS018_DRILL_APP_SHA", "ISS018_COMMAND_PG_BIN"):
        env.pop(name, None)
    run = subprocess.run([sys.executable, str(backend / "manage.py"), "test", "--verbosity", "1"],
                         cwd=backend, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace",
                         timeout=1800)
    for output in (run.stdout, run.stderr):
        print(output.replace(drill._password, "[REDACTED]"), end="", flush=True)
    print(f"POSTGRES_FULL_TEST_EXIT={run.returncode}", flush=True)
    if run.returncode:
        raise RuntimeError(f"Isolated PostgreSQL suite failed: exit {run.returncode}")
    return original_backup(drill, **kwargs)


IsolatedPostgresDrill.backup = run_tests_then_backup
runpy.run_path(str(backend / "isolated_postgres_drill.py"), run_name="__main__")
