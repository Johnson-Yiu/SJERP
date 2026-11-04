"""Supplemental source-state invariance drill; not a full ERP acceptance run.

The full1410 suites are separately preserved. This runs six original permission
tests plus populated restore verification and an explicit final source reread.
Every existing owned-cluster and clean-application guard remains unchanged.
"""
import os
import hashlib
import json
from pathlib import Path
import runpy
import subprocess
import sys
import socket
import time
from urllib.request import Request, build_opener, ProxyHandler
from urllib.error import HTTPError, URLError
from uuid import uuid4

repository = Path(__file__).resolve().parents[3]
backend = repository / "backend"
if os.environ.get("APP_STAGE", "development") != "development":
    raise SystemExit("Requires development stage and synthetic data")
if os.environ.get("DATABASE_URL") and not os.environ["DATABASE_URL"].startswith("sqlite://"):
    raise SystemExit("Refusing an inherited non-SQLite database target")
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
evidence_root = Path(os.environ.get("REVIEW_EVIDENCE_ROOT", Path(__file__).resolve().parent)).resolve()
if not evidence_root.is_relative_to(repository.resolve()):
    raise SystemExit("Evidence output must remain inside this checkout")
(evidence_root / "logs").mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(backend))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()
from crm.services.postgres_drill_backup import IsolatedPostgresDrill
from crm.services.operations_postgres import database_state, verify_media_references
from crm.services.private_media import build_private_media_manifest
from psycopg import Error as PsycopgError, sql

if os.environ.get('REVIEW_TEST_LABELS') != 'crm.tests.test_finance_integration_permissions':
    raise SystemExit('This supplementary drill requires its explicit six-test label; not a full-suite result')

original_backup = IsolatedPostgresDrill.backup
original_manage = IsolatedPostgresDrill._manage
original_restore = IsolatedPostgresDrill.restore
finance_seed_enabled = os.environ.get("REVIEW_FINANCE_SEED") == "1"
history_seed_enabled = os.environ.get("REVIEW_HISTORY_SEED") == "1"
operational_seed_enabled = os.environ.get("REVIEW_HISTORY_OPERATIONAL_SEED") == "1"
if operational_seed_enabled and not (history_seed_enabled and finance_seed_enabled):
    raise SystemExit("Operational history requires both owned archive and finance seeds")
finance_helper = Path(__file__).resolve().parent / "finance-backup-seed" / "seed_finance_backup.py"
history_helper = Path(__file__).resolve().parent / "seed_history_backup.py"
operational_helper = repository / "docs/uat-evidence/integration-closeout-02/seed_history_operational_backup.py"


def sequences(drill, database):
    with drill._connect(database) as connection:
        names = connection.execute("SELECT sequencename FROM pg_sequences WHERE schemaname='public' ORDER BY sequencename").fetchall()
        return {name: list(connection.execute(sql.SQL("SELECT last_value, is_called FROM public.{}").format(sql.Identifier(name))).fetchone())
                for (name,) in names}


def restored_private_http(drill, restored):
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    env = drill._environment(restored["database"], Path(restored["media"]))
    log_path = evidence_root / "logs" / f"restored-private-http-{drill.app_sha[:12]}.log"
    proof = []
    with log_path.open("wb") as output:
        child = subprocess.Popen([sys.executable, str(backend / "manage.py"), "runserver",
                                  f"127.0.0.1:{port}", "--noreload"], cwd=backend, env=env,
                                 stdout=output, stderr=subprocess.STDOUT)
        try:
            base = f"http://127.0.0.1:{port}"
            opener = build_opener(ProxyHandler({}))
            deadline = time.monotonic() + 30
            while True:
                try:
                    with opener.open(base + "/api/session/current-operator/", timeout=2):
                        break
                except (URLError, TimeoutError):
                    if child.poll() is not None or time.monotonic() > deadline:
                        raise RuntimeError("Owned restored HTTP server did not start")
                    time.sleep(0.1)
            voucher = next(item for item in drill.review_finance_snapshot["private_vouchers"] if item["scope"] == "account")
            download = f"/api/finance-ledger/voucher-download/?id={voucher['id']}"
            cases = [(None, download, 403), ("iss018-drill-denied", download, 403),
                     ("iss018-drill-owner", download, 200),
                     ("iss018-drill-owner", "/media/" + voucher["name"], 404)]
            for username, path, expected in cases:
                headers = {"Cookie": "sessionid=" + drill.review_sessions[username]} if username else {}
                try:
                    response = opener.open(Request(base + path, headers=headers), timeout=10)
                except HTTPError as error:
                    response = error
                with response:
                    body = response.read()
                    status = response.code
                    if status != expected:
                        raise RuntimeError(f"Restored private HTTP expected {expected}, received {status}")
                    if status == 200:
                        if hashlib.sha256(body).hexdigest() != voucher["file_sha256"]:
                            raise RuntimeError("Restored HTTP voucher bytes differ")
                        if response.headers.get("Cache-Control") != "private, no-store":
                            raise RuntimeError("Restored private HTTP cache policy differs")
                    proof.append({"identity": username or "anonymous", "path": path,
                                  "status": status, "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()})
        finally:
            child.terminate()
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=10)
    return proof


def finance_command(function, helper=finance_helper):
    return ("shell", "--no-imports", "-c",
            f"import json, runpy; print(json.dumps(runpy.run_path({str(helper)!r})[{function!r}](), ensure_ascii=False))")


def manage_with_finance_seed(drill, *arguments):
    output = original_manage(drill, *arguments)
    core_seed = "from crm.tests.iss018_drill_fixture import seed; seed()"
    if history_seed_enabled and arguments == ("shell", "--no-imports", "-c", core_seed):
        drill.review_history_snapshot = json.loads(original_manage(drill, *finance_command("seed", history_helper)).strip().splitlines()[-1])
        print("HISTORY_BACKUP_SEED=" + json.dumps(drill.review_history_snapshot), flush=True)
    if finance_seed_enabled and arguments == ("shell", "--no-imports", "-c", core_seed):
        # This hook runs before the original driver's all-table source snapshot.
        # The helper independently rejects any database outside this owned root.
        seeded = json.loads(original_manage(drill, *finance_command("seed")).strip().splitlines()[-1])
        drill.review_finance_snapshot = json.loads(original_manage(drill, *finance_command("verify")).strip().splitlines()[-1])
        drill.review_sessions = json.loads(original_manage(drill, "shell", "--no-imports", "-c",
            "from crm.tests.iss018_drill_fixture import sessions; sessions()").strip().splitlines()[-1])
        drill.review_sequences = sequences(drill, drill.source)
        with drill._connect(drill.source) as connection:
            drill.review_references = verify_media_references(connection, build_private_media_manifest(drill.media))
        print("FINANCE_BACKUP_SEED=" + json.dumps(seeded, ensure_ascii=False), flush=True)
        if operational_seed_enabled:
            drill.review_operational_snapshot = json.loads(original_manage(
                drill, *finance_command("seed", operational_helper)).strip().splitlines()[-1])
            # The operational workflow adds archive, finance, inventory and
            # private-file records. Compare the final complete snapshots.
            drill.review_history_snapshot = json.loads(original_manage(
                drill, *finance_command("verify", history_helper)).strip().splitlines()[-1])
            drill.review_finance_snapshot = json.loads(original_manage(
                drill, *finance_command("verify")).strip().splitlines()[-1])
            drill.review_sequences = sequences(drill, drill.source)
            with drill._connect(drill.source) as connection:
                drill.review_references = verify_media_references(
                    connection, build_private_media_manifest(drill.media))
            print("HISTORY_OPERATIONAL_BACKUP_SEED=" + json.dumps(
                drill.review_operational_snapshot, ensure_ascii=False), flush=True)
    return output


def restored_history_guard_probes(drill, database):
    """Prove restored statement/row guards without committing any mutation."""
    results = []
    with drill._connect(database) as connection:
        before = database_state(connection)
        for table in ("crm_historyinventorybaseline", "crm_historyinventorybaselinereversal",
                      "crm_historyoperationalcontract"):
            row = connection.execute(sql.SQL("SELECT id FROM {} LIMIT 1").format(sql.Identifier(table))).fetchone()
            if row is None:
                raise RuntimeError("A restored history table is empty; guard evidence refused")
            for action, statement, parameters in (
                ("UPDATE", sql.SQL("UPDATE {} SET id=id WHERE id=%s"), (row[0],)),
                ("DELETE", sql.SQL("DELETE FROM {} WHERE id=%s"), (row[0],)),
                ("TRUNCATE", sql.SQL("TRUNCATE TABLE {} CASCADE"), None),
            ):
                connection.execute("SAVEPOINT restored_history_probe")
                try:
                    connection.execute(statement.format(sql.Identifier(table)), parameters)
                except PsycopgError as error:
                    message = str(error).lower()
                    if error.sqlstate != "55000" or "historical" not in message or not (
                            "append only" in message or "append-only" in message):
                        raise RuntimeError("Restored history rejection was not its immutable guard") from None
                    results.append({"table": table, "action": action, "sqlstate": error.sqlstate,
                                    "rejected_by_history_guard": True})
                else:
                    raise RuntimeError("Restored history mutation unexpectedly succeeded")
                finally:
                    connection.execute("ROLLBACK TO SAVEPOINT restored_history_probe")
        if database_state(connection) != before:
            raise RuntimeError("Restored history guard probes changed rows or sequences")
    return results


def restore_with_finance_verification(drill, **kwargs):
    restored = original_restore(drill, **kwargs)
    if history_seed_enabled:
        actual_history = json.loads(drill._manage_database(
            restored["database"], Path(restored["media"]), *finance_command("verify", history_helper)).strip().splitlines()[-1])
        if actual_history != drill.review_history_snapshot:
            raise RuntimeError("Restored historical archive rows differ")
        print("HISTORY_RESTORE_VERIFICATION=PASS", flush=True)
    if finance_seed_enabled:
        actual = json.loads(drill._manage_database(
            restored["database"], Path(restored["media"]), *finance_command("verify")).strip().splitlines()[-1])
        if actual != drill.review_finance_snapshot:
            raise RuntimeError("Restored finance rows, sequences or private voucher bytes differ")
        restored_sequences = sequences(drill, restored["database"])
        if restored_sequences != drill.review_sequences:
            raise RuntimeError("Restored PostgreSQL sequence state differs")
        with drill._connect(restored["database"]) as connection:
            references = verify_media_references(connection, build_private_media_manifest(Path(restored["media"])))
        if references != drill.review_references:
            raise RuntimeError("Restored private media reference count differs")
        proof = {"source_sha": drill.app_sha, "status": "PASS", "snapshot": actual,
                 "sequences": restored_sequences, "media_references": references,
                 "restored_real_http": restored_private_http(drill, restored),
                 "scope": "Owned synthetic PostgreSQL source/restore verification, not deployment acceptance"}
        target = evidence_root / "artifacts" / "postgres-backups" / f"finance-restored-{drill.app_sha[:12]}.json"
        target.write_text(json.dumps(proof, ensure_ascii=False, indent=2), encoding="utf-8")
        print("FINANCE_RESTORE_VERIFICATION=PASS", flush=True)
    if operational_seed_enabled:
        actual = json.loads(drill._manage_database(
            restored["database"], Path(restored["media"]),
            *finance_command("verify", operational_helper)).strip().splitlines()[-1])
        if actual != drill.review_operational_snapshot:
            raise RuntimeError("Restored operational history rows, sequences, links or private bytes differ")
        probes = restored_history_guard_probes(drill, restored["database"])
        target = evidence_root / "artifacts" / "postgres-backups" / f"history-operational-restored-{drill.app_sha[:12]}.json"
        target.write_text(json.dumps({"source_sha": drill.app_sha, "status": "PASS", "snapshot": actual,
            "restored_guard_probes": probes, "guard_probe_data_unchanged": True,
            "scope": "Actual populated synthetic PostgreSQL restore; not production roles or real history"},
            ensure_ascii=False, indent=2), encoding="utf-8")
        print("HISTORY_OPERATIONAL_RESTORE_VERIFICATION=PASS", flush=True)
    with drill._connect(drill.source) as source_connection:
        source_after = database_state(source_connection)
    source_media_after = build_private_media_manifest(drill.media)
    if source_after != drill.supplemental_source_before:
        raise RuntimeError("Supplemental restore changed source public rows or sequences")
    if source_media_after != drill.supplemental_source_media_before:
        raise RuntimeError("Supplemental restore changed source private media")
    source_hash = hashlib.sha256(json.dumps(source_after, sort_keys=True).encode("utf-8")).hexdigest()
    proof = {"source_sha": drill.app_sha, "status": "PASS",
        "source_rows_and_sequences_unchanged": True, "source_media_unchanged": True,
        "before_state_sha256": hashlib.sha256(json.dumps(drill.supplemental_source_before, sort_keys=True).encode("utf-8")).hexdigest(),
        "after_state_sha256": source_hash, "source_table_count": len(source_after["tables"]),
        "source_row_count": sum(t["rows"] for t in source_after["tables"].values()),
        "source_sequence_count": len(source_after["sequences"]), "source_media_files": source_media_after["file_count"],
        "scope": "Explicit source reread after six tests, backup/restore, private HTTP and nine restored-history guard probes; before intentional owned-cluster cleanup. Not the previous1410 run."}
    target = evidence_root / "artifacts" / "postgres-backups" / f"source-invariance-{drill.app_sha[:12]}.json"
    target.write_text(json.dumps(proof, ensure_ascii=False, indent=2), encoding="utf-8")
    print("SOURCE_FINAL_ROWS_SEQUENCES_MEDIA_UNCHANGED=PASS", flush=True)
    return restored


def regression_then_backup(drill, **kwargs):
    with drill._connect(drill.source) as source_connection:
        drill.supplemental_source_before = database_state(source_connection)
    drill.supplemental_source_media_before = build_private_media_manifest(drill.media)
    # Regression files must not share the backup fixture's media snapshot.
    # Both directories belong to this one ephemeral drill root.
    test_media = drill.root / "regression-media"
    test_media.mkdir(exist_ok=False)
    env = drill._environment(drill.source, test_media)
    env["PYTHONUTF8"] = "1"
    # The full suite intentionally enables its owned-cluster backup test when
    # ISS018_DRILL_ROOT is present. Supply its complete local credential-file
    # contract; do not export or print the password itself.
    env.update(
        ISS018_DRILL_PASSWORD_FILE=str(drill.root / "secret"),
        ISS018_DRILL_PORT=str(drill.port),
        ISS018_DRILL_APP_SHA=drill.app_sha,
    )
    labels = os.environ.get("REVIEW_TEST_LABELS", "").split()
    print(f"POSTGRES_TEST_SELECTION={labels or ['full backend suite']}", flush=True)
    result = subprocess.run(
        [sys.executable, str(backend / "manage.py"), "test", *labels, "--verbosity", "2"],
        cwd=backend, env=env, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=3600,
    )
    for output in (result.stdout, result.stderr):
        print(output.replace(drill._password, "[REDACTED]"), end="", flush=True)
    print(f"POSTGRES_REGRESSION_EXIT={result.returncode}", flush=True)
    if result.returncode:
        raise RuntimeError(f"PostgreSQL regression failed: exit {result.returncode}")
    backup = original_backup(drill, **kwargs)
    # Retain the exact synthetic archive before the drill removes its owned
    # cluster and temporary files. This never changes the backup implementation.
    artifact_dir = evidence_root / "artifacts" / "postgres-backups"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    retained = artifact_dir / f"{drill.app_sha[:12]}-{uuid4().hex[:8]}.zip"
    raw_archive = Path(backup["archive"]).read_bytes()
    with retained.open("xb") as archive_file:
        archive_file.write(raw_archive)
    digest = hashlib.sha256(raw_archive).hexdigest()
    if digest != backup["sha256"]:
        raise RuntimeError("Retained synthetic backup digest differs from drill archive")
    manifest_path = retained.with_suffix(".json")
    with manifest_path.open("x", encoding="utf-8") as manifest_file:
        json.dump({"source_sha": drill.app_sha, "archive": retained.name,
                   "sha256": digest, "manifest": backup["manifest"],
                   "scope": "Synthetic owned-cluster backup; not a business database"},
                  manifest_file, ensure_ascii=False, indent=2)
    print(f"RETAINED_SYNTHETIC_BACKUP={retained.name} SHA256={digest}", flush=True)
    return backup


IsolatedPostgresDrill.backup = regression_then_backup
IsolatedPostgresDrill._manage = manage_with_finance_seed
IsolatedPostgresDrill.restore = restore_with_finance_verification
runpy.run_path(str(backend / "isolated_postgres_drill.py"), run_name="__main__")
