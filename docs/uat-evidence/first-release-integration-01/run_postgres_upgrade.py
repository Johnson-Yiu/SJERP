"""Run the first-release migration upgrade and focused PostgreSQL checks in an owned PG17 cluster."""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from urllib.parse import quote

import psycopg
from psycopg import sql


REPORT = Path(os.environ.get(
    "SUNJACK_PG_REPORT_DIR",
    str(Path(__file__).resolve().parent / "postgres"),
)).resolve()
REPORT.mkdir(parents=True, exist_ok=True)
REPO = Path(__file__).resolve().parents[3]
BACKEND = REPO / "backend"
PG_BIN = Path(os.environ.get(
    "SUNJACK_PG_BIN",
    r"C:\Users\Johnson\AppData\Local\Temp\sunjack-history-pg17-isolated-20261105\binaries\pgsql\bin",
)).resolve()
ROOT = Path(tempfile.mkdtemp(prefix="sunjack-first-release-int01-pg-")).resolve()
MARKER = uuid.uuid4().hex
SECRET = secrets.token_urlsafe(32)
ROLE = "fr01_" + uuid.uuid4().hex[:12]
DATABASE = "fr01_db_" + uuid.uuid4().hex[:12]
(ROOT / "owner.json").write_text(json.dumps({"marker": MARKER}), encoding="utf-8")
(ROOT / "password").write_text(SECRET, encoding="ascii")
(ROOT / "media").mkdir()

ENV = {key: value for key, value in os.environ.items() if not key.upper().startswith("PG")}
ENV.update(
    APP_STAGE="development",
    DEVELOPMENT_SUPERADMIN="1",
    RBAC_ENFORCEMENT="0",
    AUDIT_LOG_ENABLED="0",
    PYTHONDONTWRITEBYTECODE="1",
    PYTHONUTF8="1",
    MEDIA_ROOT=str(ROOT / "media"),
)
for key in ("ISS018_COMMAND_PG_BIN", "ISS018_DRILL_ROOT", "ISS018_DRILL_PASSWORD_FILE"):
    ENV.pop(key, None)


def source_hashes():
    listed = subprocess.check_output(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=REPO,
    )
    result = {}
    for raw in listed.split(b"\0"):
        if not raw:
            continue
        rel = raw.decode("utf-8")
        if not (rel.startswith("backend/") or rel.startswith("frontend/")):
            continue
        path = REPO / rel
        if path.is_file():
            result[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


BEFORE = source_hashes()
RESULT = {
    "head_before_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
    "tree_source_hash_count": len(BEFORE),
    "pg_bin": str(PG_BIN),
    "stages": {},
    "cleanup": "not-started",
}
TEST_LABELS = os.environ.get("SUNJACK_PG_TEST_LABELS", "").split()
STARTED = False


def stage(name: str, args: list[str], *, cwd: Path = BACKEND, env=None, timeout=1200):
    path = REPORT / f"{name}.log"
    with path.open("wb") as stream:
        completed = subprocess.run(args, cwd=cwd, env=env or ENV, stdout=stream, stderr=subprocess.STDOUT, timeout=timeout)
    RESULT["stages"][name] = completed.returncode
    print(f"{name}: {completed.returncode}", flush=True)
    return completed.returncode


def pg_tool(name: str, *args: str, timeout=180):
    return stage(name, [str(PG_BIN / f"{name.split('-')[0]}.exe"), *args], cwd=REPO, timeout=timeout)


try:
    for required in ("initdb.exe", "pg_ctl.exe", "postgres.exe"):
        if not (PG_BIN / required).is_file():
            raise RuntimeError(f"Missing PostgreSQL binary: {PG_BIN / required}")
    version = subprocess.check_output([str(PG_BIN / "pg_ctl.exe"), "--version"], text=True).strip()
    RESULT["server_binary"] = version
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        PORT = sock.getsockname()[1]
    if PORT == 5432:
        raise RuntimeError("Refusing the conventional shared PostgreSQL port")
    RESULT["port"] = PORT
    if pg_tool("initdb", "-D", str(ROOT / "data"), "-U", ROLE, "--pwfile", str(ROOT / "password"), "--auth=scram-sha-256", "-E", "UTF8", "--locale=C"):
        raise RuntimeError("initdb failed")
    if pg_tool("pg_ctl-start", "-D", str(ROOT / "data"), "-l", str(ROOT / "postgres.log"), "-o", f"-h 127.0.0.1 -p {PORT}", "-w", "start"):
        raise RuntimeError("pg_ctl start failed")
    STARTED = True
    with psycopg.connect(host="127.0.0.1", port=PORT, user=ROLE, password=SECRET, dbname="postgres", autocommit=True) as conn:
        actual = Path(conn.execute("SHOW data_directory").fetchone()[0]).resolve()
        if actual != (ROOT / "data").resolve():
            raise RuntimeError("Started PostgreSQL cluster identity did not match the owned temporary directory")
        RESULT["server_version"] = conn.execute("SHOW server_version").fetchone()[0]
        if not RESULT["server_version"].startswith("17."):
            raise RuntimeError("PostgreSQL 17 is required")
        RESULT["cluster_identity_verified"] = True
        conn.execute(sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(sql.Identifier(DATABASE)))

    ENV["DATABASE_URL"] = f"postgresql://{ROLE}:{quote(SECRET, safe='')}@127.0.0.1:{PORT}/{DATABASE}"
    commands = [
        ("migrate-reminder-baseline", [sys.executable, "manage.py", "migrate", "crm", "0109_new_product_reminders", "--noinput", "--verbosity", "2"]),
        ("seed-old-snapshot-and-reminder", [sys.executable, "manage.py", "shell", "-c", """
from datetime import date
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
state = MigrationExecutor(connection).loader.project_state([('crm', '0109_new_product_reminders')]).apps
Customer = state.get_model('crm', 'Customer')
Quote = state.get_model('crm', 'Quote')
Reminder = state.get_model('crm', 'NewProductReminder')
customer = Customer.objects.create(code='FR01-OLD', name='Synthetic legacy buyer')
Quote.objects.create(quote_no='FR01-OLD', customer=customer, quote_date=date(2020, 1, 2), buyer_company_name='Saved legacy buyer', recipient_name='Saved recipient', buyer_address='Saved historical address')
Reminder.objects.create(customer=customer, requirement='Synthetic reminder preserved through upgrade')
print('SEEDED_0109_OLD_QUOTE_AND_REMINDER')
"""]),
        ("migrate-current", [sys.executable, "manage.py", "migrate", "--noinput", "--verbosity", "2"]),
        ("migration-check", [sys.executable, "manage.py", "migrate", "--check"]),
        ("models-check", [sys.executable, "manage.py", "makemigrations", "--check", "--dry-run"]),
        ("verify-old-snapshot", [sys.executable, "manage.py", "shell", "-c", """
from crm.models import Quote, NewProductReminder
from django.db.migrations.recorder import MigrationRecorder
q = Quote.objects.get(quote_no='FR01-OLD')
assert (q.buyer_company_name, q.recipient_name, q.buyer_address) == ('Saved legacy buyer', 'Saved recipient', 'Saved historical address')
assert q.buyer_tax_id is None
assert NewProductReminder.objects.filter(requirement='Synthetic reminder preserved through upgrade').count() == 1
applied = set(MigrationRecorder.Migration.objects.filter(app='crm').values_list('name', flat=True))
assert {'0109_new_product_reminders', '0118_merge_party_reminders'} <= applied
print('PASS saved buyer snapshots unchanged; buyer_tax_id remains NULL; reminder retained; merge migration applied')
"""]),
        ("party-and-quote-postgres-tests", [sys.executable, "manage.py", "test",
            *(TEST_LABELS or [
            "crm.tests.test_party_request_lifecycle", "crm.tests.test_party_request_lifecycle_migration",
            "crm.tests.test_party_pg_cleanup", "crm.tests.test_postgres_test_isolation",
            "crm.tests.test_party_document_version", "crm.tests.test_party_document_version_pg",
            "crm.tests.test_party_quote_application", "crm.tests.test_party_version_service",
            "crm.tests.test_party_version_concurrency", "crm.tests.test_quote_party_approval_guard",
            "crm.tests.test_quote_party_change_api", "crm.tests.test_quote_party_fingerprint_versions",
            "crm.tests.test_party_version_migrations", "crm.tests.test_party_version_current_baseline",
            "crm.tests.test_party_lifecycle_api_closeout", "crm.tests.test_party_document_api_closeout",
            "crm.tests.test_quote_details_pi_export", "crm.tests.test_quote_template_snapshot",
            "crm.tests.test_party_document_details", "crm.tests.test_party_details_concurrency",
            "crm.tests.test_quote_details_formal_guard", "crm.tests.test_party_replacement",
            "crm.tests.test_party_replacement_pg", "crm.tests.test_party_replacement_migration",
            "crm.tests.test_party_replacement_creation_blockers", "crm.tests.test_quote_buyer_tax_id",
            "crm.tests.test_quote_buyer_country_snapshot", "crm.tests.test_quote_draft_tax_revision",
            "crm.tests.test_new_product_reminders", "crm.tests.test_dashboard_import"]),
            "--noinput", "--verbosity", "2"]),
    ]
    for name, args in commands:
        if stage(name, args, timeout=1800):
            RESULT["failed"] = True
            if name in {"migrate-current", "verify-old-snapshot", "party-and-quote-postgres-tests"}:
                break

    with psycopg.connect(host="127.0.0.1", port=PORT, user=ROLE, password=SECRET, dbname="postgres") as conn:
        leaked = [row[0] for row in conn.execute("SELECT datname FROM pg_database WHERE datname LIKE 'test_fr01_%'").fetchall()]
        RESULT["remaining_test_databases"] = leaked
        if leaked:
            RESULT["failed"] = True
except Exception as error:
    RESULT["error"] = str(error).replace(SECRET, "[REDACTED]")
    RESULT["failed"] = True
finally:
    try:
        AFTER = source_hashes()
        RESULT["source_hashes_match"] = BEFORE == AFTER
        RESULT["source_paths_changed"] = sorted(path for path in set(BEFORE) | set(AFTER) if BEFORE.get(path) != AFTER.get(path))
        if BEFORE != AFTER:
            RESULT["failed"] = True
    except Exception as error:
        RESULT["source_hash_error"] = str(error)
        RESULT["failed"] = True
    if STARTED:
        try:
            result = pg_tool("pg_ctl-stop", "-D", str(ROOT / "data"), "-m", "fast", "-w", "stop")
            if result:
                raise RuntimeError("pg_ctl stop failed")
            STARTED = False
        except Exception as error:
            RESULT["cleanup_error"] = str(error).replace(SECRET, "[REDACTED]")
            RESULT["failed"] = True
    if not STARTED:
        try:
            if ROOT.parent != Path(tempfile.gettempdir()).resolve() or not ROOT.name.startswith("sunjack-first-release-int01-pg-"):
                raise RuntimeError("Refusing to clean a path outside this run's owned temp directory")
            if json.loads((ROOT / "owner.json").read_text(encoding="utf-8"))["marker"] != MARKER:
                raise RuntimeError("Refusing to clean a temp directory with a mismatched ownership marker")
            shutil.rmtree(ROOT)
            RESULT["cleanup"] = "complete"
        except Exception as error:
            RESULT["cleanup_error"] = str(error).replace(SECRET, "[REDACTED]")
            RESULT["failed"] = True
    (REPORT / "result.json").write_text(json.dumps(RESULT, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(RESULT, ensure_ascii=False), flush=True)

sys.exit(1 if RESULT.get("failed") else 0)
