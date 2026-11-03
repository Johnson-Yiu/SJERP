"""Read-only source audit runner; all databases are disposable in-memory SQLite."""
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
env = os.environ.copy()
env.update(DATABASE_URL="sqlite:///:memory:", APP_STAGE="development",
           PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8")
env["MEDIA_ROOT"] = tempfile.mkdtemp(prefix="iss037-audit-media-")
env["PYTHONPATH"] = str(HERE) + os.pathsep + str(ROOT / "backend")
commands = [
    [sys.executable, "manage.py", "test", "crm.tests.test_formal_party_snapshots",
     "crm.tests.test_contract_lifecycle", "crm.tests.test_quotes",
     "crm.tests.test_quote_revision_tree", "crm.tests.test_iss020_quote_export",
     "crm.tests.test_procurement", "crm.tests.test_purchase_order_related_orders",
     "crm.tests.test_cash_events.CashMigrationTests.test_additive_migration_preserves_historical_rows_and_decimal_fields",
     "--verbosity", "2", "--noinput"],
    [sys.executable, "manage.py", "test", "snapshot_probe", "--verbosity", "2", "--noinput"],
    [sys.executable, "manage.py", "makemigrations", "crm", "--check", "--dry-run"],
]
if "--probe-only" in sys.argv:
    commands = [commands[1]]
archive_name = "probe-rerun-raw.zip" if "--probe-only" in sys.argv else "raw-evidence.zip"
if "--migration-only" in sys.argv:
    commands = [[sys.executable, "manage.py", "test", "migration_probe", "--verbosity", "2", "--noinput"]]
    archive_name = "migration-raw.zip"
if "--verification-only" in sys.argv:
    commands = [["git", "rev-parse", "HEAD"], ["git", "status", "--short", "--untracked-files=all"],
                ["git", "diff", "--exit-code"], ["git", "diff", "--cached", "--exit-code"],
                ["git", "diff", "--check"],
                [sys.executable, "-c", "import django,sqlite3,platform; print(platform.python_version(), django.get_version(), sqlite3.sqlite_version)"]]
    archive_name = "final-verification-raw.zip"
with zipfile.ZipFile(HERE / archive_name, "w", zipfile.ZIP_DEFLATED) as archive:
    metadata = {"python": platform.python_version(), "executable": sys.executable,
                "cwd": str(ROOT / "backend"), "database_url": env["DATABASE_URL"],
                "app_stage": env["APP_STAGE"], "media_root": env["MEDIA_ROOT"],
                "bytecode": False}
    archive.writestr("environment.json", json.dumps(metadata, ensure_ascii=False, indent=2))
    print(json.dumps(metadata, ensure_ascii=False), flush=True)
    for index, command in enumerate(commands, 1):
        print("COMMAND", index, command, flush=True)
        result = subprocess.run(command, cwd=ROOT / "backend", env=env,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        archive.writestr(f"{index}-stdout-stderr.log", result.stdout)
        archive.writestr(f"{index}-command.json", json.dumps({"argv": command, "exit": result.returncode}))
        print(result.stdout.decode("utf-8", errors="replace")[-4500:], flush=True)
        print("EXIT", result.returncode, flush=True)
