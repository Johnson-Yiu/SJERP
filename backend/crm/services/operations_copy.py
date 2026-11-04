"""Verified, exclusive backup copies. No deletion and no implicit success marker."""

import hashlib
import os
from pathlib import Path
import re


def digest(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def verified_copy(source, destination, expected_sha256):
    """Copy only to a new explicit destination, verify both sides, never overwrite.

    A successful same-host copy does not establish independent failure domains.
    Caller must supply a trusted digest; this cannot validate snapshot consistency.
    On failure only the destination inode created by this call may be removed.
    """
    if not isinstance(expected_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_sha256):
        raise ValueError("A complete trusted SHA-256 is required")
    source, destination = Path(source), Path(destination)
    for candidate in (source, destination.parent):
        if any(p.is_symlink() or (hasattr(p, "is_junction") and p.is_junction()) for p in (candidate, *candidate.parents)):
            raise ValueError("Linked paths are not permitted")
    if not source.is_file() or not destination.parent.is_dir():
        raise ValueError("A regular source and existing destination directory are required")
    if digest(source) != expected_sha256:
        raise ValueError("Source digest mismatch")
    identity = None
    try:
        fd = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        identity = os.fstat(fd)
        with os.fdopen(fd, "wb") as output, source.open("rb") as input_stream:
            for chunk in iter(lambda: input_stream.read(1024 * 1024), b""):
                output.write(chunk)
            output.flush()
            os.fsync(output.fileno())
        if digest(destination) != expected_sha256 or digest(source) != expected_sha256:
            raise ValueError("Copy or source changed; digest mismatch")
        return {"sha256": expected_sha256, "bytes": destination.stat().st_size,
                "independent_failure_domain_verified": False}
    except Exception as original:
        if identity is not None:
            try:
                current = destination.lstat()
                if (current.st_dev, current.st_ino) == (identity.st_dev, identity.st_ino):
                    destination.unlink()
                else:
                    original.add_note("Cleanup refused: destination identity changed")
            except FileNotFoundError:
                pass
            except OSError as cleanup_error:
                original.add_note("Copy cleanup failed: " + type(cleanup_error).__name__)
        raise
