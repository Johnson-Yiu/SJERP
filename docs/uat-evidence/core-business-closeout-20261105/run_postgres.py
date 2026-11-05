"""Synthetic core business tests in a newly initialized, owned PostgreSQL17 cluster."""
import argparse
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import uuid
from urllib.parse import quote

import psycopg
from psycopg import sql


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pg-bin", required=True)
    parser.add_argument("--full", action="store_true")
    args = parser.parse_args()
    if os.environ.get("APP_STAGE", "development") != "development" or (os.environ.get("DATABASE_URL") and not os.environ["DATABASE_URL"].startswith("sqlite://")):
        raise RuntimeError("Parent must use development and isolated SQLite settings")
    bin_dir = Path(args.pg_bin).resolve(strict=True)
    exe = lambda name: str(bin_dir / (name + (".exe" if os.name == "nt" else "")))
    version = subprocess.check_output([exe("postgres"), "--version"], text=True).strip()
    if " 17." not in version:
        raise RuntimeError("PostgreSQL17 is required")
    root = Path(tempfile.mkdtemp(prefix="sunjack-core-pg17-")).resolve()
    marker = uuid.uuid4().hex
    (root / "owner.json").write_text(json.dumps({"owner": marker}), encoding="utf-8")
    secret = secrets.token_urlsafe(32)
    user = "fin_" + uuid.uuid4().hex[:12]
    database = "fin_src_" + uuid.uuid4().hex[:16]
    password_file = root / "password"
    password_file.write_text(secret, encoding="utf-8")
    if os.name != "nt":
        root.chmod(0o700)
        password_file.chmod(0o600)
    with socket.socket() as selected:
        selected.bind(("127.0.0.1", 0))
        port = selected.getsockname()[1]
    if port == 5432:
        raise RuntimeError("Dedicated port is required")
    started, exit_code, cleanup = False, 1, "not-started"
    def tool(command):
        with tempfile.TemporaryFile() as diagnostic:
            result = subprocess.run(command, stdout=diagnostic, stderr=diagnostic, timeout=180)
            diagnostic.seek(0)
            output = diagnostic.read().decode("utf-8", errors="replace").replace(secret, "[REDACTED]")
        if result.returncode:
            raise RuntimeError(f"{Path(command[0]).name} failed ({result.returncode}): {output}")
    try:
        tool([exe("initdb"), "-D", str(root / "data"), "-U", user, "--pwfile", str(password_file), "--auth=scram-sha-256", "-E", "UTF8", "--locale=C"])
        tool([exe("pg_ctl"), "-D", str(root / "data"), "-l", str(root / "postgres.log"), "-o", f"-h 127.0.0.1 -p {port}", "-w", "start"])
        started = True
        with psycopg.connect(host="127.0.0.1", port=port, user=user, password=secret, dbname="postgres", autocommit=True) as conn:
            actual = conn.execute("SHOW data_directory").fetchone()[0]
            if Path(actual).resolve() != root / "data":
                raise RuntimeError("Cluster identity mismatch")
            conn.execute(sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(sql.Identifier(database)))
        media = root / "media"
        media.mkdir()
        env = dict(os.environ, APP_STAGE="development", MEDIA_ROOT=str(media), PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1",
            DATABASE_URL=f"postgresql://{user}:{quote(secret, safe='')}@127.0.0.1:{port}/{database}")
        env["PYTHONPATH"] = str(Path(__file__).resolve().parent)
        for name in ("ISS018_COMMAND_PG_BIN", "ISS018_DRILL_ROOT", "ISS018_DRILL_PASSWORD_FILE"):
            env.pop(name, None)
        repo = Path(__file__).resolve().parents[3]
        labels = [] if args.full else ["crm.tests.test_core_business_closeout", "crm.tests.test_core_business_concurrency", "crm.tests.test_postgres_concurrency", "crm.tests.test_iss006_idempotency", "crm.tests.test_fulfillment_audit_atomicity"]
        print(json.dumps({"postgres": version, "cluster": str(root), "source": database, "port": port, "test_labels": labels}), flush=True)
        result = subprocess.run([sys.executable, "manage.py", "test", *labels, "--verbosity", "2"], cwd=repo / "backend", env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=7200)
        print((result.stdout + result.stderr).replace(secret, "[REDACTED]"), flush=True)
        exit_code = result.returncode
        with psycopg.connect(host="127.0.0.1", port=port, user=user, password=secret, dbname="postgres") as conn:
            remaining = conn.execute("SELECT datname FROM pg_database WHERE datname LIKE 'test_%'").fetchall()
            print(json.dumps({"test_databases_remaining": remaining, "test_exit": exit_code}), flush=True)
            if remaining:
                exit_code = 1
    finally:
        try:
            if started:
                tool([exe("pg_ctl"), "-D", str(root / "data"), "-m", "fast", "-w", "stop"])
            if root.parent != Path(tempfile.gettempdir()).resolve() or not root.name.startswith("sunjack-core-pg17-") or json.loads((root / "owner.json").read_text())["owner"] != marker:
                raise RuntimeError("Refuse cleanup: ownership mismatch")
            shutil.rmtree(root)
            cleanup = "complete"
        except Exception as error:
            print(json.dumps({"cleanup_error": str(error).replace(secret, "[REDACTED]"), "retained_root": str(root)}))
            exit_code = 1
        print(json.dumps({"cleanup": cleanup, "exit": exit_code}), flush=True)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
