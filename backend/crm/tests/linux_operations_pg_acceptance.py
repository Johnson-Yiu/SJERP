"""Real PG17, restricted roles and actual Linux media fence on a CI-owned service."""
import hashlib
import base64
import errno
import getpass
import json
import os
from pathlib import Path
import re
import secrets
import signal
import socket
import shutil
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
import uuid
from unittest import mock

import psycopg
from psycopg import sql

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

from crm.services.operations_copy import digest, verified_copy
from crm.services.operations_crypto import crypt_file
from crm.services.operations_postgres import MaintenanceBackup, database_state, publish_archive
from crm.services.operations_receipt import _canonical, _openssl, public_key_fingerprint, restore_and_sign
from crm.services.operations_retention import prune_verified
from crm.services.operations_monitor import check_backup_freshness


def command(*arguments, **kwargs):
    return subprocess.run(list(map(str, arguments)), check=True, timeout=300, **kwargs)


def exercise_owned_timer(backend, monitor_script, config):
    """Use task-owned transient timers and an OnFailure loopback alert."""
    systemd_run, systemctl, logger = shutil.which("systemd-run"), shutil.which("systemctl"), shutil.which("logger")
    if not systemd_run or not systemctl or not logger:
        return {"status": "BLOCKED", "reason": "systemd-run, systemctl or logger unavailable"}
    unit = "sunjack-ci-monitor-" + uuid.uuid4().hex
    alert_unit = "sunjack-ci-alert-" + uuid.uuid4().hex
    primary = None
    receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        receiver.bind(("127.0.0.1", 0))
        receiver.settimeout(10)
        alert_port = receiver.getsockname()[1]
        alert = subprocess.run(["sudo", "-n", systemd_run, "--unit=" + alert_unit, "--on-active=1d", "--",
                                logger, "--server", "127.0.0.1", "--port", str(alert_port), "--udp", "--priority", "user.err",
                                "--", "SUNJACK synthetic scheduled failure alert"], capture_output=True, text=True, timeout=30)
        if alert.returncode:
            return {"status": "BLOCKED", "reason": (alert.stderr or alert.stdout).strip()[:500]}
        start = subprocess.run(["sudo", "-n", systemd_run, "--unit=" + unit, "--on-active=2s",
                                "--timer-property=AccuracySec=1s", "--property=Type=oneshot",
                                "--property=User=" + getpass.getuser(), "--property=WorkingDirectory=" + str(backend),
                                "--property=OnFailure=" + alert_unit + ".service", "--setenv=PYTHONPATH=" + str(backend),
                                "--", sys.executable, str(monitor_script), "--config", str(config)],
                               capture_output=True, text=True, timeout=30)
        if start.returncode:
            return {"status": "BLOCKED", "reason": (start.stderr or start.stdout).strip()[:500]}
        deadline = time.monotonic() + 40
        while time.monotonic() < deadline:
            status = subprocess.run([systemctl, "show", unit + ".service", "--property=Result", "--value"],
                                    capture_output=True, text=True, timeout=10)
            if status.returncode == 0 and status.stdout.strip() == "exit-code":
                code = subprocess.run([systemctl, "show", unit + ".service", "--property=ExecMainStatus", "--value"],
                                      capture_output=True, text=True, timeout=10)
                if code.returncode != 0 or code.stdout.strip() != "1":
                    raise RuntimeError("Scheduled stale-backup monitor did not exit with status 1")
                message, _ = receiver.recvfrom(4096)
                if b"SUNJACK synthetic scheduled failure alert" not in message:
                    raise RuntimeError("Scheduled OnFailure alert payload was not delivered to the owned receiver")
                return {"status": "PASS", "monitor_exit": 1, "on_failure_alert": "task-owned loopback receiver",
                        "unit_scope": "unique temporary runner units"}
            time.sleep(1)
        raise RuntimeError("Transient monitor timer did not run within 40 seconds")
    except Exception as error:
        primary = error
        raise
    finally:
        receiver.close()
        failures = []
        # Only this function's random unit names are touched.
        for name in (unit + ".timer", unit + ".service", alert_unit + ".timer", alert_unit + ".service"):
            loaded = subprocess.run([systemctl, "show", name, "--property=LoadState", "--value"],
                                    capture_output=True, text=True, timeout=10)
            if loaded.returncode == 0 and loaded.stdout.strip() not in ("", "not-found"):
                stopped = subprocess.run(["sudo", "-n", systemctl, "stop", name], capture_output=True, text=True, timeout=20)
                if stopped.returncode:
                    failures.append("stop " + name + ": " + stopped.stderr.strip()[:200])
                if name.endswith(".service"):
                    still_loaded = subprocess.run([systemctl, "show", name, "--property=LoadState", "--value"],
                                                  capture_output=True, text=True, timeout=10)
                    if still_loaded.returncode == 0 and still_loaded.stdout.strip() not in ("", "not-found"):
                        reset = subprocess.run(["sudo", "-n", systemctl, "reset-failed", name], capture_output=True, text=True, timeout=20)
                        if reset.returncode:
                            failures.append("reset " + name + ": " + reset.stderr.strip()[:200])
        if failures:
            if primary is not None:
                primary.add_note("Task-owned transient unit cleanup failed: " + "; ".join(failures))
            else:
                raise RuntimeError("Task-owned transient unit cleanup failed: " + "; ".join(failures))


def main():
    start = time.monotonic()
    root = Path(os.environ["SUNJACK_CI_ROOT"]).resolve(strict=True)
    runner_temp = Path(os.environ["RUNNER_TEMP"]).resolve(strict=True)
    if os.environ.get("GITHUB_ACTIONS") != "true" or root.parent != runner_temp or not root.name.startswith("sunjack-linux-pg-"):
        raise RuntimeError("An owned GitHub runner temporary root is required")
    container = os.environ["SUNJACK_CI_POSTGRES_CONTAINER"]
    port = int(os.environ["SUNJACK_CI_POSTGRES_PORT"])
    details = json.loads(command("docker", "inspect", container, capture_output=True, text=True).stdout)[0]
    bindings = details["NetworkSettings"]["Ports"]["5432/tcp"]
    if details["Id"] != container or details["Config"]["Image"] != "postgres:17" or port == 5432 or not any(int(binding["HostPort"]) == port for binding in bindings):
        raise RuntimeError("Database is not the job-owned PG17 service")
    media = root / "media"
    if not media.is_dir() or media.is_symlink():
        raise RuntimeError("Task-owned mounted media directory required")
    database, maint, runtime = "sunjack_ci_source", "sunjack_ci_maint", "sunjack_ci_runtime"
    connection = dict(host="127.0.0.1", port=port, user="postgres", dbname="postgres", sslmode="disable")
    admin = psycopg.connect(**connection, autocommit=True)
    runtime_connection = None
    try:
        if admin.execute("SELECT current_setting('server_version_num')::int").fetchone()[0] // 10000 != 17:
            raise RuntimeError("Expected PostgreSQL 17")
        admin.execute(sql.SQL("CREATE ROLE {} LOGIN CREATEDB NOSUPERUSER").format(sql.Identifier(maint)))
        admin.execute(sql.SQL("CREATE ROLE {} LOGIN NOCREATEDB NOSUPERUSER NOINHERIT").format(sql.Identifier(runtime)))
        admin.execute(sql.SQL("GRANT EXECUTE ON FUNCTION pg_catalog.pg_control_system() TO {}").format(sql.Identifier(maint)))
        admin.execute(sql.SQL("CREATE DATABASE {} OWNER {} TEMPLATE template0").format(sql.Identifier(database), sql.Identifier(maint)))
        options = dict(host="127.0.0.1", port=port, user=maint, dbname=database, sslmode="disable")
        environment = os.environ.copy()
        environment.update(APP_STAGE="development", DEVELOPMENT_SUPERADMIN="false", RBAC_ENFORCEMENT="true",
                           DATABASE_URL=f"postgresql://{maint}@127.0.0.1:{port}/{database}?sslmode=disable", MEDIA_ROOT=str(media),
                           DJANGO_SECRET_KEY=secrets.token_urlsafe(48))
        backend = Path(__file__).resolve().parents[2]
        command(sys.executable, backend / "manage.py", "migrate", "--noinput", "--verbosity", "0", env=environment)

        voucher = media / "finance-vouchers" / "synthetic.bin"
        voucher.parent.mkdir(parents=True)
        voucher.write_bytes(b"SYNTHETIC PRIVATE VOUCHER\n")
        # Incompressible synthetic bytes provide enough time to interrupt a real
        # backup while its temporary archive is being written.
        (media / "synthetic-load.bin").write_bytes(os.urandom(12 * 1024 * 1024))
        voucher_sha = digest(voucher)
        with psycopg.connect(**options, autocommit=True) as db:
            db.execute("INSERT INTO crm_financevoucher (file, original_name, sha256, size, actor, scope, bank_sources, created_at) VALUES (%s,%s,%s,%s,'{}'::jsonb,'account','[]'::jsonb,now())",
                       ("finance-vouchers/synthetic.bin", "synthetic.bin", voucher_sha, voucher.stat().st_size))
            content_type = db.execute("SELECT id FROM django_content_type ORDER BY id LIMIT 1").fetchone()[0]
            db.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(sql.Identifier(runtime)))
            db.execute(sql.SQL("GRANT SELECT, INSERT ON crm_operationlog TO {}").format(sql.Identifier(runtime)))
            db.execute(sql.SQL("GRANT USAGE, SELECT ON SEQUENCE crm_operationlog_id_seq TO {}").format(sql.Identifier(runtime)))
            db.execute(sql.SQL("REVOKE UPDATE, DELETE, TRUNCATE, TRIGGER, REFERENCES ON crm_operationlog FROM {}").format(sql.Identifier(runtime)))
            db.execute("REVOKE UPDATE, DELETE, TRUNCATE, TRIGGER, REFERENCES ON crm_operationlog FROM PUBLIC")
            before = database_state(db)
            system = db.execute("SELECT system_identifier::text FROM pg_control_system()").fetchone()[0]
            assert db.execute("SELECT rolsuper,rolcreatedb FROM pg_roles WHERE rolname=current_user").fetchone() == (False, True)
        runtime_connection = psycopg.connect(**{**options, "user": runtime}, autocommit=True)
        assert runtime_connection.execute("SELECT current_user").fetchone()[0] == runtime
        assert runtime_connection.execute("SELECT tableowner FROM pg_tables WHERE tablename='crm_operationlog'").fetchone()[0] == maint
        assert runtime_connection.execute("SELECT rolsuper,rolcreatedb FROM pg_roles WHERE rolname=current_user").fetchone() == (False, False)
        runtime_connection.execute("SELECT count(*) FROM crm_operationlog")
        row_id = runtime_connection.execute("INSERT INTO crm_operationlog (content_type_id,object_id,entity,entity_label,object_label,action,action_label,changed_fields,before_data,after_data,metadata,request_method,request_path,created_at) VALUES (%s,'synthetic','synthetic','','','custom','','[]'::jsonb,'{}'::jsonb,'{}'::jsonb,'{}'::jsonb,'','',now()) RETURNING id", (content_type,)).fetchone()[0]
        for statement in ("UPDATE crm_operationlog SET entity=entity WHERE id=%s", "DELETE FROM crm_operationlog WHERE id=%s"):
            try:
                runtime_connection.execute(statement, (row_id,))
            except psycopg.errors.InsufficientPrivilege as error:
                if "permission denied for table crm_operationlog" not in str(error):
                    raise AssertionError("Application-role denial did not come from table privileges") from error
            else:
                raise AssertionError("Restricted application role changed audit history")
        try:
            runtime_connection.execute("TRUNCATE crm_operationlog")
        except psycopg.errors.InsufficientPrivilege as error:
            if "permission denied for table crm_operationlog" not in str(error):
                raise AssertionError("Application-role TRUNCATE denial was not a permission denial") from error
        else:
            raise AssertionError("Restricted application role truncated audit history")
        # Record baseline after the intentionally inserted synthetic audit entry.
        with psycopg.connect(**options) as db:
            before = database_state(db)
        tool_dir = root / "pg-tools"
        tool_dir.mkdir()
        proxy = Path(__file__).with_name("linux_pg_tool_proxy.py")
        for name in ("pg_dump", "pg_restore"):
            destination = tool_dir / name
            shutil.copyfile(proxy, destination)
            destination.chmod(0o700)
        service = MaintenanceBackup(connection_options=options, pg_bin=tool_dir, expected_database=database,
                                    expected_system_identifier=system, app_sha=os.environ["GITHUB_SHA"])
        admin.execute("ALTER ROLE postgres NOLOGIN")
        with service.connect() as db:
            try:
                service.writer_gate(db)
            except RuntimeError as error:
                if "Other database login roles" not in str(error):
                    raise AssertionError("Unexpected failure instead of login role rejection") from error
            else:
                raise AssertionError("Additional login role was accepted")
        admin.execute(sql.SQL("ALTER ROLE {} NOLOGIN").format(sql.Identifier(runtime)))
        with service.connect() as db:
            try:
                service.writer_gate(db)
            except RuntimeError as error:
                if "Other source database sessions" not in str(error):
                    raise AssertionError("Unexpected failure instead of active session rejection") from error
            else:
                raise AssertionError("Active competing connection was accepted")
        runtime_connection.close()
        runtime_connection = None
        try:
            psycopg.connect(**{**options, "user": runtime}).close()
        except psycopg.OperationalError:
            pass
        else:
            raise AssertionError("NOLOGIN runtime role reconnected")

        try:
            service.backup(media_root=media, destination=root / "must-not-exist.zip")
        except RuntimeError as error:
            if "read-only" not in str(error):
                raise
        else:
            raise AssertionError("Writable media incorrectly accepted")
        assert not (root / "must-not-exist.zip").exists()
        command("sudo", "mount", "-o", "remount,ro", media)

        # A real independent mount process changes the kernel state while the
        # actual pg_dump is running. Only the timing hook is instrumented: the
        # filesystem verifier itself and all database operations remain real.
        original_tool = service.tool
        for fault in ("remount", "changed-file"):
            hook_fired = []
            def interrupted(name, *args, fault=fault):
                result = original_tool(name, *args)
                if name == "pg_dump" and "--file" in args:
                    command("sudo", "mount", "-o", "remount,rw", media)
                    hook_fired.append(True)
                    if fault == "changed-file":
                        command(sys.executable, "-c", "from pathlib import Path; import sys; Path(sys.argv[1]).write_bytes(b'CHANGED SYNTHETIC')", voucher)
                        command("sudo", "mount", "-o", "remount,ro", media)
                return result
            service.tool = interrupted
            rejected_path = root / (fault + ".zip")
            try:
                service.backup(media_root=media, destination=rejected_path)
            except RuntimeError as error:
                expected = "read-only" if fault == "remount" else "Media fence or contents changed"
                if not hook_fired or expected not in str(error):
                    raise AssertionError(f"{fault}: unexpected failure, not the required real media check") from error
            else:
                raise AssertionError(fault + " was not detected")
            assert not rejected_path.exists()
            command("sudo", "mount", "-o", "remount,rw", media)
            voucher.write_bytes(b"SYNTHETIC PRIVATE VOUCHER\n")
            command("sudo", "mount", "-o", "remount,ro", media)
        service.tool = original_tool
        backup = service.backup(media_root=media, destination=root / "verified.zip")
        restored = service.restore(archive=root / "verified.zip", expected_sha256=backup["sha256"], media_parent=root)
        assert restored["verified"] and restored["audit_truncate_rejected"]
        restored_voucher = Path(restored["media_root"]) / "finance-vouchers/synthetic.bin"
        assert digest(restored_voucher) == voucher_sha
        with psycopg.connect(**{**options, "dbname": restored["database"]}) as db:
            assert db.execute("SELECT file,sha256,size FROM crm_financevoucher").fetchone() == ("finance-vouchers/synthetic.bin", voucher_sha, voucher.stat().st_size)
        with psycopg.connect(**options) as db:
            assert database_state(db) == before

        # Real ENOSPC on a second task-owned loop filesystem; the source media
        # and database remain untouched and no success filename may appear.
        full_image, full_mount = root / "full.img", root / "full-volume"
        command("truncate", "-s", "16M", full_image)
        command("mkfs.ext4", "-q", "-F", "-m", "0", full_image)
        full_mount.mkdir()
        command("sudo", "mount", "-o", "loop", full_image, full_mount)
        try:
            command("sudo", "chmod", "777", full_mount)
            filler = os.open(full_mount / "synthetic-filler", os.O_CREAT | os.O_WRONLY | os.O_EXCL, 0o600)
            try:
                while True:
                    os.write(filler, b"x" * 65536)
            except OSError as error:
                if error.errno != errno.ENOSPC:
                    raise
            finally:
                os.close(filler)
            try:
                service.backup(media_root=media, destination=full_mount / "must-not-exist.zip")
            except OSError as error:
                if error.errno != errno.ENOSPC:
                    raise
            else:
                raise AssertionError("Actual full filesystem unexpectedly accepted backup")
            assert not (full_mount / "must-not-exist.zip").exists()
        finally:
            command("sudo", "umount", full_mount)

        # Induce actual Linux EACCES after publication by removing write access
        # to this job-created directory at the exact link boundary. The real
        # kernel unlink fails; only the timing of the permission change is hooked.
        if os.geteuid() == 0:
            raise RuntimeError("Cleanup-permission test requires an unprivileged runner")
        cleanup_dir = root / "cleanup-failure"
        cleanup_dir.mkdir(mode=0o700)
        actual_link = os.link
        def remove_directory_write(source, destination, **kwargs):
            result = actual_link(source, destination, **kwargs)
            cleanup_dir.chmod(0o500)
            return result
        try:
            with mock.patch("crm.services.operations_postgres.os.link", side_effect=remove_directory_write):
                with publish_archive(cleanup_dir / "verified.zip") as output:
                    output.write(b"SYNTHETIC VERIFIED ARCHIVE")
            assert output.staging_cleanup_warning == "PermissionError"
            assert (cleanup_dir / "verified.zip").read_bytes() == b"SYNTHETIC VERIFIED ARCHIVE"
            assert len(list(cleanup_dir.glob("*.partial"))) == 1
        finally:
            cleanup_dir.chmod(0o700)
            shutil.rmtree(cleanup_dir)

        # Stop only the process group spawned here while it is writing its
        # partial archive. A SIGTERM cannot leave a published success filename.
        interrupt_dir = root / "interrupt-test"
        interrupt_dir.mkdir(mode=0o700)
        child_code = '''import os, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()
from crm.services.operations_postgres import MaintenanceBackup
root=os.environ["SUNJACK_CI_ROOT"]
options={"host":"127.0.0.1","port":int(os.environ["SUNJACK_CI_POSTGRES_PORT"]),"user":"sunjack_ci_maint","dbname":"sunjack_ci_source","sslmode":"disable"}
service=MaintenanceBackup(connection_options=options,pg_bin=root+"/pg-tools",expected_database="sunjack_ci_source",expected_system_identifier=os.environ["SUNJACK_CI_SYSTEM_ID"],app_sha=os.environ["GITHUB_SHA"])
service.backup(media_root=root+"/media",destination=root+"/interrupt-test/must-not-exist.zip")
'''
        child_env = {**os.environ, "SUNJACK_CI_SYSTEM_ID": str(system)}
        child = subprocess.Popen([sys.executable, "-c", child_code], env=child_env, stdout=subprocess.DEVNULL,
                                 stderr=subprocess.PIPE, start_new_session=True)
        try:
            deadline = time.monotonic() + 180
            partials = []
            while time.monotonic() < deadline:
                if child.poll() is not None:
                    raise RuntimeError("Backup exited before interruption could be exercised")
                partials = [p for p in interrupt_dir.glob("*.partial") if p.stat().st_size > 0]
                if partials:
                    break
                time.sleep(0.01)
            else:
                raise RuntimeError("Timed out waiting for a live backup partial")
            os.killpg(child.pid, signal.SIGTERM)
            child.wait(timeout=15)
            assert not (interrupt_dir / "must-not-exist.zip").exists()
            assert partials and interrupt_dir.resolve().parent == root
            for partial in interrupt_dir.iterdir():
                if partial.is_symlink() or not re.fullmatch(r"\.sunjack-[0-9a-f]{32}\.partial", partial.name):
                    raise RuntimeError("Refusing to remove an unknown interruption artifact")
                partial.unlink()
        finally:
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGTERM)
                child.wait(timeout=15)
            if child.stderr:
                child.stderr.close()

        # Use real GnuPG, actual restored databases, independent signing key and
        # public verification. Same-host replicas are not disaster recovery.
        archive_root, replica_root, key_root = root / "archives", root / "replicas", root / "keys"
        archive_root.mkdir(mode=0o700); replica_root.mkdir(mode=0o700); key_root.mkdir(mode=0o700)
        owner = uuid.uuid4().hex
        (archive_root / ".sunjack-backup-owner").write_text(owner, encoding="ascii")
        (archive_root / ".sunjack-backup-owner").chmod(0o600)
        private, public = key_root / "private.pem", key_root / "public.pem"
        openssl, gpg = shutil.which("openssl"), shutil.which("gpg")
        if not openssl or not gpg:
            raise RuntimeError("OpenSSL and GnuPG are required")
        command(openssl, "genpkey", "-algorithm", "EC", "-pkeyopt", "ec_paramgen_curve:P-256", "-out", private, capture_output=True)
        private.chmod(0o600)
        public.write_bytes(_openssl(openssl, "pkey", "-in", private, "-pubout"))
        verification = {"executable": openssl, "public_key": str(public), "pinned_fingerprint": public_key_fingerprint(openssl, public), "max_age_seconds": 86400}
        key = secrets.token_hex(32).encode()
        now = datetime.now(timezone.utc)
        receipts = []
        for age in (1, 2, 3):
            encrypted = archive_root / ("backup-" + uuid.uuid4().hex + ".gpg")
            cipher = crypt_file(root / "verified.zip", encrypted, executable=gpg, key=key, expected_sha256=backup["sha256"])
            if age == 1:
                try:
                    crypt_file(encrypted, root / "wrong-key-output", executable=gpg, key=secrets.token_hex(32).encode(),
                               expected_sha256=backup["sha256"], decrypt=True)
                except RuntimeError:
                    assert not (root / "wrong-key-output").exists()
                else:
                    raise AssertionError("Wrong encryption key was accepted")
                wrong_key = key_root / "synthetic-wrong.key"
                wrong_key.write_bytes(secrets.token_hex(32).encode())
                wrong_key.chmod(0o600)
                wrong_config = root / "synthetic-wrong-key.json"
                wrong_config.write_text(json.dumps({"source": str(encrypted), "destination": str(root / "wrong-key-cli-output"),
                    "executable": gpg, "key_file": str(wrong_key), "expected_sha256": backup["sha256"]}), encoding="utf-8")
                wrong = subprocess.run([sys.executable, str(backend / "operations_archive.py"), "decrypt", "--config", str(wrong_config)],
                                       capture_output=True, text=True, timeout=60)
                assert wrong.returncode == 1 and json.loads(wrong.stdout)["status"] == "FAILED"
                assert not (root / "wrong-key-cli-output").exists()
            timestamp = (now-timedelta(days=age)).timestamp()
            os.utime(encrypted, (timestamp, timestamp))
            signed, signed_restore = restore_and_sign(service, encrypted_archive=encrypted, encrypted_sha256=cipher["sha256"],
                plaintext_sha256=backup["sha256"], media_parent=root, gpg_executable=gpg, encryption_key=key,
                openssl_executable=openssl, signing_key=private)
            assert signed_restore["verified"] and digest(Path(signed_restore["media_root"]) / "finance-vouchers/synthetic.bin") == voucher_sha
            replica = replica_root / encrypted.name
            verified_copy(encrypted, replica, cipher["sha256"])
            receipts.append({"name": encrypted.name, "sha256": cipher["sha256"], "restore_receipt": signed, "replica": str(replica),
                             "created_at": datetime.fromtimestamp(encrypted.stat().st_mtime_ns/1_000_000_000, timezone.utc).isoformat()})
        original = receipts[0]["restore_receipt"]
        attacker_key = key_root / "synthetic-attacker.pem"
        command(openssl, "genpkey", "-algorithm", "EC", "-pkeyopt", "ec_paramgen_curve:P-256", "-out", attacker_key, capture_output=True)
        attacker_signature = _openssl(openssl, "dgst", "-sha256", "-sign", attacker_key, data=_canonical(original["payload"]))
        forged = {"payload": original["payload"], "signature": base64.b64encode(attacker_signature).decode("ascii")}
        for bad in (None, receipts[1]["restore_receipt"], forged, {"payload": {**original["payload"], "app_sha": "f" * 40}, "signature": original["signature"]}):
            receipts[0]["restore_receipt"] = bad
            try:
                prune_verified(archive_root, owner_id=owner, receipts=receipts, keep=1, minimum_age_seconds=86400,
                               receipt_verification=verification, execute=True)
            except ValueError:
                pass
            else:
                raise AssertionError("Forged, absent or wrong-archive receipt accepted")
            assert all((archive_root / receipt["name"]).exists() for receipt in receipts)
        receipts[0]["restore_receipt"] = original
        monitor_verification = {**verification, "max_age_seconds": 7 * 86400}
        monitor_options = {"archive": archive_root / receipts[0]["name"], "restore_receipt": original,
                           "receipt_verification": monitor_verification, "maximum_backup_age_seconds": 2 * 86400}
        assert check_backup_freshness(**monitor_options)["status"] == "OK"
        try:
            check_backup_freshness(**monitor_options, now=datetime.now(timezone.utc)+timedelta(days=2))
        except RuntimeError:
            pass
        else:
            raise AssertionError("A missed schedule was not detected")
        receipt_file = root / "verified-receipt.json"
        receipt_file.write_text(json.dumps(original), encoding="utf-8")
        monitor_config = root / "monitor.json"
        monitor_config.write_text(json.dumps({"archive": str(archive_root / receipts[0]["name"]),
            "receipt_file": str(receipt_file), "receipt_verification": monitor_verification,
            "maximum_backup_age_seconds": 2 * 86400}), encoding="utf-8")
        monitor_script = backend / "operations_monitor.py"
        monitor = subprocess.run([sys.executable, str(monitor_script), "--config", str(monitor_config)],
                                 capture_output=True, text=True, timeout=60)
        assert monitor.returncode == 0 and json.loads(monitor.stdout)["status"] == "OK"
        monitor_config.write_text(json.dumps({"archive": str(archive_root / receipts[0]["name"]),
            "receipt_file": str(receipt_file), "receipt_verification": monitor_verification,
            "maximum_backup_age_seconds": 3600}), encoding="utf-8")
        monitor = subprocess.run([sys.executable, str(monitor_script), "--config", str(monitor_config)],
                                 capture_output=True, text=True, timeout=60)
        assert monitor.returncode == 1 and json.loads(monitor.stdout)["status"] == "ALERT"
        scheduler = exercise_owned_timer(backend, monitor_script, monitor_config)
        logger = shutil.which("logger")
        if logger:
            alert = subprocess.run([logger, "-s", "-p", "user.err", "--", "SUNJACK synthetic missed-backup alert"],
                                   capture_output=True, text=True, timeout=15)
            local_alert = "PASS" if alert.returncode == 0 else "BLOCKED: local syslog unavailable"
        else:
            local_alert = "BLOCKED: logger unavailable"
        loopback_alert = "BLOCKED: logger unavailable"
        if logger:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as receiver:
                receiver.bind(("127.0.0.1", 0))
                receiver.settimeout(5)
                port = receiver.getsockname()[1]
                sent = subprocess.run([logger, "--server", "127.0.0.1", "--port", str(port), "--udp", "--priority", "user.err", "--", "SUNJACK synthetic missed-backup alert"],
                                      capture_output=True, text=True, timeout=15)
                if sent.returncode == 0:
                    message, _ = receiver.recvfrom(4096)
                    assert b"SUNJACK synthetic missed-backup alert" in message
                    loopback_alert = "PASS: task-owned loopback receiver"
                else:
                    loopback_alert = "BLOCKED: logger loopback delivery failed"
        archive_root.chmod(0o770)
        try:
            try:
                prune_verified(archive_root, owner_id=owner, receipts=receipts, keep=1, minimum_age_seconds=86400,
                               receipt_verification=verification, execute=True)
            except ValueError as error:
                if "exclusively controlled" not in str(error):
                    raise
            else:
                raise AssertionError("Group-writable retention root was accepted")
        finally:
            archive_root.chmod(0o700)
        assert all((archive_root / receipt["name"]).exists() for receipt in receipts)
        time.sleep(1.2)
        try:
            prune_verified(archive_root, owner_id=owner, receipts=receipts, keep=1, minimum_age_seconds=86400,
                           receipt_verification={**verification, "max_age_seconds": 1}, execute=True)
        except ValueError as error:
            if "expired" not in str(error):
                raise
        else:
            raise AssertionError("Expired signed receipt accepted")
        result = prune_verified(archive_root, owner_id=owner, receipts=receipts, keep=1, minimum_age_seconds=86400,
                                receipt_verification=verification, execute=True)
        assert len(result["removed"]) == 2 and len(list(replica_root.iterdir())) == 3
        with psycopg.connect(**options) as db:
            assert database_state(db) == before
        assert digest(voucher) == voucher_sha
        print(json.dumps({"status": "PASS", "source_sha": os.environ["GITHUB_SHA"], "postgres_major": 17,
            "maintenance_non_superuser": True, "application_non_superuser": True, "runtime_insert_allowed": True,
            "runtime_update_delete_truncate_denied": True, "other_login_rejected": True, "active_connection_rejected": True,
            "actual_readonly_media": True, "independent_write_protection": "tested in media-fence job",
            "remount_during_backup_rejected": True, "changed_file_during_backup_rejected": True,
            "restored_private_voucher_sha256": voucher_sha, "real_signed_restores": len(receipts),
            "forged_wrong_archive_expired_rejected": True, "retention_deleted": len(result["removed"]),
            "group_writable_retention_root_rejected": True,
            "missed_schedule_detected": True,
            "monitor_healthy_and_failure_exit_codes_verified": True, "local_alert_entry": local_alert,
            "loopback_alert_delivery": loopback_alert,
            "transient_scheduler": scheduler,
            "wrong_key_rejected": True, "actual_enospc_rejected": True, "interrupted_backup_not_published": True,
            "real_cleanup_permission_failure_reported": True,
            "replicas_same_runner_only": True, "tables": len(before["tables"]),
            "source_database_and_voucher_unchanged": True,
            "rows": sum(entry["rows"] for entry in before["tables"].values()), "seconds": round(time.monotonic()-start, 3)}))
    finally:
        if runtime_connection is not None:
            runtime_connection.close()
        admin.close()


if __name__ == "__main__":
    main()
