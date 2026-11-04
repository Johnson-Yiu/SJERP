"""PostgreSQL and private-media backup for *owned, isolated drills only*.

This is deliberately not a production backup command.  It creates its own
source and target databases in a task-owned local temporary cluster and keeps
all media writers behind one in-process gate.  The SQLite backup entry point
and its PostgreSQL refusal remain unchanged.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import uuid
import zipfile
from pathlib import Path
from urllib.parse import quote

import psycopg
from django import get_version as django_version
from psycopg import sql

from .backup_recovery import (
    BackupRecoveryError,
    _archive_directory,
    _copy_media_snapshot,
    _extract_archive,
    _isoformat,
    _json_bytes,
    _safe_member_path,
    _sha256,
    assert_secure_backup_file,
)
from .private_media import build_private_media_manifest, compare_private_media_manifest


class IsolatedPostgresDrill:
    """Own newly created databases and media inside a disposable local cluster.

    The caller must have created the cluster under a new task-specific temp
    directory.  This object creates its own random source database and is the
    only supported owner of the synthetic media writers.  It cannot target an
    existing database or a production/staging server.
    """

    def __init__(self, *, task_root, pg_bin, port, user, password, app_sha):
        root = Path(task_root).resolve(strict=True)
        temp_root = Path(tempfile.gettempdir()).resolve(strict=True)
        if root.parent != temp_root or not root.name.startswith("sunjack-iss018-pg17-"):
            raise BackupRecoveryError("Drill root must be a task-specific direct child of the temporary directory")
        if not isinstance(app_sha, str) or not re.fullmatch(r"[0-9a-f]{40}", app_sha):
            raise BackupRecoveryError("A full application commit SHA is required")
        self.root = root
        self.pg_bin = Path(pg_bin).resolve(strict=True)
        if self.pg_bin != root / "pgsql" / "bin":
            raise BackupRecoveryError("PostgreSQL tools must be inside the task-owned root")
        self.port = int(port)
        if self.port < 1024 or self.port == 5432:
            raise BackupRecoveryError("A dedicated non-default local port is required")
        self.user = user
        self._password = password
        self.app_sha = app_sha
        self._assert_application()
        self._media_gate = threading.Lock()
        self._owned_targets = set()
        self.source = "iss018_src_" + uuid.uuid4().hex[:16]
        self.media = root / ("media-source-" + uuid.uuid4().hex)
        self.media.mkdir(mode=0o700)
        self._assert_cluster()
        self._versions()
        with self._connect("postgres", autocommit=True) as connection:
            connection.execute(sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(sql.Identifier(self.source)))

    def _assert_application(self):
        repo = Path(__file__).resolve().parents[3]
        actual = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all", "--", "backend", "templates"],
                               cwd=repo, capture_output=True, text=True, check=True).stdout
        if actual != self.app_sha or dirty:
            raise BackupRecoveryError("Application SHA must match a clean backend and templates checkout")

    def _connect(self, database, **kwargs):
        return psycopg.connect(host="127.0.0.1", port=self.port, user=self.user,
                               password=self._password, dbname=database, **kwargs)

    def _assert_cluster(self):
        with self._connect("postgres", autocommit=True) as connection:
            row = connection.execute(
                "SELECT current_setting('data_directory'), host(inet_server_addr()), "
                "inet_server_port(), current_setting('server_version_num')::integer"
            ).fetchone()
        if Path(row[0]).resolve() != self.root / "cluster-host" or row[1] != "127.0.0.1" or row[2] != self.port:
            raise BackupRecoveryError("Database is not the task-owned local temporary cluster")
        if row[3] // 10000 != 17:
            raise BackupRecoveryError("The isolated drill requires PostgreSQL 17")
        return row[3]

    def _tool(self, name):
        path = self.pg_bin / (name + (".exe" if os.name == "nt" else ""))
        if not path.is_file():
            raise BackupRecoveryError(f"Required PostgreSQL tool is unavailable: {name}")
        return str(path)

    def _run(self, name, *arguments):
        env = os.environ.copy()
        env.update(PGHOST="127.0.0.1", PGPORT=str(self.port), PGUSER=self.user,
                   PGPASSWORD=self._password, PGCONNECT_TIMEOUT="5")
        result = subprocess.run([self._tool(name), *map(str, arguments)], env=env,
                                capture_output=True, text=True, encoding="utf-8", errors="replace")
        if result.returncode:
            detail = (result.stderr or result.stdout).replace(self._password, "[REDACTED]")
            raise BackupRecoveryError(f"{name} failed ({result.returncode}): {detail.strip()}")
        return result.stdout.strip()

    def _versions(self):
        server = self._assert_cluster()
        versions = {name: self._run(name, "--version") for name in ("pg_dump", "pg_restore")}
        for name, value in versions.items():
            match = re.search(r"\b(\d+)\.\d+", value)
            if not match or int(match.group(1)) != server // 10000:
                raise BackupRecoveryError(f"{name} version does not match PostgreSQL server major version")
        return {"server_version_num": server, "django": django_version(), **versions}

    def _environment(self, database, media):
        if database != self.source and database not in self._owned_targets:
            raise BackupRecoveryError("Django may only use a database created by this drill")
        media = Path(media).resolve(strict=True)
        if media.parent != self.root:
            raise BackupRecoveryError("Django media root must belong to this drill")
        env = os.environ.copy()
        env.update(APP_STAGE="development", DJANGO_DEBUG="false", DJANGO_ALLOWED_HOSTS="localhost,127.0.0.1,testserver", DEVELOPMENT_SUPERADMIN="false",
                   RBAC_ENFORCEMENT="true", AUDIT_LOG_ENABLED="true", MEDIA_ROOT=str(media),
                   DATABASE_URL=f"postgresql://{quote(self.user, safe='')}:{quote(self._password, safe='')}@127.0.0.1:{self.port}/{database}")
        return env

    def _manage_database(self, database, media, *arguments):
        """Run a Django command against an owned database, credentials in env only."""
        backend = Path(__file__).resolve().parents[2]
        env = self._environment(database, media)
        result = subprocess.run([sys.executable, str(backend / "manage.py"), *arguments], cwd=backend,
                                env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if result.returncode:
            detail = (result.stderr or result.stdout).replace(self._password, "[REDACTED]")
            detail = detail.replace(quote(self._password, safe=""), "[REDACTED]")
            raise BackupRecoveryError(f"Django {' '.join(arguments)} failed ({result.returncode}): {detail.strip()}")
        return result.stdout

    def _manage(self, *arguments):
        return self._manage_database(self.source, self.media, *arguments)

    def media_write(self, relative, content):
        """The only media writer used by this isolated drill's fixture."""
        relative = _safe_member_path(relative)
        with self._media_gate:
            target = self.media.joinpath(*relative.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            return target

    def _migration_rows(self, connection):
        return [list(row) for row in connection.execute(
            "SELECT app, name FROM django_migrations ORDER BY app, name"
        ).fetchall()]

    def backup(self, *, probe=None):
        """Hold DB table locks and the owned media gate during the snapshot.

        ``probe`` is used only by the drill to verify the controlled DB and
        media writers cannot pass their gates.  An arbitrary --quiesced flag
        is never accepted as evidence of the consistency window.
        """
        self._assert_cluster()
        self._assert_application()
        versions = self._versions()
        self._manage("migrate", "--check")
        started = _isoformat()
        destination = self.root / ("iss018-pg-" + uuid.uuid4().hex + ".zip")
        with self._media_gate, self._connect(self.source, autocommit=True) as connection:
            active = connection.execute(
                "SELECT pid FROM pg_stat_activity WHERE datname = current_database() AND pid <> pg_backend_pid()"
            ).fetchall()
            if active:
                raise BackupRecoveryError("Source has uncontrolled database sessions; refusing backup")
            tables = connection.execute(
                "SELECT n.nspname, c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
                "WHERE n.nspname='public' AND c.relkind IN ('r','p') ORDER BY 1,2"
            ).fetchall()
            if not tables:
                raise BackupRecoveryError("Source database has no migrated application tables")
            connection.execute("BEGIN ISOLATION LEVEL REPEATABLE READ")
            for schema, table in tables:
                connection.execute(sql.SQL("LOCK TABLE {}.{} IN SHARE MODE").format(
                    sql.Identifier(schema), sql.Identifier(table)))
            snapshot = connection.execute("SELECT pg_export_snapshot()").fetchone()[0]
            migrations = self._migration_rows(connection)
            before = build_private_media_manifest(self.media)
            if probe is not None:
                probe(self)
            with tempfile.TemporaryDirectory(prefix="iss018-pg-stage-", dir=self.root) as temporary:
                stage = Path(temporary)
                dump = stage / "database.dump"
                self._run("pg_dump", "--format=custom", "--no-owner", "--no-acl",
                          "--snapshot", snapshot, "--file", dump, "--dbname", self.source)
                (stage / "media").mkdir()
                _copy_media_snapshot(self.media, stage / "media", before)
                after = build_private_media_manifest(self.media)
                if before != after:
                    raise BackupRecoveryError("Media changed during the isolated consistency window")
                manifest = {
                    "schema_version": 1, "kind": "isolated-postgresql-drill", "app_sha": self.app_sha,
                    "started_at": started, "finished_at": _isoformat(), "versions": versions,
                    "consistency": "exported-postgresql-snapshot-table-locks-and-owned-media-gate",
                    "source_database": self.source, "database_sha256": _sha256(dump),
                    "migrations": migrations, "media": before,
                }
                (stage / "manifest.json").write_bytes(_json_bytes(manifest))
                _archive_directory(stage, destination)
        return {"archive": str(destination), "sha256": _sha256(destination), "manifest": manifest}

    def restore(self, *, archive, expected_sha256, current_app_sha):
        """Restore only to a newly created database and new owned media path."""
        self._assert_cluster()
        self._assert_application()
        versions = self._versions()
        archive = Path(archive)
        if archive.is_symlink() or not archive.is_file() or archive.resolve().parent != self.root:
            raise BackupRecoveryError("Archive must be a regular file inside the task-owned root")
        assert_secure_backup_file(archive)
        if not isinstance(expected_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_sha256) or _sha256(archive) != expected_sha256:
            raise BackupRecoveryError("Archive SHA256 mismatch")
        target = "iss018_dst_" + uuid.uuid4().hex[:16]
        media_target = self.root / ("media-restored-" + uuid.uuid4().hex)
        created = False
        try:
            with tempfile.TemporaryDirectory(prefix="iss018-pg-restore-", dir=self.root) as temporary:
                stage = Path(temporary)
                with zipfile.ZipFile(archive) as bundle:
                    names = bundle.namelist()
                    if len(names) != len(set(names)) or bundle.testzip() is not None:
                        raise BackupRecoveryError("Archive has duplicate or corrupt members")
                    for name in names:
                        _safe_member_path(name)
                _extract_archive(archive, stage)
                (stage / "media").mkdir(exist_ok=True)
                manifest = json.loads((stage / "manifest.json").read_text(encoding="utf-8"))
                if (manifest.get("kind") != "isolated-postgresql-drill" or
                        manifest.get("schema_version") != 1 or
                        manifest.get("source_database") != self.source or
                        manifest.get("app_sha") != current_app_sha or current_app_sha != self.app_sha or
                        manifest.get("versions", {}).get("server_version_num", 0) // 10000 != versions["server_version_num"] // 10000):
                    raise BackupRecoveryError("Archive source, application or PostgreSQL version mismatch")
                dump = stage / "database.dump"
                if _sha256(dump) != manifest.get("database_sha256"):
                    raise BackupRecoveryError("Database dump SHA256 mismatch")
                differences = compare_private_media_manifest(manifest.get("media", {}), stage / "media")
                if differences:
                    raise BackupRecoveryError("Media manifest mismatch: " + "; ".join(differences))
                with self._connect("postgres", autocommit=True) as connection:
                    connection.execute(sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(sql.Identifier(target)))
                created = True
                self._owned_targets.add(target)
                self._run("pg_restore", "--exit-on-error", "--single-transaction", "--no-owner", "--no-acl",
                          "--dbname", target, dump)
                with self._connect(target) as connection:
                    if self._migration_rows(connection) != manifest.get("migrations"):
                        raise BackupRecoveryError("Restored migration state differs from archive")
                if media_target.exists():
                    raise BackupRecoveryError("Restore media target already exists")
                os.replace(stage / "media", media_target)
            return {"database": target, "media": str(media_target), "manifest": manifest}
        except Exception as original:
            if created and target in self._owned_targets:
                try:
                    with self._connect("postgres", autocommit=True) as connection:
                        connection.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(target)))
                    self._owned_targets.remove(target)
                except Exception as cleanup_error:
                    raise BackupRecoveryError(
                        f"Restore failed: {original}; cleanup failed for owned database {target}: {cleanup_error}"
                    ) from original
            raise
