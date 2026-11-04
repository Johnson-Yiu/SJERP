"""Explicit maintenance-window PostgreSQL/private-media backup primitives.

Requires OS-enforced read-only media and a dedicated maintenance DB login.
Does not stop services, revoke roles, or accept a quiesced boolean as evidence.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import uuid
import zipfile
import shutil
import re
import stat
from contextlib import contextmanager

import psycopg
from psycopg import sql

from .operations_copy import digest
from .operations_fence import verify_readonly_filesystem
from .private_media import build_private_media_manifest, compare_private_media_manifest
from .backup_recovery import _copy_media_snapshot, _extract_archive, _safe_member_path


@contextmanager
def publish_archive(destination):
    """Only publish the final name after all nested verification/DB exits succeed."""
    destination = Path(destination)
    partial = destination.parent / (".sunjack-" + uuid.uuid4().hex + ".partial")
    fd = os.open(partial, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    identity = os.fstat(fd)
    original = None
    published = False
    try:
        with os.fdopen(fd, "wb") as output:
            output.staging_cleanup_warning = None
            yield output
            output.flush()
            os.fsync(output.fileno())
        info = partial.lstat()
        if (info.st_dev, info.st_ino) != (identity.st_dev, identity.st_ino):
            raise RuntimeError("Backup staging path identity changed")
        # Same-filesystem hard link gives exclusive publication, never replace.
        os.link(partial, destination, follow_symlinks=False)
        published_info = destination.lstat()
        if (published_info.st_dev, published_info.st_ino) != (identity.st_dev, identity.st_ino):
            raise RuntimeError("Published backup identity changed")
        published = True
    except Exception as error:
        original = error
        raise
    finally:
        try:
            current = partial.lstat()
            if (current.st_dev, current.st_ino) != (identity.st_dev, identity.st_ino):
                raise RuntimeError("Refusing to remove a replaced staging path")
            partial.unlink()
        except FileNotFoundError:
            pass
        except OSError as cleanup_error:
            if published and original is None:
                output.staging_cleanup_warning = type(cleanup_error).__name__
            elif original is None:
                raise
            else:
                original.add_note("Partial archive cleanup failed: " + type(cleanup_error).__name__)
        except RuntimeError as cleanup_error:
            if original is None:
                raise
            original.add_note(str(cleanup_error))


def verify_media_references(connection, media):
    files = {entry["path"]: entry for entry in media["files"]}
    paths = set(files)
    checked = 0
    for table, column in (("crm_followupattachment", "file"), ("crm_sku", "image"),
                          ("crm_productcertificate", "file"), ("crm_quoteitem", "image_snapshot")):
        rows = connection.execute(sql.SQL("SELECT {} FROM {} WHERE {} IS NOT NULL AND {} <> ''").format(
            sql.Identifier(column), sql.Identifier(table), sql.Identifier(column), sql.Identifier(column)))
        for (relative,) in rows:
            if relative not in paths:
                raise RuntimeError("Database references a missing private media file")
            checked += 1
    # New account and bank proofs are private media too. A file existing under
    # the same path is insufficient when its registered bytes have changed.
    for relative, size, sha256 in connection.execute(
            "SELECT file, size, sha256 FROM crm_financevoucher"):
        entry = files.get(relative)
        if entry is None:
            raise RuntimeError("Database references a missing private finance voucher")
        if entry["size"] != size or entry["sha256"] != sha256:
            raise RuntimeError("Private finance voucher metadata differs from media bytes")
        checked += 1
    return checked


def database_state(connection):
    result = {}
    tables = connection.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename").fetchall()
    for (name,) in tables:
        hasher = hashlib.sha256()
        count = 0
        with connection.cursor() as cursor:
            cursor.execute(sql.SQL("SELECT row_to_json(t)::text FROM {} t ORDER BY 1").format(sql.Identifier(name)))
            for (row,) in cursor:
                encoded = row.encode("utf-8")
                hasher.update(len(encoded).to_bytes(8, "big"))
                hasher.update(encoded)
                count += 1
        result[name] = {"rows": count, "sha256": hasher.hexdigest()}
    sequences = {}
    for (name,) in connection.execute("SELECT sequencename FROM pg_sequences WHERE schemaname='public' ORDER BY sequencename"):
        sequences[name] = list(connection.execute(sql.SQL("SELECT last_value, is_called FROM {}").format(sql.Identifier(name))).fetchone())
    return {"tables": result, "sequences": sequences}


class MaintenanceBackup:
    def __init__(self, *, connection_options, pg_bin, expected_database, expected_system_identifier, app_sha):
        if len(app_sha) != 40 or any(c not in "0123456789abcdef" for c in app_sha):
            raise ValueError("A complete application SHA is required")
        self.options = dict(connection_options)
        if not all(self.options.get(key) for key in ("host", "port", "user", "dbname")):
            raise ValueError("Explicit PostgreSQL host, port, user and database required")
        if self.options["dbname"] != expected_database:
            raise ValueError("Database connection and expected identity differ")
        self.pg_bin = Path(pg_bin)
        self.database = expected_database
        self.system_identifier = str(expected_system_identifier)
        self.app_sha = app_sha

    def connect(self):
        return psycopg.connect(**self.options)

    def application_identity(self):
        repository = Path(__file__).resolve().parents[3]
        actual = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repository,
                                capture_output=True, text=True, check=True, timeout=15).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all", "--", "backend", "templates"],
                               cwd=repository, capture_output=True, text=True, check=True, timeout=15).stdout
        if actual != self.app_sha or dirty:
            raise RuntimeError("Reviewed application SHA and clean backend/templates checkout required")

    def identity(self, connection):
        row = connection.execute("SELECT current_database(), system_identifier::text, current_setting('server_version_num')::int FROM pg_control_system()").fetchone()
        if row[0] != self.database or row[1] != self.system_identifier or row[2] // 10000 != 17:
            raise RuntimeError("PostgreSQL target identity or version mismatch")
        return row

    def writer_gate(self, connection):
        self.identity(connection)
        # Fail closed even for monitoring/administration logins. Maintenance
        # requires a single trusted login; all application roles are NOLOGIN.
        if connection.execute("SELECT rolname FROM pg_roles WHERE rolcanlogin AND rolname <> current_user").fetchone():
            raise RuntimeError("Other database login roles remain enabled")
        if connection.execute("SELECT pid FROM pg_stat_activity WHERE datname=current_database() AND pid<>pg_backend_pid()").fetchone():
            raise RuntimeError("Other source database sessions remain active")
        if connection.execute("SELECT gid FROM pg_prepared_xacts WHERE database=current_database()").fetchone():
            raise RuntimeError("Prepared transactions remain unresolved")

    def tool(self, name, *args):
        executable = self.pg_bin / (name + (".exe" if os.name == "nt" else ""))
        if not executable.is_absolute() or not executable.is_file():
            raise ValueError("Explicit PostgreSQL tools are required")
        environment = os.environ.copy()
        for variable in ("PGHOSTADDR", "PGSERVICE", "PGSERVICEFILE", "PGOPTIONS", "PGPASSWORD", "PGPASSFILE", "PGSSLMODE", "PGSSLROOTCERT"):
            environment.pop(variable, None)
        for option, variable in (("host", "PGHOST"), ("port", "PGPORT"), ("user", "PGUSER"), ("password", "PGPASSWORD"), ("passfile", "PGPASSFILE"), ("sslmode", "PGSSLMODE"), ("sslrootcert", "PGSSLROOTCERT")):
            if option in self.options:
                environment[variable] = str(self.options[option])
        environment["PGCONNECT_TIMEOUT"] = "10"
        result = subprocess.run([str(executable), *map(str, args)], env=environment,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=600)
        if result.returncode:
            raise RuntimeError(name + " failed; credential-bearing diagnostics withheld")
        return result.stdout

    def backup(self, *, media_root, destination):
        media_root, destination = Path(media_root), Path(destination)
        fence = verify_readonly_filesystem(media_root)
        self.application_identity()
        for name in ("pg_dump", "pg_restore"):
            if not re.search(rb"\b17\.\d+", self.tool(name, "--version")):
                raise RuntimeError("PostgreSQL tools must match server major 17")
        if destination.exists() or destination.is_symlink():
            raise FileExistsError("Backup destination already exists")
        with publish_archive(destination) as output, self.connect() as connection, tempfile.TemporaryDirectory(prefix="sunjack-backup-stage-") as staging:
            self.writer_gate(connection)
            connection.execute("SET LOCAL lock_timeout='5s'")
            tables = connection.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename").fetchall()
            if not tables or ("django_migrations",) not in tables:
                raise RuntimeError("Migrated application database required")
            for (name,) in tables:
                connection.execute(sql.SQL("LOCK TABLE {} IN SHARE MODE").format(sql.Identifier(name)))
            snapshot = connection.execute("SELECT pg_export_snapshot()").fetchone()[0]
            state = database_state(connection)
            media = build_private_media_manifest(media_root)
            references = verify_media_references(connection, media)
            applied = {row[0] for row in connection.execute("SELECT name FROM django_migrations WHERE app='crm'")}
            expected = {file.stem for file in (Path(__file__).resolve().parents[1] / "migrations").glob("[0-9]*.py")}
            if not expected.issubset(applied):
                raise RuntimeError("Required application migrations are not complete")
            stage = Path(staging)
            self.tool("pg_dump", "--format=custom", "--no-owner", "--no-acl", "--snapshot", snapshot,
                      "--file", stage / "database.dump", "--dbname", self.database)
            (stage / "media").mkdir()
            _copy_media_snapshot(media_root, stage / "media", media)
            if verify_readonly_filesystem(media_root) != fence or compare_private_media_manifest(media, media_root):
                raise RuntimeError("Media fence or contents changed")
            if database_state(connection) != state:
                raise RuntimeError("Database state changed during backup")
            self.writer_gate(connection)
            manifest = {"kind": "sunjack-maintenance-backup", "version": 1, "app_sha": self.app_sha,
                        "postgres_major": 17, "system_identifier": self.system_identifier,
                        "database": self.database, "database_sha256": digest(stage / "database.dump"),
                        "state": state, "media": media, "media_fence": fence, "media_references": references,
                        "migrations": sorted(applied)}
            (stage / "manifest.json").write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
            with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for file in sorted(stage.rglob("*")):
                    if file.is_file():
                        archive.write(file, file.relative_to(stage).as_posix())
        return {"sha256": digest(destination), "manifest": manifest,
                "staging_cleanup_warning": output.staging_cleanup_warning}

    def restore(self, *, archive, expected_sha256, media_parent):
        """Restore into a newly generated database and exclusively new media.

        No overwrite option exists. Only names generated by this call are
        cleanup candidates. Target cluster identity is verified before DDL.
        """
        archive, media_parent = Path(archive), Path(media_parent)
        if not re.fullmatch(r"[0-9a-f]{64}", expected_sha256) or archive.is_symlink() or not archive.is_file() or digest(archive) != expected_sha256:
            raise ValueError("Archive identity or digest mismatch")
        if media_parent.is_symlink() or not media_parent.is_dir():
            raise ValueError("An existing private restore parent is required")
        target = "sunjack_restore_" + uuid.uuid4().hex
        media = media_parent / target
        database_created = media_created = False
        with tempfile.TemporaryDirectory(prefix="sunjack-restore-stage-") as staging:
            stage = Path(staging)
            with zipfile.ZipFile(archive) as bundle:
                names = bundle.namelist()
                if len(names) != len(set(names)):
                    raise ValueError("Invalid archive members")
                if sum(member.file_size for member in bundle.infolist()) > shutil.disk_usage(stage).free // 2:
                    raise ValueError("Insufficient safe extraction capacity")
                for member in bundle.infolist():
                    if stat.S_ISLNK(member.external_attr >> 16) or member.flag_bits & 1:
                        raise ValueError("Archive links and encrypted ZIP members are unsupported")
                if bundle.testzip() is not None:
                    raise ValueError("Invalid archive checksum")
                for name in names:
                    _safe_member_path(name)
                    if name not in ("manifest.json", "database.dump") and not name.startswith("media/"):
                        raise ValueError("Unexpected archive member")
                # Extraction also enforces safe paths and forbids archive links.
                _extract_archive(archive, stage)
            manifest = json.loads((stage / "manifest.json").read_text(encoding="utf-8"))
            if manifest.get("kind") != "sunjack-maintenance-backup" or manifest.get("version") != 1 or manifest.get("app_sha") != self.app_sha or manifest.get("postgres_major") != 17:
                raise ValueError("Archive application or format is incompatible")
            self.application_identity()
            if digest(stage / "database.dump") != manifest["database_sha256"] or compare_private_media_manifest(manifest["media"], stage / "media"):
                raise ValueError("Archive database or media integrity failed")
            try:
                with self.connect() as admin:
                    self.identity(admin)
                    admin.commit()
                    admin.autocommit = True
                    admin.execute(sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(sql.Identifier(target)))
                    database_created = True
                self.tool("pg_restore", "--exit-on-error", "--single-transaction", "--no-owner", "--no-acl", "--dbname", target, stage / "database.dump")
                options = {**self.options, "dbname": target}
                with psycopg.connect(**options) as restored:
                    if database_state(restored) != manifest["state"]:
                        raise RuntimeError("Restored rows, amounts, relations or sequences differ")
                    if verify_media_references(restored, manifest["media"]) != manifest["media_references"]:
                        raise RuntimeError("Restored attachment references differ")
                    for table in ("crm_csvimportbatch", "crm_csvimportrowaudit", "crm_csvimportpreviewaudit"):
                        restored.execute("SAVEPOINT audit_probe")
                        try:
                            restored.execute(sql.SQL("TRUNCATE TABLE {} CASCADE").format(sql.Identifier(table)))
                        except psycopg.Error as error:
                            if "append-only" not in str(error).lower():
                                raise RuntimeError("Audit rejection was not the append-only guard") from None
                        else:
                            raise RuntimeError("Restored audit trigger did not reject TRUNCATE")
                        finally:
                            restored.execute("ROLLBACK TO SAVEPOINT audit_probe")
                    rejected_mutations = 0
                    for table in ("crm_operationlog", "crm_csvimportbatch", "crm_csvimportrowaudit", "crm_csvimportpreviewaudit"):
                        row = restored.execute(sql.SQL("SELECT id FROM {} LIMIT 1").format(sql.Identifier(table))).fetchone()
                        if row is None:
                            continue
                        for statement in (sql.SQL("UPDATE {} SET id=id WHERE id=%s"), sql.SQL("DELETE FROM {} WHERE id=%s")):
                            restored.execute("SAVEPOINT audit_row_probe")
                            try:
                                restored.execute(statement.format(sql.Identifier(table)), (row[0],))
                            except psycopg.Error as error:
                                if "append-only" not in str(error).lower():
                                    raise RuntimeError("Audit row rejection was not append-only protection") from None
                                rejected_mutations += 1
                            else:
                                raise RuntimeError("Restored audit row mutation was accepted")
                            finally:
                                restored.execute("ROLLBACK TO SAVEPOINT audit_row_probe")
                    if database_state(restored) != manifest["state"]:
                        raise RuntimeError("Audit probes changed restored data")
                media.mkdir(mode=0o700)
                media_created = True
                shutil.copytree(stage / "media", media, dirs_exist_ok=True)
                if compare_private_media_manifest(manifest["media"], media):
                    raise RuntimeError("Restored media integrity failed")
                return {"database": target, "media_root": str(media), "verified": True,
                        "audit_truncate_rejected": True, "audit_row_mutations_rejected": rejected_mutations}
            except Exception as original:
                if database_created:
                    try:
                        with self.connect() as admin:
                            self.identity(admin)
                            admin.commit()
                            admin.autocommit = True
                            admin.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(target)))
                    except Exception as error:
                        original.add_note("Owned restore database cleanup failed: " + type(error).__name__)
                if media_created:
                    try:
                        shutil.rmtree(media)
                    except OSError as error:
                        original.add_note("Owned restore media cleanup failed: " + type(error).__name__)
                raise
