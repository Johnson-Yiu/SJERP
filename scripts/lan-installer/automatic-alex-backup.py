"""Create an encrypted database and media backup from the dedicated ALEX ERP VM."""

import fcntl
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
from zipfile import ZIP_STORED, ZipFile

ROOT = Path("/srv/sjerp")
STATE = Path("/var/lib/sjerp-automatic-backup")
CONFIG = Path("/etc/sjerp/a")
MEDIA = Path("/var/lib/sjerp/a/private-media")
UNIT = "sjerp-local@a.service"
PG = Path("/usr/lib/postgresql/17/bin")
MARKER = STATE / "maintenance-active"
DATABASE = "sjerp_a"
LOGIN = "postgres"
STATUS = STATE / "latest.zip"
PSQL = ("runuser", "-u", "postgres", "--", PG / "psql", "-Xd", "postgres", "-v", "ON_ERROR_STOP=1")
FENCE = r"""
import psycopg
import sys

with psycopg.connect(dbname="postgres", user="postgres", autocommit=True) as db:
    names = {row[0] for row in db.execute("SELECT datname FROM pg_database")}
    roles = {row[0] for row in db.execute("SELECT rolname FROM pg_roles WHERE rolcanlogin")}
    assert names == {"postgres", "template0", "template1", "sjerp_a"}, names
    assert roles == {"postgres", "sjerp_a_runtime", "sjerp_a_migrate"}, roles
    print(db.execute("SELECT system_identifier FROM pg_control_system()").fetchone()[0], flush=True)
    if sys.stdin.readline() != "FENCE\n":
        raise SystemExit(1)
    with db.transaction():
        db.execute("ALTER ROLE sjerp_a_runtime NOLOGIN")
        db.execute("ALTER ROLE sjerp_a_migrate NOLOGIN")
    try:
        print("FENCED", flush=True)
        sys.stdin.readline()
    finally:
        with db.transaction():
            db.execute("ALTER ROLE sjerp_a_migrate LOGIN")
            db.execute("ALTER ROLE sjerp_a_runtime LOGIN")
"""


def run(*argv, **kwargs):
    return subprocess.run(argv, check=True, text=True, **kwargs)


def digest(path):
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def mount_options():
    result = run("findmnt", "-n", "-o", "FSTYPE,OPTIONS", "--mountpoint", MEDIA,
                 stdout=subprocess.PIPE)
    fs, options = result.stdout.strip().split(None, 1)
    if fs != "ext4":
        raise RuntimeError("Expected dedicated ext4 media volume")
    return set(options.split(","))


def recover(settings):
    if not MARKER.exists():
        return
    cluster = (STATE / "source-cluster").read_text().strip()
    actual = run(*PSQL, "-Atc", "SELECT system_identifier FROM pg_control_system()",
                 stdout=subprocess.PIPE).stdout.strip()
    if actual != cluster or MARKER.read_text().strip() != cluster:
        raise RuntimeError("Refusing to recover another PostgreSQL cluster")
    run(*PSQL, "-qc", "ALTER ROLE sjerp_a_migrate LOGIN; ALTER ROLE sjerp_a_runtime LOGIN;")
    if "ro" in mount_options():
        run("mount", "-o", "remount,rw", MEDIA)
    if "rw" not in mount_options():
        raise RuntimeError("Media remained read-only")
    if settings == "online":
        run("systemctl", "start", UNIT)
    MARKER.unlink()


def backup():
    with (ROOT / ".upgrade.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if MARKER.exists() or "rw" not in mount_options():
            raise RuntimeError("Maintenance state requires recovery")
        run("systemctl", "is-active", "--quiet", UNIT)
        version = (ROOT / "current").resolve(strict=True)
        metadata = json.loads((version / "release/RELEASE.json").read_text())
        if version.parent != ROOT / "versions" or version.name != metadata["commit"]:
            raise RuntimeError("ERP release identity mismatch")
        app_sha = metadata["commit"]
        checkout = STATE / "checkout"
        if run("git", "-C", checkout, "rev-parse", "HEAD", stdout=subprocess.PIPE).stdout.strip() != app_sha:
            raise RuntimeError("Matching maintenance checkout required after upgrading")
        backend = checkout / "backend"
        python = version / "venv/bin/python"
        environment = dict(line.split("=", 1) for line in (CONFIG / "runtime.env").read_text().splitlines() if line)
        env = {**os.environ, **environment, "PYTHONDONTWRITEBYTECODE": "1"}
        with tempfile.TemporaryDirectory(prefix="run-", dir=STATE) as directory:
            work = Path(directory)
            archive_dir = work / "archive"
            archive_dir.mkdir()
            key = work / "archive.key"
            key.write_text(secrets.token_hex(48) + "\n", encoding="ascii")
            envelope = work / "recovery-key.bin"
            recipient = STATE / "recovery-public.pem"
            run("openssl", "pkeyutl", "-encrypt", "-pubin", "-inkey", recipient,
                "-pkeyopt", "rsa_padding_mode:oaep", "-pkeyopt", "rsa_oaep_md:sha256",
                "-pkeyopt", "rsa_mgf1_md:sha256", "-in", key, "-out", envelope)
            config = work / "backup.json"
            with subprocess.Popen(["runuser", "-u", "postgres", "--", python, "-u", "-c", FENCE],
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True) as admin:
                cluster = admin.stdout.readline().strip()
                if not cluster.isdecimal() or cluster != (STATE / "source-cluster").read_text().strip():
                    raise RuntimeError("Dedicated database cluster identity mismatch")
                config.write_text(json.dumps({
                    "connection": {"host": "/var/run/postgresql", "port": 5432, "user": LOGIN,
                                   "dbname": DATABASE, "sslmode": "disable"},
                    "pg_bin": str(PG), "expected_database": DATABASE, "expected_system_identifier": cluster,
                    "app_sha": app_sha, "media_root": str(MEDIA), "destination_directory": str(archive_dir),
                    "encryption": {"key_file": str(key), "executable": "/usr/bin/gpg"},
                }))
                try:
                    with MARKER.open("x") as marker:
                        marker.write(cluster + "\n")
                        marker.flush()
                        os.fsync(marker.fileno())
                    os.sync()
                    run("systemctl", "stop", UNIT)
                    run("mount", "-o", "remount,ro", MEDIA)
                    admin.stdin.write("FENCE\n")
                    admin.stdin.flush()
                    if admin.stdout.readline().strip() != "FENCED":
                        raise RuntimeError("Database fence could not be established")
                    result = run(python, backend / "operations_backup.py", "backup", "--config", config,
                                 cwd=backend, env=env, stdout=subprocess.PIPE, timeout=1200)
                finally:
                    admin.stdin.close()
                    try:
                        admin.wait(timeout=20)
                    finally:
                        recover("online")
            receipt = json.loads(result.stdout)
            archive = Path(receipt["archive"])
            if (receipt["status"] != "VERIFIED" or receipt.get("encryption_roundtrip_verified") is not True
                    or archive.parent != archive_dir or archive.is_symlink() or digest(archive) != receipt["sha256"]):
                raise RuntimeError("Encrypted backup failed verification")
            manifest = {"format": 1, "commit": app_sha, "source_system_identifier": cluster,
                        "encrypted_sha256": receipt["sha256"], "plaintext_sha256": receipt["plaintext_sha256"],
                        "wrapped_key_sha256": digest(envelope), "recovery_public_sha256": digest(recipient)}
            candidate = work / "result.zip"
            with ZipFile(candidate, "x", compression=ZIP_STORED) as bundle:
                bundle.write(archive, "database-and-media.gpg")
                bundle.write(envelope, "recovery-key.bin")
                bundle.writestr("manifest.json", json.dumps(manifest, sort_keys=True))
            os.replace(candidate, STATUS)
            print("SJERP automatic joint backup verified", flush=True)


if __name__ == "__main__":
    os.umask(0o077)
    if os.geteuid() != 0 or os.uname().nodename.split(".")[0] != "sjerp-image-test":
        raise SystemExit("Unexpected user or backup source host")
    if sys.argv[1:] == ["backup"]:
        backup()
    elif sys.argv[1:] == ["recover-online"]:
        recover("online")
    elif sys.argv[1:] == ["recover-boot"]:
        recover("boot")
    else:
        raise SystemExit("Unknown maintenance operation")
