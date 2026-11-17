"""Verify an ALEX backup on a separate Windows computer with an isolated PG17 cluster."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
from zipfile import ZipFile

PORT = 18291
APP_CHECK = """
import hashlib
import json
import os
import secrets
from pathlib import Path
from django.contrib.auth import get_user_model
from django.test import Client
from crm.models import FinanceVoucher
from crm.services.operations_receipt import public_key_fingerprint, verify_receipt
options = json.loads(os.environ["SJERP_RESTORE_RECEIPT_CHECK"])
verification_key = Path(options["public_key"])
receipt = json.loads(Path(options["receipt"]).read_text(encoding="utf-8"))
fingerprint = public_key_fingerprint(options["openssl"], verification_key)
payload = verify_receipt(
    receipt, encrypted_sha256=options["encrypted_sha256"], executable=options["openssl"],
    public_key=verification_key, pinned_fingerprint=fingerprint, max_age_seconds=3600,
)
for field in ("source_system_identifier", "target_system_identifier", "restored_database", "app_sha"):
    assert str(payload[field]) == options[field], field

users = get_user_model()
assert users.objects.filter(username="johnson", is_superuser=True, is_active=True).exists()
operator = "restore_probe_" + secrets.token_hex(8)
password = secrets.token_urlsafe(36)
users.objects.create_superuser(username=operator, password=password)
client = Client()
response = client.post("/api/session/login/", {"username": operator, "password": password},
                       content_type="application/json", secure=True)
assert response.status_code == 200
files = 0
downloads = 0
for voucher in FinanceVoucher.objects.order_by("pk"):
    with voucher.file.open("rb") as attachment:
        assert hashlib.file_digest(attachment, "sha256").hexdigest() == voucher.sha256
    files += 1
    if voucher.scope == "account":
        response = client.get("/api/finance-ledger/voucher-download/", {"id": voucher.pk}, secure=True)
        assert response.status_code == 200
        assert hashlib.sha256(b"".join(response.streaming_content)).hexdigest() == voucher.sha256
        downloads += 1
assert files and downloads, "Acceptance archive must contain the LAN verification attachments"
response = client.get("/api/reports/data/", {"source": "sales", "export": "csv"}, secure=True)
assert response.status_code == 200 and "text/csv" in response.headers["Content-Type"]
print(json.dumps({"signed_receipt": True, "login": True, "hashed_attachments": files, "downloaded_attachments": downloads, "csv": True}))
"""


def run(*args, **kwargs):
    return subprocess.run(args, check=True, text=True, **kwargs)


def sha256(path):
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def extract_bundle(args, directory):
    if sha256(args.bundle) != args.bundle_sha256:
        raise ValueError("Backup bundle SHA-256 mismatch")
    archive = directory / "archive"
    archive.mkdir()
    with ZipFile(args.bundle) as bundle:
        if sorted(bundle.namelist()) != ["database-and-media.gpg", "manifest.json", "recovery-key.bin"]:
            raise ValueError("Unknown or duplicated backup entries")
        if bundle.getinfo("manifest.json").file_size > 4096 or bundle.getinfo("recovery-key.bin").file_size != 384:
            raise ValueError("Backup metadata size mismatch")
        manifest = json.loads(bundle.read("manifest.json"))
        if (manifest["format"] != 1 or not re.fullmatch(r"[0-9]{10,32}", manifest["source_system_identifier"])
                or not re.fullmatch(r"[a-f0-9]{40}", manifest["commit"])
                or not re.fullmatch(r"[a-f0-9]{64}", manifest["plaintext_sha256"])
                or sha256(args.public_key) != manifest["recovery_public_sha256"]):
            raise ValueError("Backup metadata or recipient key mismatch")
        for name, field in (("database-and-media.gpg", "encrypted_sha256"), ("recovery-key.bin", "wrapped_key_sha256")):
            path = archive / name
            with bundle.open(name) as source, path.open("xb") as target:
                shutil.copyfileobj(source, target)
            if sha256(path) != manifest[field]:
                raise ValueError(f"Backup entry checksum mismatch: {name}")
    return manifest, archive


def restore(args):
    if os.name != "nt" or socket.gethostname().split(".")[0].lower() == "alex":
        raise ValueError("Run this drill on the separate Windows recovery computer")
    args.output.mkdir()
    target = args.output.resolve(strict=True)
    archive_manifest, inputs = extract_bundle(args, target)
    checkout = args.checkout
    commit = run("git", "-C", checkout, "rev-parse", "HEAD", capture_output=True).stdout.strip()
    if commit != archive_manifest["commit"]:
        raise ValueError("Recovery checkout does not match backup")
    if run("git", "-C", checkout, "status", "--porcelain", "--untracked-files=all", "--", "backend", "templates",
           capture_output=True).stdout.strip():
        raise ValueError("Recovery checkout has changed")
    pg = args.pg_bin
    if not re.search(r"\b17\.\d+", run(pg / "initdb.exe", "--version", capture_output=True).stdout):
        raise ValueError("PostgreSQL 17 required")
    media = target / "media"
    media.mkdir()
    cluster = target / "isolated-pg"
    receipt = target / "signed-receipt.json"
    public_receipt = target / "receipt-signing-public.pem"

    with tempfile.TemporaryDirectory(prefix="sjerp-drill-private-", dir=target) as private_dir:
        private = Path(private_dir)
        init_pass = private / "init-password"
        db_password = secrets.token_hex(48)
        init_pass.write_text(db_password + "\n", encoding="ascii")
        pgpass = private / "pgpass"
        pgpass.write_text(f"127.0.0.1:{PORT}:*:postgres:{db_password}\n", encoding="ascii")
        signing = private / "receipt-signing.key"
        key = private / "backup.key"
        unlock = Path(__file__).resolve().with_name("Unlock-AlexRecoveryKey.ps1")
        run("pwsh", "-NoProfile", "-NonInteractive", "-File", unlock, "-ProtectedKey", args.protected_key,
            "-PublicKey", args.public_key, "-Envelope", inputs / "recovery-key.bin", "-Output", key)
        run(args.openssl, "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:3072", "-out", signing,
            stderr=subprocess.DEVNULL)
        run(args.openssl, "pkey", "-in", signing, "-pubout", "-out", public_receipt)
        run(pg / "initdb.exe", "-D", cluster, "-U", "postgres", "--no-locale", "--encoding=UTF8",
            "--auth=scram-sha-256", f"--pwfile={init_pass}", stdout=subprocess.DEVNULL)
        init_pass.unlink()
        service = (pg / "pg_ctl.exe", "-D", cluster, "-w")
        run(*service, "-l", target / "postgres.log", "-o", f"-h 127.0.0.1 -p {PORT}", "start", stdout=subprocess.DEVNULL)
        try:
            env = {**os.environ, "APP_STAGE": "staging", "DJANGO_ALLOWED_HOSTS": "testserver",
                   "DJANGO_SECRET_KEY": secrets.token_hex(48), "PGPASSFILE": str(pgpass),
                   "MEDIA_ROOT": str(media), "PYTHONDONTWRITEBYTECODE": "1"}
            env["DATABASE_URL"] = f"postgresql://postgres@127.0.0.1:{PORT}/postgres"
            target_id = run(pg / "psql.exe", "-XAtw", "-h", "127.0.0.1", "-p", str(PORT), "-U", "postgres",
                            "-d", "postgres", "-c", "SELECT system_identifier FROM pg_control_system()",
                            env=env, capture_output=True).stdout.strip()
            if not target_id.isdecimal() or target_id == archive_manifest["source_system_identifier"]:
                raise ValueError("Recovery database identity overlaps source")
            config = private / "restore.json"
            config.write_text(json.dumps({
                "connection": {"host": "127.0.0.1", "port": PORT, "user": "postgres", "dbname": "postgres",
                               "passfile": str(pgpass), "sslmode": "disable"},
                "pg_bin": str(pg), "expected_database": "postgres", "expected_system_identifier": target_id,
                "app_sha": commit, "archive": str(inputs / "database-and-media.gpg"), "media_parent": str(media),
                "expected_sha256": archive_manifest["plaintext_sha256"], "encrypted_sha256": archive_manifest["encrypted_sha256"],
                "encryption": {"key_file": str(key), "executable": str(args.gpg), "msys_paths": True},
                "receipt_signing": {"private_key": str(signing), "executable": str(args.openssl)},
                "receipt_output": str(receipt),
            }), encoding="utf-8")
            backend = checkout / "backend"
            completed = subprocess.run([sys.executable, backend / "operations_backup.py", "restore-encrypted-verify",
                                        "--config", config], cwd=backend, env=env, capture_output=True, text=True)
            result = json.loads(completed.stdout)
            if completed.returncode or result["status"] != "VERIFIED" or not result["database"].startswith("sunjack_restore_"):
                raise RuntimeError(f"Restore verification failed ({result.get('error_type', 'unknown')})")
            env["DATABASE_URL"] = f"postgresql://postgres@127.0.0.1:{PORT}/{result['database']}"
            env["MEDIA_ROOT"] = str(Path(result["media_root"]).resolve(strict=True))
            env["SJERP_RESTORE_RECEIPT_CHECK"] = json.dumps({
                "public_key": str(public_receipt), "receipt": str(receipt), "openssl": str(args.openssl),
                "encrypted_sha256": archive_manifest["encrypted_sha256"],
                "source_system_identifier": archive_manifest["source_system_identifier"],
                "target_system_identifier": target_id, "restored_database": result["database"], "app_sha": commit,
            })
            probe = run(sys.executable, backend / "manage.py", "shell", "-c", APP_CHECK, cwd=backend,
                        env=env, capture_output=True).stdout.splitlines()
            evidence = json.loads(probe[-1])
        finally:
            run(*service, "-m", "fast", "stop", stdout=subprocess.DEVNULL)
    evidence.update(status="VERIFIED", host=socket.gethostname(), source_cluster=archive_manifest["source_system_identifier"],
                    target_cluster=target_id, commit=commit, bundle_sha256=args.bundle_sha256)
    (target / "verification.json").write_text(json.dumps(evidence, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(evidence, sort_keys=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("bundle", "checkout", "pg-bin", "openssl", "gpg", "public-key", "protected-key", "output"):
        parser.add_argument("--" + name, type=lambda value: Path(value).absolute(), required=True)
    parser.add_argument("--bundle-sha256", type=str.lower, required=True)
    restore(parser.parse_args())
