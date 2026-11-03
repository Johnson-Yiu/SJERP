"""Disposable ISS-018 exercise only; this is NOT a production backup command."""

import argparse
import hashlib
import json
import os
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

from psycopg import sql
from crm.services.backup_recovery import _sha256
from crm.services.postgres_drill_backup import IsolatedPostgresDrill


def tool(bin_dir, name):
    return str(bin_dir / (name + (".exe" if os.name == "nt" else "")))


def run_tool(args, *, env=None):
    # A Windows server child can inherit pipes from pg_ctl and keep them open
    # after pg_ctl exits.  Discard output instead of waiting for pipe EOF.
    result = subprocess.run(args, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180)
    if result.returncode:
        # Never forward tool output: it can contain credentials or connection strings.
        raise RuntimeError(f"{Path(args[0]).name} failed (exit {result.returncode})")


def snapshot(drill, database):
    """Compare all application rows, rather than calculated summaries."""
    with drill._connect(database) as conn:
        names = conn.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename").fetchall()
        return {name: conn.execute(sql.SQL("SELECT row_to_json(t)::text FROM {} t ORDER BY 1").format(
            sql.Identifier(name))).fetchall() for (name,) in names}


def fault_archive(source, dest, fault):
    with zipfile.ZipFile(source) as original, zipfile.ZipFile(dest, "w") as modified:
        for entry in original.infolist():
            if fault == "missing-media" and entry.filename.startswith("media/") and not entry.is_dir():
                fault = "missing-media-done"
                continue
            content = original.read(entry)
            if entry.filename == "manifest.json" and fault in ("version", "tool"):
                manifest = json.loads(content)
                if fault == "version":
                    manifest["versions"]["server_version_num"] = 160000
                else:
                    manifest["database_sha256"] = hashlib.sha256(b"invalid custom dump").hexdigest()
                content = json.dumps(manifest).encode()
            if entry.filename == "database.dump" and fault == "tool":
                content = b"invalid custom dump"
            modified.writestr(entry, content)
    if os.name != "nt":
        os.chmod(dest, 0o600)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--postgres-bin", required=True, help="PostgreSQL 17 binaries, copied into a new task-owned root")
    parser.add_argument("--test-fault", choices=("checksum", "missing-media", "corrupt", "version", "tool", "environment"),
                        help="Synthetic failure injection; always returns nonzero")
    args = parser.parse_args()
    root = Path(tempfile.mkdtemp(prefix="sunjack-iss018-pg17-"))
    pg_bin = root / "pgsql" / "bin"
    cluster = root / "cluster-host"
    start_attempted = False
    source_unchanged = None
    password = None
    error = None
    result = None
    cleanup_error = None
    try:
        source_bin = Path(args.postgres_bin).resolve(strict=True)
        shutil.copytree(source_bin.parent, pg_bin.parent)
        password = secrets.token_urlsafe(32)
        secret_file = root / "secret"
        secret_file.write_text(password, encoding="ascii")
        if os.name != "nt":
            os.chmod(secret_file, 0o600)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        run_tool([tool(pg_bin, "initdb"), "-D", str(cluster), "-U", "iss018_drill_admin",
                  "--auth=scram-sha-256", "--pwfile=" + str(secret_file), "--encoding=UTF8", "--no-locale"])
        start_attempted = True
        run_tool([tool(pg_bin, "pg_ctl"), "-D", str(cluster), "-l", str(root / "postgres.log"),
                  "-o", f"-h 127.0.0.1 -p {port}", "-w", "start"])
        os.environ["ISS018_DRILL_ROOT"] = str(root)
        repo = Path(__file__).resolve().parents[1]
        sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True).stdout.strip()
        drill = IsolatedPostgresDrill(task_root=root, pg_bin=pg_bin, port=port, user="iss018_drill_admin",
                                      password=password, app_sha=sha)
        drill._manage("migrate", "--noinput", "--verbosity", "0")
        fixture = json.loads(drill._manage("shell", "--no-imports", "-c", "from crm.tests.iss018_drill_fixture import seed; seed()"))
        before = snapshot(drill, drill.source)
        backup = drill.backup()
        archive = Path(backup["archive"])
        expected = backup["sha256"]
        if args.test_fault == "checksum":
            expected = "0" * 64
        elif args.test_fault == "corrupt":
            archive.write_bytes(b"invalid archive")
            expected = _sha256(archive)
        elif args.test_fault in ("missing-media", "version", "tool"):
            altered = root / "fault.zip"
            fault_archive(archive, altered, args.test_fault)
            archive, expected = altered, _sha256(altered)
        with drill._connect("postgres") as conn:
            targets_before = set(conn.execute("SELECT datname FROM pg_database WHERE datname LIKE 'iss018_dst_%'").fetchall())
        try:
            if args.test_fault == "environment":
                drill._environment("postgres", drill.media)
            restored = drill.restore(archive=archive, expected_sha256=expected, current_app_sha=sha)
            if args.test_fault:
                raise RuntimeError("Injected fault unexpectedly succeeded")
            if snapshot(drill, restored["database"]) != before:
                raise RuntimeError("Restored business rows differ from source")
            for key in ("attachment", "image"):
                if not (Path(restored["media"]) / fixture[key]).is_file():
                    raise RuntimeError("Restored fixture media association is missing")
            result = {"status": "PASS", "versions": backup["manifest"]["versions"],
                      "source": drill.source, "target": restored["database"], "sha256": expected,
                      "table_count": len(before), "row_count": sum(map(len, before.values())),
                      "migrations": len(backup["manifest"]["migrations"]), "media": backup["manifest"]["media"]}
        except Exception as original:
            if snapshot(drill, drill.source) != before:
                raise RuntimeError(f"{original}; failure changed source data") from original
            source_unchanged = True
            with drill._connect("postgres") as conn:
                targets_after = set(conn.execute("SELECT datname FROM pg_database WHERE datname LIKE 'iss018_dst_%'").fetchall())
            if targets_after != targets_before:
                raise RuntimeError(f"{original}; failure left a restore database") from original
            if list(root.glob("media-restored-*")):
                raise RuntimeError(f"{original}; failure left restored media") from original
            raise
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        if password:
            error = error.replace(password, "[REDACTED]")
    finally:
        if start_attempted:
            try:
                status = subprocess.run([tool(pg_bin, "pg_ctl"), "-D", str(cluster), "status"],
                                        capture_output=True).returncode
                if status == 0:
                    run_tool([tool(pg_bin, "pg_ctl"), "-D", str(cluster), "-m", "fast", "-w", "stop"])
                elif status != 3 or (cluster / "postmaster.pid").exists():
                    raise RuntimeError(f"Cannot prove cluster is stopped (status {status})")
            except Exception as exc:
                cleanup_error = str(exc)
        if not cleanup_error:
            try:
                if root.parent.resolve() != Path(tempfile.gettempdir()).resolve() or not root.name.startswith("sunjack-iss018-pg17-") or root.is_symlink():
                    raise RuntimeError("Owned root validation failed")
                shutil.rmtree(root)
            except Exception as exc:
                cleanup_error = str(exc)
    if cleanup_error:
        print(json.dumps({"status": "FAILED", "error": error, "cleanup_error": cleanup_error, "leftover_root": str(root)}), file=sys.stderr)
        return 1
    if error:
        print(json.dumps({"status": "FAILED", "error": error, "source_unchanged": source_unchanged, "cleanup": "complete"}), file=sys.stderr)
        return 1
    result["cleanup"] = "complete"
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
