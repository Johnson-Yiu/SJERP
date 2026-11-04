"""Load a root-controlled receipt trust anchor; never trust a caller's pin."""
import json
import os
from pathlib import Path
import stat


def _root_controlled_file(path):
    path = Path(path)
    if not path.is_absolute():
        raise ValueError("Absolute trust path required")
    for component in (path, *path.parents):
        info = component.lstat()
        if stat.S_ISLNK(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
            raise ValueError("Trust anchor and all parent directories must be root-owned and not writable by others")
    if not path.is_file():
        raise ValueError("Trust path must be a regular file")
    return path


def load_receipt_trust(path):
    """Require immutable-to-operator Linux trust configuration and key paths."""
    if os.name != "posix" or not Path("/proc/self/mountinfo").is_file():
        raise RuntimeError("Independent trust-anchor ownership is not verified on this platform")
    if os.geteuid() == 0:
        raise RuntimeError("Retention and monitoring must run as a non-root account")
    path = _root_controlled_file(path)
    with path.open("rb") as stream:
        raw = stream.read(65537)
    if len(raw) > 65536:
        raise ValueError("Trust anchor is too large")
    value = json.loads(raw)
    if not isinstance(value, dict) or set(value) != {"executable", "public_key", "pinned_fingerprint", "max_age_seconds"}:
        raise ValueError("Invalid trust anchor configuration")
    _root_controlled_file(value["public_key"])
    _root_controlled_file(value["executable"])
    return value
