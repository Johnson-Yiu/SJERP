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
import zipfile
import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

from isolated_postgres_drill import run_tool, tool
from crm.services.postgres_drill_backup import IsolatedPostgresDrill
from crm.services.operations_postgres import MaintenanceBackup, database_state
from crm.services.operations_copy import digest
from crm.services.operations_copy import verified_copy
from crm.services.operations_crypto import crypt_file
from crm.services.operations_retention import prune_verified
from crm.services.operations_receipt import restore_and_sign, public_key_fingerprint, _openssl
import psycopg


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--postgres-bin", required=True)
    parser.add_argument("--gpg")
    parser.add_argument("--openssl")
    parser.add_argument("--msys-paths", action="store_true")
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
        os.environ["ISS018_DRILL_ROOT"] = str(root)
        sha = subprocess.run(["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
        drill = IsolatedPostgresDrill(task_root=root, pg_bin=pg, port=port, user="iss018_drill_admin", password=password, app_sha=sha)
        drill._manage("migrate", "--noinput", "--verbosity", "0")
        drill._manage("shell", "--no-imports", "-c", "from crm.tests.iss018_drill_fixture import seed; seed()")
        options = dict(host="127.0.0.1", port=port, user="iss018_drill_admin", password=password, dbname=drill.source)
        with drill._connect(drill.source) as connection:
            system = connection.execute("SELECT system_identifier::text FROM pg_control_system()").fetchone()[0]
            before = database_state(connection)
        with drill._connect(drill.source) as holder, drill._connect(drill.source) as competitor:
            holder.execute("LOCK TABLE crm_customer IN SHARE MODE")
            competitor.execute("SET LOCAL lock_timeout='300ms'")
            try:
                competitor.execute("UPDATE crm_customer SET id=id")
            except psycopg.errors.LockNotAvailable:
                lock_competition_rejected = True
                competitor.rollback()
            else:
                raise AssertionError("competing table writer bypassed SHARE lock")
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
        corrupt = root / "invalid-dump.zip"
        invalid_dump = b"SYNTHETIC INVALID POSTGRES CUSTOM DUMP"
        with zipfile.ZipFile(archive) as original, zipfile.ZipFile(corrupt, "w") as changed:
            for entry in original.infolist():
                content = original.read(entry)
                if entry.filename == "database.dump":
                    content = invalid_dump
                elif entry.filename == "manifest.json":
                    manifest = json.loads(content)
                    manifest["database_sha256"] = hashlib.sha256(invalid_dump).hexdigest()
                    content = json.dumps(manifest).encode()
                changed.writestr(entry, content)
        with drill._connect("postgres") as connection:
            databases_before = connection.execute("SELECT datname FROM pg_database ORDER BY datname").fetchall()
        try:
            service.restore(archive=corrupt, expected_sha256=digest(corrupt), media_parent=root)
        except RuntimeError:
            failed_restore_rejected = True
        else:
            raise AssertionError("invalid pg_restore input accepted")
        with drill._connect("postgres") as connection:
            assert connection.execute("SELECT datname FROM pg_database ORDER BY datname").fetchall() == databases_before
        try:
            service.restore(archive=archive, expected_sha256="0"*64, media_parent=root)
        except ValueError:
            bad_digest_rejected = True
        else:
            raise AssertionError("wrong archive digest accepted")
        with drill._connect(drill.source) as connection:
            assert database_state(connection) == before
        retention_removed = None
        if args.gpg:
            if not args.openssl:
                raise ValueError("OpenSSL is required for signed restore receipt verification")
            backup_root, replica_root = root / "encrypted", root / "local-replicas"
            backup_root.mkdir(mode=0o700); replica_root.mkdir(mode=0o700)
            key_root = root / "receipt-key"
            key_root.mkdir()
            signing_key, public_key = key_root / "signing.pem", key_root / "verify.pem"
            subprocess.run([args.openssl, "genpkey", "-algorithm", "EC", "-pkeyopt", "ec_paramgen_curve:P-256", "-out", str(signing_key)], check=True, capture_output=True)
            signing_key.chmod(0o600)
            public_key.write_bytes(_openssl(args.openssl, "pkey", "-in", signing_key, "-pubout"))
            verification = {"executable": args.openssl, "public_key": str(public_key),
                            "pinned_fingerprint": public_key_fingerprint(args.openssl, public_key), "max_age_seconds": 86400}
            owner = uuid.uuid4().hex
            (backup_root / ".sunjack-backup-owner").write_text(owner, encoding="ascii")
            (backup_root / ".sunjack-backup-owner").chmod(0o600)
            key = secrets.token_hex(32).encode()
            receipts = []
            now = datetime.now(timezone.utc)
            for age in (1, 2, 3):
                name = "backup-" + uuid.uuid4().hex + ".gpg"
                encrypted = backup_root / name
                cipher = crypt_file(archive, encrypted, executable=args.gpg, key=key,
                                    expected_sha256=backup["sha256"], msys_paths=args.msys_paths)
                synthetic_timestamp = (now-timedelta(days=age)).timestamp()
                os.utime(encrypted, (synthetic_timestamp, synthetic_timestamp))
                plaintext = root / ("verified-" + str(age) + ".zip")
                crypt_file(encrypted, plaintext, executable=args.gpg, key=key, expected_sha256=backup["sha256"],
                           msys_paths=args.msys_paths, decrypt=True)
                restore_receipt, receipt_restored = restore_and_sign(service, encrypted_archive=encrypted,
                    encrypted_sha256=cipher["sha256"], plaintext_sha256=backup["sha256"], media_parent=root,
                    gpg_executable=args.gpg, encryption_key=key, openssl_executable=args.openssl,
                    signing_key=signing_key, msys_paths=args.msys_paths)
                assert receipt_restored["verified"] and receipt_restored["audit_truncate_rejected"]
                replica = replica_root / name
                verified_copy(encrypted, replica, cipher["sha256"])
                receipts.append({"name": name, "sha256": cipher["sha256"], "restore_verified_sha256": cipher["sha256"],
                                 "restore_receipt": restore_receipt,
                                 "replica": str(replica), "created_at": datetime.fromtimestamp(encrypted.stat().st_mtime_ns / 1_000_000_000, timezone.utc).isoformat()})
            now = datetime.now(timezone.utc)
            retention = prune_verified(backup_root, owner_id=owner, receipts=receipts, keep=1,
                                       minimum_age_seconds=86400, now=now, receipt_verification=verification, execute=True)
            retention_removed = len(retention["removed"])
            assert retention_removed == 2 and len(list(replica_root.iterdir())) == 3
            assert (backup_root / receipts[0]["name"]).exists()
        result = {"status": "PASS", "source_sha": sha, "scope": "real-PG17-with-simulated-media-fence", "active_session_rejected": active_rejected,
                          "other_login_rejected": login_rejected, "restored_verified": restored["verified"],
                          "audit_truncate_rejected": restored["audit_truncate_rejected"], "source_unchanged": True,
                          "audit_row_mutations_rejected": restored["audit_row_mutations_rejected"],
                          "real_lock_competition_rejected": lock_competition_rejected, "bad_digest_rejected": bad_digest_rejected,
                          "failed_restore_rejected_and_owned_database_removed": failed_restore_rejected,
                          "encrypted_retention_removed": retention_removed, "replicas_are_local_only": True,
                          "tables": len(before["tables"]), "rows": sum(v["rows"] for v in before["tables"].values()),
                          "seconds": round(time.monotonic()-clock, 3)}
    finally:
        if started:
            run_tool([tool(pg, "pg_ctl"), "-D", str(cluster), "-m", "fast", "-w", "stop"])
        if root.parent.resolve() != Path(tempfile.gettempdir()).resolve() or not root.name.startswith("sunjack-iss018-pg17-") or root.is_symlink():
            raise RuntimeError("Owned cleanup root identity mismatch")
        for attempt in range(5):
            try:
                shutil.rmtree(root)
                break
            except PermissionError:
                if attempt == 4:
                    raise
                time.sleep(1)
    result["cleanup"] = "complete"
    print(json.dumps(result))


if __name__ == "__main__":
    main()
