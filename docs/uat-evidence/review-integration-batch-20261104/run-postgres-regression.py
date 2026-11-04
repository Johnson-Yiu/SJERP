"""Run this checkout's tests in a new cluster owned by the existing PG drill."""
import os
import hashlib
import json
from pathlib import Path
import runpy
import subprocess
import sys
from uuid import uuid4

repository = Path(__file__).resolve().parents[3]
backend = repository / "backend"
if os.environ.get("APP_STAGE", "development") != "development":
    raise SystemExit("Requires development stage and synthetic data")
if os.environ.get("DATABASE_URL") and not os.environ["DATABASE_URL"].startswith("sqlite://"):
    raise SystemExit("Refusing an inherited non-SQLite database target")
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
sys.path.insert(0, str(backend))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()
from crm.services.postgres_drill_backup import IsolatedPostgresDrill
from crm.services.operations_postgres import verify_media_references
from crm.services.private_media import build_private_media_manifest
from psycopg import sql

original_backup = IsolatedPostgresDrill.backup
original_manage = IsolatedPostgresDrill._manage
original_restore = IsolatedPostgresDrill.restore
finance_seed_enabled = os.environ.get("REVIEW_FINANCE_SEED") == "1"
finance_helper = Path(__file__).resolve().parent / "finance-backup-seed" / "seed_finance_backup.py"


def sequences(drill, database):
    with drill._connect(database) as connection:
        names = connection.execute("SELECT sequencename FROM pg_sequences WHERE schemaname='public' ORDER BY sequencename").fetchall()
        return {name: list(connection.execute(sql.SQL("SELECT last_value, is_called FROM public.{}").format(sql.Identifier(name))).fetchone())
                for (name,) in names}


def finance_command(function):
    return ("shell", "--no-imports", "-c",
            f"import json, runpy; print(json.dumps(runpy.run_path({str(finance_helper)!r})[{function!r}](), ensure_ascii=False))")


def manage_with_finance_seed(drill, *arguments):
    output = original_manage(drill, *arguments)
    core_seed = "from crm.tests.iss018_drill_fixture import seed; seed()"
    if finance_seed_enabled and arguments == ("shell", "--no-imports", "-c", core_seed):
        # This hook runs before the original driver's all-table source snapshot.
        # The helper independently rejects any database outside this owned root.
        seeded = json.loads(original_manage(drill, *finance_command("seed")).strip().splitlines()[-1])
        drill.review_finance_snapshot = json.loads(original_manage(drill, *finance_command("verify")).strip().splitlines()[-1])
        drill.review_sequences = sequences(drill, drill.source)
        with drill._connect(drill.source) as connection:
            drill.review_references = verify_media_references(connection, build_private_media_manifest(drill.media))
        print("FINANCE_BACKUP_SEED=" + json.dumps(seeded, ensure_ascii=False), flush=True)
    return output


def restore_with_finance_verification(drill, **kwargs):
    restored = original_restore(drill, **kwargs)
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
                 "scope": "Owned synthetic PostgreSQL source/restore verification, not deployment acceptance"}
        target = Path(__file__).resolve().parent / "artifacts" / "postgres-backups" / f"finance-restored-{drill.app_sha[:12]}.json"
        target.write_text(json.dumps(proof, ensure_ascii=False, indent=2), encoding="utf-8")
        print("FINANCE_RESTORE_VERIFICATION=PASS", flush=True)
    return restored


def regression_then_backup(drill, **kwargs):
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
    artifact_dir = Path(__file__).resolve().parent / "artifacts" / "postgres-backups"
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
