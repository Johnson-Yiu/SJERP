"""Filesystem media inventory used by the ISS-018 backup/restore handoff.

This module deliberately does not serve files or expose an HTTP endpoint.  It
provides a deterministic, path-relative SHA256 manifest for the initial
single-server storage layout.  Django's storage abstraction remains the write
and read boundary so a later object-storage migration does not change CRM
model paths.
"""

import hashlib
import json
import os
from pathlib import Path
from pathlib import PurePosixPath

from django.conf import settings


class PrivateMediaStorageError(RuntimeError):
    """Raised when the private media root cannot be inventoried safely."""


def _media_root(root=None):
    path = Path(root) if root is not None else Path(settings.MEDIA_ROOT)
    path = path.resolve()
    if not path.exists():
        raise PrivateMediaStorageError(f"Private media root does not exist: {path}")
    if not path.is_dir():
        raise PrivateMediaStorageError(f"Private media root is not a directory: {path}")
    return path


def _iter_files(root):
    root = root.resolve()
    for current, directories, filenames in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        directories[:] = sorted(directories)
        filenames = sorted(filenames)
        for directory in directories:
            candidate = current_path / directory
            if candidate.is_symlink():
                raise PrivateMediaStorageError(f"Symlink directory is not allowed in private media: {candidate}")
        for filename in filenames:
            candidate = current_path / filename
            if candidate.is_symlink():
                raise PrivateMediaStorageError(f"Symlink file is not allowed in private media: {candidate}")
            try:
                candidate.resolve(strict=True).relative_to(root)
                if not candidate.is_file():
                    raise PrivateMediaStorageError(f"Non-regular file is not allowed in private media: {candidate}")
            except (OSError, ValueError) as exc:
                raise PrivateMediaStorageError(f"File escapes private media root: {candidate}") from exc
            yield candidate


def _iter_directories(root):
    root = root.resolve()
    for current, directories, _ in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        directories[:] = sorted(directories)
        for directory in directories:
            candidate = current_path / directory
            if candidate.is_symlink():
                raise PrivateMediaStorageError(f"Symlink directory is not allowed in private media: {candidate}")
            try:
                candidate.resolve(strict=True).relative_to(root)
            except (OSError, ValueError) as exc:
                raise PrivateMediaStorageError(f"Directory escapes private media root: {candidate}") from exc
            yield candidate


def _sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _files_digest(files):
    canonical = json.dumps(files, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _inventory_digest(files, directories):
    canonical = json.dumps(
        {"directories": directories, "files": files},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _safe_manifest_path(value):
    if not isinstance(value, str) or not value or "\\" in value:
        return False
    path = PurePosixPath(value)
    return (
        not path.is_absolute()
        and bool(path.parts)
        and path.as_posix() == value
        and all(part not in {"", ".", ".."} and ":" not in part for part in path.parts)
    )


def build_private_media_manifest(root=None):
    """Return a deterministic manifest without exposing an absolute root path."""
    media_root = _media_root(root)
    directories = sorted(path.relative_to(media_root).as_posix() for path in _iter_directories(media_root))
    files = []
    for path in _iter_files(media_root):
        relative_path = path.relative_to(media_root).as_posix()
        if not _safe_manifest_path(relative_path):
            raise PrivateMediaStorageError(f"Unsupported path in private media: {relative_path}")
        size = path.stat().st_size
        files.append({"path": relative_path, "size": size, "sha256": _sha256(path)})
    if any(not _safe_manifest_path(path) for path in directories):
        raise PrivateMediaStorageError("Unsupported directory path in private media")
    return {
        "schema_version": 2,
        "storage_backend": "filesystem",
        "root": "MEDIA_ROOT",
        "algorithm": "sha256",
        "directory_count": len(directories),
        "directories": directories,
        "file_count": len(files),
        "total_bytes": sum(item["size"] for item in files),
        "files": files,
        "manifest_sha256": _inventory_digest(files, directories),
    }


def compare_private_media_manifest(manifest, root=None):
    """Return restore mismatches; an empty list means the media tree matches."""
    if not isinstance(manifest, dict):
        return ["manifest must be an object"]
    schema_version = manifest.get("schema_version", 1)
    if schema_version not in {1, 2}:
        return ["unsupported manifest schema version"]
    actual = build_private_media_manifest(root)
    differences = []
    expected_files = manifest.get("files")
    if not isinstance(expected_files, list):
        return ["manifest files must be a list"]
    legacy_manifest = schema_version == 1 and "directories" not in manifest
    expected_directories = manifest.get("directories", [])
    if schema_version == 2 and "directories" not in manifest:
        return ["manifest directories must be a list"]
    if not isinstance(expected_directories, list):
        return ["manifest directories must be a list"]
    if any(not _safe_manifest_path(path) for path in expected_directories):
        return ["manifest contains an unsafe directory path"]
    if len(expected_directories) != len(set(expected_directories)):
        return ["manifest contains duplicate directory paths"]
    if any(not isinstance(entry, dict) or not _safe_manifest_path(entry.get("path")) for entry in expected_files):
        return ["manifest contains an unsafe file path"]
    expected_file_paths = [entry["path"] for entry in expected_files]
    if len(expected_file_paths) != len(set(expected_file_paths)):
        return ["manifest contains duplicate file paths"]
    expected_digest = _files_digest(expected_files) if legacy_manifest else _inventory_digest(expected_files, expected_directories)
    if manifest.get("manifest_sha256") != expected_digest:
        differences.append("manifest_sha256 does not match the media inventory")

    expected_by_path = {item.get("path"): item for item in expected_files if isinstance(item, dict)}
    actual_by_path = {item["path"]: item for item in actual["files"]}
    for path in sorted(set(expected_by_path) - set(actual_by_path)):
        differences.append(f"missing: {path}")
    for path in sorted(set(actual_by_path) - set(expected_by_path)):
        differences.append(f"unexpected: {path}")
    for path in sorted(set(expected_by_path) & set(actual_by_path)):
        if expected_by_path[path] != actual_by_path[path]:
            differences.append(f"changed: {path}")
    if not legacy_manifest:
        actual_directories = actual["directories"]
        for path in sorted(set(expected_directories) - set(actual_directories)):
            differences.append(f"missing directory: {path}")
        for path in sorted(set(actual_directories) - set(expected_directories)):
            differences.append(f"unexpected directory: {path}")
        if manifest.get("directory_count") != actual["directory_count"]:
            differences.append("directory_count differs")
    if manifest.get("file_count") != actual["file_count"]:
        differences.append("file_count differs")
    if manifest.get("total_bytes") != actual["total_bytes"]:
        differences.append("total_bytes differs")
    return differences


def secure_private_media_tree(root):
    """Apply owner-only POSIX modes to a restored private media tree.

    Windows access control lists cannot be safely set with chmod; deployment
    tooling must provision and verify those ACLs separately.
    """
    path = Path(root)
    if path.is_symlink() or not path.exists() or not path.is_dir():
        raise PrivateMediaStorageError("Restored private media root is missing or invalid")
    resolved_root = path.resolve()
    directories = [resolved_root]
    files = []
    for current, child_directories, filenames in os.walk(resolved_root, topdown=True, followlinks=False):
        current_path = Path(current)
        child_directories[:] = sorted(child_directories)
        for name in child_directories:
            candidate = current_path / name
            if candidate.is_symlink():
                raise PrivateMediaStorageError("Restored private media contains a symlink directory")
            candidate.resolve(strict=True).relative_to(resolved_root)
            directories.append(candidate)
        for name in filenames:
            candidate = current_path / name
            if candidate.is_symlink() or not candidate.is_file():
                raise PrivateMediaStorageError("Restored private media contains an unsupported file")
            candidate.resolve(strict=True).relative_to(resolved_root)
            files.append(candidate)
    if os.name != "nt":
        for directory in directories:
            directory.chmod(0o700)
        for file_path in files:
            file_path.chmod(0o600)
    return {"directories": len(directories), "files": len(files), "windows_acl_pending": os.name == "nt"}
