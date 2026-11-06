"""Run the sales order import acceptance tests on an owned temporary PostgreSQL 17 cluster."""
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
import time
import uuid
from urllib.parse import quote


REPO = Path(__file__).resolve().parents[3]


def run_tool(command, secret="", env=None):
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180, env=env)
    output = result.stdout + result.stderr
    if secret:
        output = output.replace(secret, "[REDACTED]")
    if result.returncode:
        raise RuntimeError(f"{Path(command[0]).name} failed ({result.returncode}): {output}")
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--postgres-bin", required=True)
    args = parser.parse_args()
    source_bin = Path(args.postgres_bin).resolve(strict=True)
    for executable in ("postgres.exe", "initdb.exe", "pg_ctl.exe", "psql.exe"):
        if not (source_bin / executable).is_file():
            raise FileNotFoundError(f"Missing PostgreSQL tool: {source_bin / executable}")
    version = run_tool([str(source_bin / "postgres.exe"), "--version"]).strip()
    if " 17." not in version:
        raise RuntimeError(f"PostgreSQL 17 is required: {version}")

    root = Path(tempfile.mkdtemp(prefix="sunjack-sales-order-import-pg17-")).resolve()
    owner = uuid.uuid4().hex
    (root / "owner.json").write_text(json.dumps({"owner": owner}), encoding="utf-8")
    pg_bin = source_bin
    cluster = root / "cluster"
    password_file = root / "password"
    password = secrets.token_urlsafe(32)
    password_file.write_text(password, encoding="ascii")
    if os.name != "nt":
        root.chmod(0o700)
        password_file.chmod(0o600)
    user = "sales_import_" + uuid.uuid4().hex[:12]
    database = "sales_import_" + uuid.uuid4().hex[:12]
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]

    started = False
    exit_code = 1
    try:
        print(json.dumps({"phase": "initialize-owned-cluster", "version": version, "port": port, "cluster": str(cluster)}), flush=True)
        run_tool([
            str(pg_bin / "initdb.exe"), "-D", str(cluster), "-U", user,
            "--auth=scram-sha-256", "--pwfile=" + str(password_file), "--encoding=UTF8", "--no-locale",
        ], password)
        password_file.unlink()
        start_result = subprocess.run([
            str(pg_bin / "pg_ctl.exe"), "-D", str(cluster), "-l", str(root / "postgres.log"),
            "-o", f"-h 127.0.0.1 -p {port}", "-w", "start",
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180)
        if start_result.returncode:
            log = (root / "postgres.log").read_text(encoding="utf-8", errors="replace") if (root / "postgres.log").exists() else ""
            raise RuntimeError(f"pg_ctl.exe failed ({start_result.returncode}): {log.replace(password, '[REDACTED]')}")
        started = True
        print(json.dumps({"phase": "postgres-listening", "port": port}), flush=True)
        client_env = dict(os.environ, PGPASSWORD=password, PGCONNECT_TIMEOUT="5")
        psql = str(pg_bin / "psql.exe")
        actual_data = run_tool([
            psql, "-h", "127.0.0.1", "-p", str(port), "-U", user, "-d", "postgres", "-w", "-A", "-t", "-c", "SHOW data_directory",
        ], password, env=client_env).strip()
        if Path(actual_data).resolve() != cluster.resolve():
            raise RuntimeError("Temporary cluster identity mismatch")
        print(json.dumps({"phase": "cluster-identity-verified"}), flush=True)
        run_tool([
            psql, "-h", "127.0.0.1", "-p", str(port), "-U", user, "-d", "postgres", "-w", "-v", "ON_ERROR_STOP=1",
            "-c", f'CREATE DATABASE "{database}" TEMPLATE template0',
        ], password, env=client_env)
        print(json.dumps({"phase": "synthetic-database-created", "database": database}), flush=True)

        media = root / "media"
        media.mkdir()
        database_url = f"postgresql://{user}:{quote(password, safe='')}@127.0.0.1:{port}/{database}"
        env = dict(os.environ)
        env.update({
            "APP_STAGE": "development",
            "DATABASE_URL": database_url,
            "MEDIA_ROOT": str(media),
            "PYTHONUTF8": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
        })
        print(json.dumps({"phase": "run-targeted-tests", "postgres": version, "port": port, "database": database, "database_url": f"postgresql://{user}:[REDACTED]@127.0.0.1:{port}/{database}", "test_label": "crm.tests.test_sales_order_import"}), flush=True)
        result = subprocess.run(
            [sys.executable, str(REPO / "backend" / "manage.py"), "test", "crm.tests.test_sales_order_import", "--noinput", "--verbosity", "2"],
            cwd=REPO / "backend", env=env, timeout=1800,
        )
        exit_code = result.returncode
        remaining = run_tool([
            psql, "-h", "127.0.0.1", "-p", str(port), "-U", user, "-d", "postgres", "-w", "-A", "-t",
            "-c", "SELECT datname FROM pg_database WHERE datname LIKE 'test_%'",
        ], password, env=client_env).splitlines()
        if remaining:
            print(json.dumps({"test_databases_remaining": remaining}), flush=True)
            exit_code = 1
        print(json.dumps({"phase": "tests-finished", "exit": exit_code, "remaining_test_databases": len(remaining)}), flush=True)
    finally:
        if cluster.exists():
            status_result = subprocess.run(
                [str(pg_bin / "pg_ctl.exe"), "-D", str(cluster), "status"],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30,
            )
            if started or status_result.returncode == 0:
                run_tool([str(pg_bin / "pg_ctl.exe"), "-D", str(cluster), "-m", "fast", "-w", "stop"], password)
        if root.parent.resolve() != Path(tempfile.gettempdir()).resolve() or not root.name.startswith("sunjack-sales-order-import-pg17-") or root.is_symlink() or json.loads((root / "owner.json").read_text(encoding="utf-8"))["owner"] != owner:
            raise RuntimeError("Refuse cleanup: temporary root ownership mismatch")
        for attempt in range(6):
            try:
                shutil.rmtree(root)
                break
            except PermissionError:
                if attempt == 5:
                    raise
                time.sleep(1)
        print(json.dumps({"phase": "owned-cluster-cleaned", "exit": exit_code}), flush=True)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
