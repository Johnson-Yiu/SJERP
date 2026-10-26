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
            except (OSError, ValueError) as exc:
                raise PrivateMediaStorageError(f"File escapes private media root: {candidate}") from exc
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


def build_private_media_manifest(root=None):
    """Return a deterministic manifest without exposing an absolute root path."""
    media_root = _media_root(root)
    files = []
    for path in _iter_files(media_root):
        relative_path = path.relative_to(media_root).as_posix()
        size = path.stat().st_size
        files.append({"path": relative_path, "size": size, "sha256": _sha256(path)})
    return {
        "schema_version": 1,
        "storage_backend": "filesystem",
        "root": "MEDIA_ROOT",
        "algorithm": "sha256",
        "file_count": len(files),
        "total_bytes": sum(item["size"] for item in files),
        "files": files,
        "manifest_sha256": _files_digest(files),
    }


def compare_private_media_manifest(manifest, root=None):
    """Return restore mismatches; an empty list means the media tree matches."""
    actual = build_private_media_manifest(root)
    differences = []
    expected_files = manifest.get("files")
    if not isinstance(expected_files, list):
        return ["manifest files must be a list"]
    if manifest.get("manifest_sha256") != _files_digest(expected_files):
        differences.append("manifest_sha256 does not match its file list")

    expected_by_path = {item.get("path"): item for item in expected_files if isinstance(item, dict)}
    actual_by_path = {item["path"]: item for item in actual["files"]}
    for path in sorted(set(expected_by_path) - set(actual_by_path)):
        differences.append(f"missing: {path}")
    for path in sorted(set(actual_by_path) - set(expected_by_path)):
        differences.append(f"unexpected: {path}")
    for path in sorted(set(expected_by_path) & set(actual_by_path)):
        if expected_by_path[path] != actual_by_path[path]:
            differences.append(f"changed: {path}")
    if manifest.get("file_count") != actual["file_count"]:
        differences.append("file_count differs")
    if manifest.get("total_bytes") != actual["total_bytes"]:
        differences.append("total_bytes differs")
    return differences
