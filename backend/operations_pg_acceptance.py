"""Disposable PG17 validation of maintenance primitives.

The Linux media fence is simulated explicitly; no production-readiness claim.
All PostgreSQL operations and database writer rejection probes are real.
"""
import argparse
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import tempfile
import time
from unittest.mock import patch

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

from isolated_postgres_drill import run_tool, tool
from crm.services.postgres_drill_backup import IsolatedPostgresDrill
from crm.services.operations_postgres import MaintenanceBackup, database_state
from crm.services.operations_copy import digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--postgres-bin", required=True)
    args = parser.parse_args()
    root = Path(tempfile.mkdtemp(prefix="sunjack-iss018-pg17-"))
    pg = root / "pgsql" / "bin"
    cluster = root / "cluster-host"
    started = False
    password = secrets.token_urlsafe(32)
    clock = time.monotonic()
    try:
        shutil.copytree(Path(args.postgres_bin).parent, pg.parent)
        secret = root / "secret"
        secret.write_text(password, encoding="ascii")
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        run_tool([tool(pg, "initdb"), "-D", str(cluster), "-U", "iss018_drill_admin", "--auth=scram-sha-256", "--pwfile=" + str(secret), "--encoding=UTF8", "--no-locale"])
        secret.unlink()
        started = True
        run_tool([tool(pg, "pg_ctl"), "-D", str(cluster), "-l", str(root / "postgres.log"), "-o", f"-h 127.0.0.1 -p {port}", "-w", "start"])
        sha = subprocess.run(["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
        drill = IsolatedPostgresDrill(task_root=root, pg_bin=pg, port=port, user="iss018_drill_admin", password=password, app_sha=sha)
        drill._manage("migrate", "--noinput", "--verbosity", "0")
        drill._manage("shell", "--no-imports", "-c", "from crm.tests.iss018_drill_fixture import seed; seed()")
        options = dict(host="127.0.0.1", port=port, user="iss018_drill_admin", password=password, dbname=drill.source)
        with drill._connect(drill.source) as connection:
            system = connection.execute("SELECT system_identifier::text FROM pg_control_system()").fetchone()[0]
            before = database_state(connection)
        service = MaintenanceBackup(connection_options=options, pg_bin=pg, expected_database=drill.source, expected_system_identifier=system, app_sha=sha)
        with drill._connect(drill.source) as active, service.connect() as connection:
            try:
                service.writer_gate(connection)
            except RuntimeError:
                active_rejected = True
            else:
                raise AssertionError("active writer session accepted")
        with drill._connect(drill.source) as connection:
            connection.execute("CREATE ROLE synthetic_writer LOGIN")
        try:
            with service.connect() as connection:
                service.writer_gate(connection)
        except RuntimeError:
            login_rejected = True
        else:
            raise AssertionError("enabled writer login accepted")
        finally:
            with drill._connect(drill.source) as connection:
                connection.execute("DROP ROLE synthetic_writer")
        archive = root / "backup.zip"
        # Only media OS evidence is substituted. This is not a full fence drill.
        with patch("crm.services.operations_postgres.verify_readonly_filesystem", return_value={"evidence": "SIMULATED-LINUX-MEDIA-FENCE"}):
            backup = service.backup(media_root=drill.media, destination=archive)
        restored = service.restore(archive=archive, expected_sha256=backup["sha256"], media_parent=root)
        with drill._connect(drill.source) as connection:
            assert database_state(connection) == before
        print(json.dumps({"status": "PASS", "scope": "real-PG17-with-simulated-media-fence", "active_session_rejected": active_rejected,
                          "other_login_rejected": login_rejected, "restored_verified": restored["verified"],
                          "audit_truncate_rejected": restored["audit_truncate_rejected"], "source_unchanged": True,
                          "tables": len(before["tables"]), "rows": sum(v["rows"] for v in before["tables"].values()),
                          "seconds": round(time.monotonic()-clock, 3)}))
    finally:
        if started:
            run_tool([tool(pg, "pg_ctl"), "-D", str(cluster), "-m", "fast", "-w", "stop"])
        shutil.rmtree(root)


if __name__ == "__main__":
    main()
