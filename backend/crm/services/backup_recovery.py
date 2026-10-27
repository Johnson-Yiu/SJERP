"""Consistent database/private-media backup and isolated restore primitives.

The first deployment target is a single server with a local filesystem media
volume.  A database dump and an independently copied media directory are not
an application-consistent backup by themselves.  This module therefore uses a
strict, explicit contract:

* the caller must quiesce ERP writes before starting the operation;
* the SQLite snapshot and media tree are written into one archive;
* the media manifest is checked before and after the copy; and
* restore verifies the archive, database integrity and every media SHA256
  before writing a new isolated target directory.

PostgreSQL production backups intentionally are not implemented as a guessed
``pg_dump + cp`` combination.  The deployment runbook must bind a PostgreSQL
exported snapshot to a filesystem snapshot or a documented write-quiescence
window before this operation can be marked production-ready.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import sqlite3
import subprocess
import tempfile
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from django.conf import settings

from .private_media import (
    PrivateMediaStorageError,
    build_private_media_manifest,
    compare_private_media_manifest,
)


ARCHIVE_SCHEMA_VERSION = 1
DATABASE_MEMBER = "database.sqlite3"
MEDIA_DIRECTORY = "media"
CONFIG_MEMBER = "recovery-config.json"
MANIFEST_MEMBER = "manifest.json"
BACKUP_FILENAME_PREFIX = "erp-backup-"
BACKUP_FILENAME_RE = re.compile(r"^erp-backup-[A-Za-z0-9][A-Za-z0-9._-]*\.zip$")


class BackupRecoveryError(RuntimeError):
    """Raised when a backup or restore cannot satisfy the safety contract."""


def _windows_acl_required():
    return os.name == "nt" and getattr(settings, "APP_STAGE", "development") in {"staging", "production"}


def ensure_secure_backup_directory(directory, *, tighten=False, require_windows_acl=None):
    """Create/check a backup directory without claiming Windows ACL isolation.

    POSIX backup directories are owner-only (0700).  Existing directories with
    group/other bits are rejected unless the caller explicitly opts into the
    documented 0700 tightening.  On Windows, chmod is deliberately not used
    as an ACL proof; deployed stages fail closed until NTFS ACLs are provisioned
    and checked outside the application.
    """
    path = Path(directory).expanduser()
    if path.exists() and path.is_symlink():
        raise BackupRecoveryError(f"Backup directory must not be a symlink: {path}")
    if require_windows_acl is None:
        require_windows_acl = _windows_acl_required()
    if os.name == "nt" and require_windows_acl:
        raise BackupRecoveryError(
            "Windows production backup storage requires a pre-provisioned NTFS ACL; "
            "the application will not create or chmod an unverified directory."
        )
    created = False
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
        created = True
    if not path.is_dir():
        raise BackupRecoveryError(f"Backup path is not a directory: {path}")
    if os.name == "nt":
        return {"path": str(path.resolve()), "platform": "windows", "status": "WINDOWS_ACL_PENDING", "created": created}
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode & 0o077:
        if not tighten:
            raise BackupRecoveryError(
                f"Backup directory is accessible to group/other users: {path} mode={mode:04o}; "
                "refuse writing or pass --tighten-permissions after reviewing ownership."
            )
        os.chmod(path, 0o700)
    else:
        os.chmod(path, 0o700)
    return {"path": str(path.resolve()), "platform": "posix", "status": "PASS", "created": created, "mode": "0700"}


def secure_backup_file(path, *, require_windows_acl=None):
    """Apply owner-only file mode on POSIX; never present Windows chmod as ACL proof."""
    path = Path(path).expanduser()
    if path.is_symlink():
        raise BackupRecoveryError(f"Backup file must not be a symlink: {path}")
    if not path.is_file():
        raise BackupRecoveryError(f"Backup file does not exist: {path}")
    if require_windows_acl is None:
        require_windows_acl = _windows_acl_required()
    if os.name == "nt":
        if require_windows_acl:
            raise BackupRecoveryError(
                "Windows production backup files require verified NTFS ACLs; chmod is not sufficient."
            )
        return {"path": str(path.resolve()), "platform": "windows", "status": "WINDOWS_ACL_PENDING"}
    os.chmod(path, 0o600)
    return {"path": str(path.resolve()), "platform": "posix", "status": "PASS", "mode": "0600"}


def assert_secure_backup_file(path, *, require_windows_acl=None):
    """Reject an input archive whose local permissions expose its contents."""
    path = Path(path).expanduser()
    if path.is_symlink() or not path.is_file():
        raise BackupRecoveryError(f"Backup archive is not a regular file: {path}")
    if require_windows_acl is None:
        require_windows_acl = _windows_acl_required()
    if os.name == "nt":
        if require_windows_acl:
            raise BackupRecoveryError(
                "Windows production backup archives require verified NTFS ACLs; chmod is not sufficient."
            )
        return {"path": str(path.resolve()), "platform": "windows", "status": "WINDOWS_ACL_PENDING"}
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode & 0o077:
        raise BackupRecoveryError(f"Backup archive is accessible to group/other users: {path} mode={mode:04o}")
    return {"path": str(path.resolve()), "platform": "posix", "status": "PASS", "mode": f"{mode:04o}"}


def _secure_tree(root, *, require_windows_acl=None):
    root = Path(root)
    if not root.is_dir() or root.is_symlink():
        raise BackupRecoveryError(f"Restore staging directory is invalid: {root}")
    paths = [root, *sorted(root.rglob("*"))]
    for path in paths:
        if path.is_symlink():
            raise BackupRecoveryError(f"Restore archive contains a symlink: {path.relative_to(root)}")
        if path.is_dir():
            ensure_secure_backup_directory(path, tighten=True, require_windows_acl=require_windows_acl)
        elif path.is_file():
            secure_backup_file(path, require_windows_acl=require_windows_acl)
        else:
            raise BackupRecoveryError(f"Restore staging contains unsupported filesystem entry: {path}")


def _write_structured_result(path, result, *, require_windows_acl=None):
    """Write a report atomically with owner-only file permissions on POSIX."""
    path = Path(path).expanduser()
    if path.is_symlink():
        raise BackupRecoveryError(f"Structured result path must not be a symlink: {path}")
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".partial", dir=path.parent)
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        secure_backup_file(temporary, require_windows_acl=require_windows_acl)
        temporary.write_bytes(_json_bytes(result))
        secure_backup_file(temporary, require_windows_acl=require_windows_acl)
        os.replace(temporary, path)
        secure_backup_file(path, require_windows_acl=require_windows_acl)
    finally:
        if temporary.exists():
            temporary.unlink()


def _default_restore_result_path(target):
    target = Path(target)
    return target.parent / f".{target.name}.restore-result.json"


def _validate_restore_result_path(result_file, target_dir):
    """Reject report paths that can write into the recovery target.

    Check the user-supplied path for a symlink before resolving it.  The
    resolved comparison then catches lexical variants and symlinked parent
    directories that point inside the target.
    """
    result_path = Path(result_file).expanduser()
    target_path = Path(target_dir).expanduser()
    if result_path.is_symlink():
        raise BackupRecoveryError(f"Structured result path must not be a symlink: {result_path}")
    if target_path.is_symlink():
        raise BackupRecoveryError(f"Restore target must not be a symlink: {target_path}")
    resolved_target = target_path.resolve()
    resolved_result = result_path.resolve()
    if resolved_result == resolved_target or resolved_target in resolved_result.parents:
        raise BackupRecoveryError("result_file must be outside target_dir")
    return result_path


def _utc_now():
    return datetime.now(timezone.utc)


def _isoformat(value=None):
    return (value or _utc_now()).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _json_bytes(payload):
    return (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_member_path(name):
    """Return a safe relative POSIX member path, or raise on traversal."""
    if not isinstance(name, str) or not name or "\\" in name:
        raise BackupRecoveryError(f"Unsafe archive member: {name!r}")
    path = PurePosixPath(name)
    if path.is_absolute() or any(part in {"", ".", ".."} or ":" in part for part in path.parts):
        raise BackupRecoveryError(f"Unsafe archive member: {name!r}")
    return path


def _safe_backup_id(value):
    value = str(value or "").strip()
    if not value or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", value):
        raise BackupRecoveryError("backup_id must contain only letters, numbers, dot, underscore or hyphen")
    return value


def _database_path(database=None):
    value = database if database is not None else settings.DATABASES["default"]["NAME"]
    if value in {None, "", ":memory:"}:
        raise BackupRecoveryError("A file-backed SQLite database is required for an isolated backup.")
    path = Path(value).expanduser().resolve()
    if not path.exists() or not path.is_file():
        raise BackupRecoveryError(f"SQLite database does not exist: {path}")
    return path


def _assert_sqlite(database=None):
    engine = settings.DATABASES["default"].get("ENGINE", "")
    if "sqlite" not in engine.lower():
        raise BackupRecoveryError(
            "This command refuses PostgreSQL production backups without a bound database/filesystem snapshot. "
            "Use the ISS-018 deployment runbook and mark this environment DEPLOYMENT_VERIFICATION_PENDING."
        )
    return _database_path(database)


def _media_path(media_root=None):
    root = Path(media_root if media_root is not None else settings.MEDIA_ROOT).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise BackupRecoveryError(f"Private media root does not exist: {root}")
    return root


def _safe_recovery_config():
    """Return allow-listed recovery settings; never serialize secrets."""
    storage_backend = getattr(settings, "MEDIA_STORAGE_BACKEND", "django.core.files.storage.FileSystemStorage")
    return {
        "schema_version": 1,
        "database_engine": "sqlite",
        "storage_backend": str(storage_backend),
        "media_url": str(getattr(settings, "MEDIA_URL", "/media/")),
        "time_zone": str(getattr(settings, "TIME_ZONE", "UTC")),
        "media_root_placeholder": "MEDIA_ROOT",
        "secrets_included": False,
    }


def _snapshot_sqlite(source, destination):
    """Create a transaction-consistent SQLite snapshot using the backup API."""
    source = Path(source).resolve()
    destination = Path(destination).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    source_connection = sqlite3.connect(str(source), timeout=30)
    destination_connection = sqlite3.connect(str(destination))
    try:
        # The caller has already quiesced ERP writes.  A deferred read
        # transaction gives sqlite3.Connection.backup() a stable snapshot
        # without holding a writer lock that can make the backup API wait on
        # Windows SQLite builds.  The media before/after manifest check below
        # detects a violated quiescence window and discards the archive.
        source_connection.execute("BEGIN")
        source_connection.backup(destination_connection, pages=256, sleep=0.05)
        destination_connection.commit()
        source_connection.rollback()
    except Exception as exc:
        destination_connection.rollback()
        raise BackupRecoveryError(f"SQLite snapshot failed: {exc}") from exc
    finally:
        destination_connection.close()
        source_connection.close()
    check = sqlite3.connect(str(destination))
    try:
        result = check.execute("PRAGMA integrity_check").fetchone()[0]
    finally:
        check.close()
    if result != "ok":
        raise BackupRecoveryError(f"SQLite snapshot integrity check failed: {result}")


def _copy_media_snapshot(source_root, destination_root, manifest):
    source_root = Path(source_root).resolve()
    destination_root = Path(destination_root).resolve()
    for entry in manifest["files"]:
        relative = _safe_member_path(entry["path"])
        source = (source_root / Path(*relative.parts)).resolve()
        try:
            source.relative_to(source_root)
        except ValueError as exc:
            raise BackupRecoveryError(f"Media path escapes MEDIA_ROOT: {entry['path']}") from exc
        destination = destination_root.joinpath(*relative.parts)
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(source, destination)
        except OSError as exc:
            raise BackupRecoveryError(f"Media copy failed for {entry['path']}: {exc}") from exc


def _archive_directory(stage, archive_path):
    archive_path = Path(archive_path)
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{archive_path.name}.", suffix=".partial", dir=archive_path.parent)
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        secure_backup_file(temporary)
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, strict_timestamps=False) as archive:
            for path in sorted(Path(stage).rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(stage).as_posix())
        with zipfile.ZipFile(temporary) as archive:
            if archive.testzip() is not None:
                raise BackupRecoveryError("Created backup archive failed CRC verification")
        os.replace(temporary, archive_path)
        secure_backup_file(archive_path)
    finally:
        if temporary.exists():
            temporary.unlink()


def create_consistent_backup(
    *,
    database=None,
    media_root=None,
    output_dir,
    backup_id=None,
    quiesced=False,
    encrypted_output=None,
    age_recipient=None,
    status_file=None,
    tighten_permissions=False,
):
    """Create one archive containing a quiesced SQLite+private-media point."""
    started = time.monotonic()
    result = {"status": "FAILED", "started_at": _isoformat(), "errors": []}
    require_windows_acl = _windows_acl_required()
    try:
        if not quiesced:
            raise BackupRecoveryError(
                "Consistency contract not satisfied: pass --quiesced only after ERP DB and media writes are stopped."
            )
        database_path = _assert_sqlite(database)
        media_root_path = _media_path(media_root)
        destination_dir = Path(output_dir).expanduser()
        access_control = ensure_secure_backup_directory(
            destination_dir,
            tighten=tighten_permissions,
            require_windows_acl=require_windows_acl,
        )
        destination_dir = destination_dir.resolve()
        if encrypted_output and not age_recipient:
            raise BackupRecoveryError("--age-recipient is required when --encrypted-output is requested")
        if age_recipient and not encrypted_output:
            raise BackupRecoveryError("--encrypted-output is required when --age-recipient is requested")
        backup_id = _safe_backup_id(backup_id or _utc_now().strftime("%Y%m%dT%H%M%SZ"))
        archive_path = destination_dir / f"{BACKUP_FILENAME_PREFIX}{backup_id}.zip"
        if archive_path.exists():
            raise BackupRecoveryError(f"Backup archive already exists: {archive_path}")

        before_media = build_private_media_manifest(media_root_path)
        with tempfile.TemporaryDirectory(prefix=f"iss018-{backup_id}-", dir=destination_dir) as temporary_dir:
            stage = Path(temporary_dir)
            _snapshot_sqlite(database_path, stage / DATABASE_MEMBER)
            _copy_media_snapshot(media_root_path, stage / MEDIA_DIRECTORY, before_media)
            after_media = build_private_media_manifest(media_root_path)
            if before_media != after_media:
                raise BackupRecoveryError("MEDIA_ROOT changed during backup; archive discarded")

            config_bytes = _json_bytes(_safe_recovery_config())
            (stage / CONFIG_MEMBER).write_bytes(config_bytes)
            manifest = {
                "schema_version": ARCHIVE_SCHEMA_VERSION,
                "backup_id": backup_id,
                "created_at": _isoformat(),
                "consistency": {
                    "method": "application-quiesced-sqlite-backup-and-media-archive",
                    "quiesced": True,
                    "write_window": "caller-stopped-db-and-media-writes",
                },
                "source": {
                    "database_engine": "sqlite",
                    "database_path": "DATABASE_PATH_REDACTED",
                    "media_root": "MEDIA_ROOT",
                },
                "database": {"member": DATABASE_MEMBER, "sha256": _sha256(stage / DATABASE_MEMBER)},
                "media": before_media,
                "recovery_config": {"member": CONFIG_MEMBER, "sha256": hashlib.sha256(config_bytes).hexdigest()},
            }
            (stage / MANIFEST_MEMBER).write_bytes(_json_bytes(manifest))
            _secure_tree(stage, require_windows_acl=require_windows_acl)
            _archive_directory(stage, archive_path)

        result.update(
            {
                "status": "PASS",
                "backup_id": backup_id,
                "archive": str(archive_path),
                "archive_sha256": _sha256(archive_path),
                "encrypted_archive": None,
                "consistency_method": manifest["consistency"]["method"],
                "access_control": access_control,
            }
        )
        if encrypted_output:
            encrypted_path = Path(encrypted_output).expanduser().resolve()
            _encrypt_with_age(archive_path, encrypted_path, age_recipient)
            result["encrypted_archive"] = str(encrypted_path)
            result["encrypted_archive_sha256"] = _sha256(encrypted_path)
    except (BackupRecoveryError, PrivateMediaStorageError, OSError, ValueError) as exc:
        result["status"] = "FAILED"
        result["errors"].append(str(exc))
        raise
    finally:
        result["finished_at"] = _isoformat()
        result["duration_seconds"] = round(time.monotonic() - started, 3)
        if status_file:
            status_path = Path(status_file).expanduser().resolve()
            try:
                _write_structured_result(status_path, result, require_windows_acl=require_windows_acl)
            except (BackupRecoveryError, OSError) as status_error:
                if result["status"] == "PASS":
                    raise
                result["errors"].append(f"Could not write backup status: {status_error}")
    return result


def _encrypt_with_age(archive_path, encrypted_path, recipient):
    executable = shutil.which("age")
    if not executable:
        raise BackupRecoveryError("age executable is not installed; encrypted independent copy is pending")
    ensure_secure_backup_directory(encrypted_path.parent)
    command = [executable, "--encrypt", "--recipient", str(recipient), "--output", str(encrypted_path), str(archive_path)]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "age returned a non-zero exit status").strip()
        raise BackupRecoveryError(f"age encryption failed: {detail}")
    secure_backup_file(encrypted_path)


def _extract_archive(archive_path, stage):
    with zipfile.ZipFile(archive_path) as source:
        for info in source.infolist():
            relative = _safe_member_path(info.filename)
            destination = Path(stage).joinpath(*relative.parts)
            if info.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            with source.open(info, "r") as input_file, destination.open("wb") as output_file:
                shutil.copyfileobj(input_file, output_file)


def restore_consistent_backup(*, archive, target_dir, result_file=None):
    """Verify and atomically restore an archive into a new isolated directory.

    The target must not already exist.  The verified staging directory is on
    the target filesystem and is atomically renamed into place only after all
    checks pass.  The default structured report is a sibling of the target so
    a rejected target can never be changed by reporting the failure.
    """
    started = time.monotonic()
    raw_target = Path(target_dir).expanduser()
    raw_archive = Path(archive).expanduser()
    if raw_target.is_symlink():
        raise BackupRecoveryError(f"Restore target must not be a symlink: {raw_target}")
    target = raw_target.resolve()
    archive_path = raw_archive.resolve()
    output = _validate_restore_result_path(
        result_file if result_file is not None else _default_restore_result_path(target),
        raw_target,
    )
    result = {
        "status": "FAILED",
        "restore_status": "FAILED",
        "report_status": "PENDING",
        "report_file": str(output),
        "started_at": _isoformat(),
        "errors": [],
        "archive": str(archive_path),
    }
    error = None
    staging = None
    require_windows_acl = _windows_acl_required()
    try:
        if not raw_archive.is_file() or raw_archive.is_symlink():
            raise BackupRecoveryError(f"Backup archive does not exist: {archive_path}")
        assert_secure_backup_file(raw_archive, require_windows_acl=require_windows_acl)
        if raw_target.is_symlink() or target.exists():
            if target.is_symlink() or not target.is_dir():
                raise BackupRecoveryError(f"Restore target must be a new directory: {target}")
            raise BackupRecoveryError(
                f"Restore target already exists; choose a new path for atomic recovery: {target}"
            )
        target.parent.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=f".{target.name}.restore-", dir=target.parent))
        ensure_secure_backup_directory(staging, require_windows_acl=require_windows_acl)
        _extract_archive(archive_path, staging)
        manifest = json.loads((staging / MANIFEST_MEMBER).read_text(encoding="utf-8"))
        if manifest.get("schema_version") != ARCHIVE_SCHEMA_VERSION:
            raise BackupRecoveryError("Unsupported backup manifest schema")
        if manifest.get("consistency", {}).get("quiesced") is not True:
            raise BackupRecoveryError("Backup manifest does not prove a quiesced consistency point")
        database = staging / DATABASE_MEMBER
        if _sha256(database) != manifest.get("database", {}).get("sha256"):
            raise BackupRecoveryError("Restored database SHA256 does not match manifest")
        check = sqlite3.connect(str(database))
        try:
            integrity = check.execute("PRAGMA integrity_check").fetchone()[0]
        finally:
            check.close()
        if integrity != "ok":
            raise BackupRecoveryError(f"Restored database integrity check failed: {integrity}")
        media = staging / MEDIA_DIRECTORY
        differences = compare_private_media_manifest(manifest.get("media", {}), media)
        if differences:
            raise BackupRecoveryError("Restored media manifest mismatch: " + "; ".join(differences))
        config = staging / CONFIG_MEMBER
        if _sha256(config) != manifest.get("recovery_config", {}).get("sha256"):
            raise BackupRecoveryError("Recovery configuration SHA256 does not match manifest")
        _secure_tree(staging, require_windows_acl=require_windows_acl)
        if target.exists():
            raise BackupRecoveryError(f"Restore target appeared during verification: {target}")
        os.replace(staging, target)
        staging = None
        result.update(
            {
                "status": "PASS",
                "restore_status": "PASS",
                "backup_id": manifest.get("backup_id"),
                "target_dir": str(target),
                "verified_database_sha256": _sha256(target / DATABASE_MEMBER),
                "verified_media_manifest_sha256": manifest.get("media", {}).get("manifest_sha256"),
            }
        )
    except zipfile.BadZipFile as exc:
        error = BackupRecoveryError(f"Invalid backup archive: {archive_path}")
        result["errors"].append(str(error))
    except (BackupRecoveryError, OSError, ValueError, json.JSONDecodeError) as exc:
        error = exc
        result["errors"].append(str(exc))
    finally:
        if staging is not None and staging.exists():
            shutil.rmtree(staging)
    result["finished_at"] = _isoformat()
    result["duration_seconds"] = round(time.monotonic() - started, 3)
    result["report_status"] = "PASS"
    try:
        _write_structured_result(output, result, require_windows_acl=require_windows_acl)
    except (BackupRecoveryError, OSError) as report_error:
        result["report_status"] = "FAILED"
        result["report_error"] = str(report_error)
        if error is None:
            # The restore directory may already have been atomically committed.
            # Keep recovery status authoritative and surface the report failure
            # separately so callers do not retry over a successful restore.
            if result["restore_status"] != "PASS":
                error = report_error
                result["errors"].append(f"Could not write restore result: {report_error}")
    if error is not None:
        raise error
    return result


def _archive_metadata(path):
    try:
        with zipfile.ZipFile(path) as source:
            manifest = json.loads(source.read(MANIFEST_MEMBER).decode("utf-8"))
        created = datetime.fromisoformat(manifest["created_at"].replace("Z", "+00:00"))
        return manifest, created
    except (OSError, KeyError, ValueError, zipfile.BadZipFile, json.JSONDecodeError) as exc:
        raise BackupRecoveryError(f"Cannot read backup metadata: {path}") from exc


def prune_backup_archives(directory, *, apply=False, tighten_permissions=False):
    """Plan or apply the 7 daily / 4 weekly / 3 monthly retention policy."""
    root = Path(directory).expanduser()
    if root.is_symlink():
        raise BackupRecoveryError(f"Backup directory must not be a symlink: {root}")
    if not root.exists():
        raise BackupRecoveryError(f"Backup directory does not exist: {root}")
    if not root.is_dir():
        raise BackupRecoveryError(f"Backup path is not a directory: {root}")
    ensure_secure_backup_directory(root, tighten=tighten_permissions)
    root = root.resolve()
    archives = []
    for path in sorted(root.glob(f"{BACKUP_FILENAME_PREFIX}*.zip")):
        if not BACKUP_FILENAME_RE.match(path.name):
            continue
        manifest, created = _archive_metadata(path)
        archives.append({"path": path, "manifest": manifest, "created": created})
    archives.sort(key=lambda item: item["created"], reverse=True)
    keep = set()
    keep.update(item["path"] for item in archives[:7])
    weekly = {}
    for item in archives:
        key = item["created"].isocalendar()[:2]
        weekly.setdefault(key, item)
    keep.update(item["path"] for item in list(weekly.values())[:4])
    monthly = {}
    for item in archives:
        key = (item["created"].year, item["created"].month)
        monthly.setdefault(key, item)
    keep.update(item["path"] for item in list(monthly.values())[:3])
    removed = []
    for item in archives:
        if item["path"] in keep:
            continue
        removed.append(str(item["path"]))
        if apply:
            item["path"].unlink()
            encrypted = item["path"].with_suffix(item["path"].suffix + ".age")
            if encrypted.exists():
                encrypted.unlink()
    return {"status": "PASS", "apply": bool(apply), "kept": sorted(str(path) for path in keep), "removed": removed}
