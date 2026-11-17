"""Run an encrypted backup and same-schema release switch on the ALEX test guest."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import tempfile


SOURCE = "96276dffa07c11fb60720a439269df8c36031f7a"
TARGET = "3b156502472478f47ae015ae51d3ac92c1edc42a"
PACK_SHA = "23dbd427ccc21ceb1c350779b50d6a22cafa8073a060439ba359f557518a2322"
PAYLOAD_SHA = "28e13c1a0bbccdbfb5cb0a60b1c8d789d9d047c44f194de6cecdefe330213022"
ROOT = Path("/srv/sjerp")
VERSION = ROOT / "versions" / SOURCE
MEDIA = Path("/var/lib/sjerp/a/private-media")
UNIT = "sjerp-local@a.service"
CONFIG = Path("/etc/sjerp/a")
STATUS = Path("/etc/issue.d/92-sjerp-upgrade.issue")
PG_ADMIN = """
import psycopg, sys
with psycopg.connect(dbname="postgres", user="postgres", autocommit=True) as db:
    roles = {r[0] for r in db.execute("SELECT rolname FROM pg_roles WHERE rolcanlogin")}
    names = {r[0] for r in db.execute("SELECT datname FROM pg_database")}
    assert roles == {"postgres", "sjerp_a_runtime", "sjerp_a_migrate"}, roles
    assert names == {"postgres", "template0", "template1", "sjerp_a"}, names
    cluster = db.execute("SELECT system_identifier FROM pg_control_system()").fetchone()[0]
    print(cluster, flush=True)
    if sys.stdin.readline().strip() != "FENCE": raise SystemExit(1)
    db.execute("ALTER ROLE sjerp_a_runtime NOLOGIN")
    try:
        db.execute("ALTER ROLE postgres NOLOGIN")
        try:
            print("FENCED", flush=True)
            sys.stdin.readline()
        finally:
            db.execute("ALTER ROLE postgres LOGIN")
    finally:
        db.execute("ALTER ROLE sjerp_a_runtime LOGIN")
"""


def run(*command, **kwargs):
    return subprocess.run(command, check=True, text=True, **kwargs)


def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def report(text):
    STATUS.write_text(text + "\n", encoding="utf-8")
    STATUS.chmod(0o644)


def main(seed):
    if os.geteuid() != 0 or socket.gethostname().split(".")[0] != "sjerp-image-test":
        raise RuntimeError("仅支持隔离的 ALEX 验收来宾")
    if (ROOT / "current").resolve(strict=True) != VERSION:
        raise RuntimeError("当前版本与演练源版本不一致")
    if digest(seed / "source.pack") != PACK_SHA or digest(seed / "target.zip") != PAYLOAD_SHA:
        raise ValueError("维护源码或目标载荷摘要不符")
    run("systemctl", "is-active", "--quiet", UNIT)
    if run("findmnt", "-n", "-o", "FSTYPE", "--mountpoint", MEDIA, capture_output=True).stdout.strip() != "ext4":
        raise RuntimeError("未找到专用 ext4 媒体挂载")
    report("SJERP TEST UPGRADE IN PROGRESS")
    values = dict(line.split("=", 1) for line in (CONFIG / "runtime.env").read_text().splitlines() if line)
    env = {**os.environ, **values, "PYTHONDONTWRITEBYTECODE": "1"}
    python = VERSION / "venv/bin/python"
    target = ROOT / "versions" / TARGET
    run(python, seed / "stage.py", seed / "target.zip", PAYLOAD_SHA, ROOT / "versions", env=env)
    run("chmod", "0755", target)
    run("chmod", "-R", "a+rX", target / "release", target / "venv")
    exercise = Path(tempfile.mkdtemp(prefix="upgrade-rehearsal-", dir=CONFIG))
    checkout = exercise / "source"
    checkout.mkdir()
    run("git", "-C", checkout, "init", "-q")
    with (seed / "source.pack").open("rb") as pack:
        run("git", "-C", checkout, "index-pack", "--stdin", stdin=pack)
    (checkout / ".git/shallow").write_text(SOURCE + "\n")
    run("git", "-C", checkout, "sparse-checkout", "set", "--no-cone", "/backend/", "/templates/", "/.gitignore")
    run("git", "-C", checkout, "update-ref", "HEAD", SOURCE)
    run("git", "-C", checkout, "read-tree", "-mu", "HEAD")

    archive_dir = exercise / "archives"
    archive_dir.mkdir()
    key = exercise / "archive.key"
    key.write_text(secrets.token_hex(48) + "\n")
    backup_config = exercise / "backup.json"
    migration_env = exercise / "migration.json"
    migration = {k: values[k] for k in ("APP_STAGE", "DJANGO_ALLOWED_HOSTS", "DJANGO_SECRET_KEY", "MEDIA_ROOT")}
    migration.update(DATABASE_URL="postgresql://sjerp_a_migrate@127.0.0.1:5432/sjerp_a",
                     PGPASSFILE=str(CONFIG / "migration.pgpass"))
    migration_env.write_text(json.dumps(migration))
    marker = MEDIA / ("upgrade-rehearsal-" + secrets.token_hex(8) + ".txt")
    marker.write_text("Synthetic SJERP upgrade rehearsal attachment\n")
    marker_sha = digest(marker)
    archive_info = ROOT / "upgrade-backup.json"

    with subprocess.Popen(["runuser", "-u", "postgres", "--", python, "-u", "-c", PG_ADMIN],
                          stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True) as admin:
        cluster = admin.stdout.readline().strip()
        if not cluster.isdecimal():
            raise RuntimeError("数据库集群身份读取失败")
        backup_config.write_text(json.dumps({
            "connection": {"host": "127.0.0.1", "port": 5432, "user": "sjerp_a_migrate",
                           "dbname": "sjerp_a", "passfile": str(CONFIG / "migration.pgpass"), "sslmode": "disable"},
            "pg_bin": "/usr/lib/postgresql/17/bin", "expected_database": "sjerp_a",
            "expected_system_identifier": cluster, "app_sha": SOURCE,
            "media_root": str(MEDIA), "destination_directory": str(archive_dir),
            "encryption": {"key_file": str(key), "executable": "/usr/bin/gpg"},
        }))
        common = [ROOT, TARGET, "--instance", "a", "--database", "sjerp_a",
                  "--system-identifier", cluster, "--maintenance-role", "sjerp_a_migrate", "--media", MEDIA]
        run("systemctl", "stop", UNIT)
        run("mount", "-o", "remount,ro", MEDIA)
        try:
            admin.stdin.write("FENCE\n")
            admin.stdin.flush()
            if admin.stdout.readline().strip() != "FENCED":
                raise RuntimeError("数据库登录隔离未确认")
            run(python, seed / "upgrade-pilot-release.py", "backup", *common,
                "--checkout", checkout, "--backup-config", backup_config, env=env)
            record = json.loads(archive_info.read_text())
            (exercise / "verified-backup.json").write_text(json.dumps(record))
        finally:
            admin.stdin.close()
            try:
                if admin.wait(timeout=30):
                    raise RuntimeError("数据库登录隔离清理失败")
            finally:
                run("mount", "-o", "remount,rw", MEDIA)
    run(python, seed / "upgrade-pilot-release.py", "activate", *common, "--migration-env", migration_env, env=env)
    if (ROOT / "current").resolve(strict=True) != target or digest(marker) != marker_sha:
        raise RuntimeError("目标版本或原媒体复核失败")
    run("curl", "-fsS", "--cacert", "/etc/sjerp-a-test-ca.crt",
        "https://localhost:18443/api/session/csrf/", stdout=subprocess.DEVNULL)
    report("SJERP TEST UPGRADE READY: encrypted backup, version switch and HTTPS verified")


if __name__ == "__main__":
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("seed", type=Path)
    args = parser.parse_args()
    try:
        main(args.seed)
    except BaseException:
        if os.geteuid() == 0 and socket.gethostname().split(".")[0] == "sjerp-image-test":
            report("SJERP TEST UPGRADE FAILED: see sjerp-test-upgrade.service journal")
        raise
