"""Kernel-backed offline snapshot fence. Refuse unsupported platforms.

This checks filesystem superblock read-only state, not merely a read-only bind
mount. A caller must hold this state throughout archive creation. It does not
stop services or alter mounts, and never treats a user flag as proof.
"""
import json
import os
from pathlib import Path
import subprocess


def verify_readonly_filesystem(path):
    path = Path(path)
    if os.name != "posix" or not Path("/proc/self/mountinfo").is_file():
        raise RuntimeError("Offline filesystem fence requires Linux mount evidence")
    if not path.is_absolute() or not path.is_dir():
        raise ValueError("An existing absolute snapshot root is required")
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("Snapshot roots must not contain symlinks")
    result = subprocess.run(["findmnt", "--json", "--submounts", "--target", str(path),
                             "--output", "TARGET,FSTYPE,FS-OPTIONS,VFS-OPTIONS,MAJ:MIN"],
                            capture_output=True, text=True, timeout=15, check=True)
    rows = json.loads(result.stdout).get("filesystems", [])
    if len(rows) != 1:
        raise RuntimeError("Filesystem identity could not be determined")
    return validate_mount_record(rows[0], path)


def validate_mount_record(row, path):
    """Validate findmnt metadata; this alone is not live filesystem evidence."""
    path = Path(path)
    if row.get("fstype") not in {"ext4", "xfs", "btrfs"} or row.get("children"):
        raise RuntimeError("A dedicated local filesystem without submounts is required")
    if "ro" not in row.get("fs-options", "").split(",") or "ro" not in row.get("vfs-options", "").split(","):
        raise RuntimeError("Filesystem and mount must both be read-only")
    if not row.get("maj:min") or not row.get("target"):
        raise RuntimeError("Filesystem identity is incomplete")
    return {"root": str(path.resolve()), "filesystem": row["maj:min"], "mount": row["target"]}


def verify_offline_postgres(data_root, pg_controldata):
    """Require a cleanly stopped PG17 source on a read-only filesystem.

    Tablespaces and external WAL paths require another verified volume design;
    they are deliberately refused here. No server connection is made.
    """
    root = Path(data_root)
    fence = verify_readonly_filesystem(root)
    if (root / "PG_VERSION").read_text(encoding="ascii").strip() != "17":
        raise RuntimeError("Offline source must be PostgreSQL 17")
    if (root / "postmaster.pid").exists():
        raise RuntimeError("Source contains a postmaster PID; shutdown is unproven")
    if any(p.is_symlink() for p in root.rglob("*")):
        raise RuntimeError("External PostgreSQL storage links are unsupported")
    environment = os.environ.copy()
    environment.update(LC_ALL="C", LANG="C")
    result = subprocess.run([str(pg_controldata), str(root)], env=environment,
                            capture_output=True, text=True, timeout=30, check=True)
    fields = dict(line.split(":", 1) for line in result.stdout.splitlines() if ":" in line)
    if fields.get("Database cluster state", "").strip() != "shut down":
        raise RuntimeError("PostgreSQL did not complete a clean primary shutdown")
    identity = fields.get("Database system identifier", "").strip()
    if not identity.isdecimal():
        raise RuntimeError("PostgreSQL system identity is missing")
    return {**fence, "system_identifier": identity, "major_version": 17}
