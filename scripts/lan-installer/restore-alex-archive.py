"""Recover the deployed ALEX encrypted archive into a separate local PG17 cluster."""
import hashlib
import json
import os
from pathlib import Path
import pwd
import secrets
import shutil
import subprocess
import sys
import tempfile


SOURCE = "3b156502472478f47ae015ae51d3ac92c1edc42a"
PACK_SHA = "0aabea9ad4cfba037ea1057c943f1a10c2f18d37b309843e26b1f4e09dc33aa1"
ARCHIVE = "backup-9bbea3f05507489dbe4cb98c8be48f56.gpg"
SHA = "0ae73eec385c1015297fbfb40ba83ab2ecf66b837def85edeb32fce63f4097a9"
PYTHON = Path("/srv/sjerp/versions") / SOURCE / "venv/bin/python"
PG = Path("/usr/lib/postgresql/17/bin")
STATUS = Path("/etc/issue.d/97-sjerp-recovery.issue")
PORT = 18291
APP_CHECK = r"""
import hashlib, json, secrets
from django.contrib.auth import get_user_model
from django.test import Client
from crm.models import FinanceVoucher
users = get_user_model()
assert users.objects.filter(username="johnson", is_superuser=True, is_active=True, first_name="姚战森").exists()
password = secrets.token_urlsafe(36)
operator = "restore_probe_" + secrets.token_hex(8)
users.objects.create_superuser(username=operator, password=password)
client = Client()
response = client.post("/api/session/login/", {"username": operator, "password": password},
                       content_type="application/json", secure=True)
assert response.status_code == 200
verified = 0
for voucher in FinanceVoucher.objects.order_by("pk"):
    expected = voucher.sha256
    with voucher.file.open("rb") as attachment:
        assert hashlib.file_digest(attachment, "sha256").hexdigest() == expected
    if voucher.scope == "account":
        response = client.get("/api/finance-ledger/voucher-download/", {"id": voucher.pk}, secure=True)
        assert response.status_code == 200
        assert hashlib.sha256(b"".join(response.streaming_content)).hexdigest() == expected
        verified += 1
assert verified >= 2
response = client.get("/api/reports/data/", {"source":"sales","export":"csv"}, secure=True)
assert response.status_code == 200 and "text/csv" in response.headers["Content-Type"]
print("RESTORED_APP_VERIFIED", verified)
"""


def run(*args, **kwargs):
    return subprocess.run(args, check=True, text=True, **kwargs)


def digest(file):
    with file.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def report(value):
    STATUS.write_text(value + "\n", encoding="utf-8")
    STATUS.chmod(0o644)


def main(seed):
    if os.geteuid() != 0 or os.uname().nodename.split(".")[0] != "sjerp-image-test":
        raise RuntimeError("Not the ALEX ERP guest")
    run("systemctl", "is-active", "--quiet", "sjerp-local@a")
    archive = seed / "archive.gpg"
    if digest(archive) != SHA or digest(seed / "source.pack") != PACK_SHA:
        raise ValueError("Recovery input SHA mismatch")
    records = []
    for file in Path("/etc/sjerp/a").glob("upgrade-rehearsal-*/verified-backup.json"):
        record = json.loads(file.read_text())
        if Path(record["archive"]).name == ARCHIVE and record["sha256"] == SHA and record["from"] == SOURCE:
            records.append((file.parent, record))
    if len(records) != 1:
        raise RuntimeError("No unique protected backup record")
    original, record = records[0]
    key = original / "archive.key"

    report("SJERP ISOLATED RESTORE IN PROGRESS")
    parent = Path("/var/lib/sjerp-recovery")
    parent.mkdir(mode=0o700, exist_ok=True)
    if parent.is_symlink() or not parent.is_dir() or parent.stat().st_uid != 0:
        raise RuntimeError("Unsafe recovery parent")
    # postgres needs traversal to reach its own data and socket directories.
    # Archive, receipt and key subdirectories stay private.
    parent.chmod(0o711)
    report("SJERP ISOLATED RESTORE IN PROGRESS: target cluster and source checkout")
    work = Path(tempfile.mkdtemp(prefix="alex-", dir=parent))
    work.chmod(0o711)
    media = work / "media"
    media.mkdir()
    recovery = work / "checkout"
    recovery.mkdir()
    inputs = work / "archive-input"
    inputs.mkdir(mode=0o700)
    restore_archive = inputs / ARCHIVE
    shutil.copyfile(archive, restore_archive)
    secrets_dir = work / "signing"
    secrets_dir.mkdir(mode=0o700)
    run("git", "-C", recovery, "init", "-q")
    with (seed / "source.pack").open("rb") as pack:
        run("git", "-C", recovery, "index-pack", "--stdin", stdin=pack)
    (recovery / ".git/shallow").write_text(SOURCE + "\n")
    run("git", "-C", recovery, "sparse-checkout", "set", "--no-cone", "/backend/", "/templates/", "/.gitignore")
    run("git", "-C", recovery, "update-ref", "HEAD", SOURCE)
    run("git", "-C", recovery, "read-tree", "-mu", "HEAD")

    account = pwd.getpwnam("postgres")
    cluster, sock = work / "cluster", work / "sock"
    for path in (cluster, sock):
        path.mkdir()
        os.chown(path, account.pw_uid, account.pw_gid)
    postgres = ("runuser", "-u", "postgres", "--")
    run(*postgres, PG / "initdb", "-D", cluster, "--no-locale", "--encoding=UTF8",
        "--auth-local=peer", "--auth-host=scram-sha-256", stdout=subprocess.DEVNULL)
    run(*postgres, PG / "pg_ctl", "-D", cluster, "-l", cluster / "postgres.log",
        "-o", f"-h 127.0.0.1 -p {PORT} -k {sock}", "-w", "start")
    try:
        psql = (*postgres, PG / "psql", "-h", sock, "-p", str(PORT), "-Xd", "postgres", "-v", "ON_ERROR_STOP=1")
        cluster_id = run(*psql, "-Atc", "SELECT system_identifier FROM pg_control_system()",
                         capture_output=True).stdout.strip()
        if cluster_id == str(record["system_identifier"]):
            raise RuntimeError("Recovery and production cluster identities overlap")
        password = secrets.token_hex(32)
        role = "sjerp_restore_operator"
        run(*psql, input=f"CREATE ROLE {role} LOGIN CREATEDB PASSWORD '{password}';\n"
                        f"GRANT EXECUTE ON FUNCTION pg_control_system() TO {role};\n")
        pgpass = work / "pgpass"
        pgpass.write_text(f"127.0.0.1:{PORT}:*:{role}:{password}\n")
        signing = secrets_dir / "receipt.key"
        run("openssl", "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:3072", "-out", signing,
            stderr=subprocess.DEVNULL)
        receipt = work / "receipt.json"
        conf = work / "restore.json"
        conf.write_text(json.dumps({
            "connection": {"host":"127.0.0.1","port":PORT,"user":role,"dbname":"postgres",
                           "passfile":str(pgpass),"sslmode":"disable"},
            "pg_bin": str(PG),"expected_database":"postgres","expected_system_identifier":cluster_id,
            "app_sha":SOURCE,"archive":str(restore_archive),"expected_sha256":record["plaintext_sha256"],
            "encrypted_sha256":SHA,"media_parent":str(media),
            "encryption":{"key_file":str(key),"executable":"/usr/bin/gpg"},
            "receipt_signing":{"private_key":str(signing),"executable":"/usr/bin/openssl"},
            "receipt_output":str(receipt),
        }))
        env = {**os.environ, "APP_STAGE":"staging","DJANGO_ALLOWED_HOSTS":"testserver",
               "DJANGO_SECRET_KEY":secrets.token_hex(48),"MEDIA_ROOT":str(media),
               "DATABASE_URL":f"postgresql://{role}@127.0.0.1:{PORT}/postgres","PGPASSFILE":str(pgpass),
               "PYTHONDONTWRITEBYTECODE":"1"}
        backend = recovery / "backend"
        report("SJERP ISOLATED RESTORE IN PROGRESS: archive and signature")
        process = subprocess.run(
            [PYTHON, backend / "operations_backup.py", "restore-encrypted-verify", "--config", conf],
            cwd=recovery, env=env, capture_output=True, text=True, check=False,
        )
        result = json.loads(process.stdout)
        if process.returncode:
            error_type = str(result.get("error_type", "Unknown"))[:48]
            report(f"SJERP ISOLATED RESTORE FAILED: archive/signature ({error_type})")
            raise RuntimeError(f"Recovery CLI error: {error_type}")
        report("SJERP ISOLATED RESTORE IN PROGRESS: application readback")
        if result["status"] != "VERIFIED" or not result["database"].startswith("sunjack_restore_"):
            raise RuntimeError("Recovery result not verified")
        env["DATABASE_URL"] = f"postgresql://{role}@127.0.0.1:{PORT}/{result['database']}"
        env["MEDIA_ROOT"] = result["media_root"]
        run(PYTHON, backend / "manage.py", "shell", "-c", APP_CHECK, cwd=backend, env=env)
        run("systemctl", "is-active", "--quiet", "sjerp-local@a")
        report("SJERP ISOLATED RESTORE READY: signed receipt, login, attachments and CSV verified")
    finally:
        run(*postgres, PG / "pg_ctl", "-D", cluster, "-m", "fast", "-w", "stop",
            stdout=subprocess.DEVNULL)


if __name__ == "__main__":
    os.umask(0o077)
    try:
        main(Path(sys.argv[1]))
    except BaseException:
        if os.geteuid() == 0 and os.uname().nodename.split(".")[0] == "sjerp-image-test":
            last = STATUS.read_text(encoding="utf-8").strip() if STATUS.exists() else ""
            if not last.startswith("SJERP ISOLATED RESTORE FAILED:"):
                stage = last.partition(": ")[2] or "preflight or target cluster"
                report(f"SJERP ISOLATED RESTORE FAILED: {stage}")
        raise
