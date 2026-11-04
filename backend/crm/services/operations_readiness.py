"""Read-only configuration checks; this module never performs a backup.

Passing these checks is not proof that every database and filesystem writer is
stopped. In particular, it must not be used as a quiescence authorization.
"""

from pathlib import Path
import os
import shutil
from urllib.parse import urlsplit


def inspect_config(config):
    errors, warnings = [], []
    allowed = {"public_origin", "media_root", "static_root", "backup_root", "min_free_bytes", "min_free_inodes"}
    if not isinstance(config, dict) or set(config) - allowed:
        return {"ok": False, "errors": ["配置包含未知字段或不是对象"], "warnings": [], "backup_authorized": False}
    origin = config.get("public_origin", "")
    try:
        parsed = urlsplit(origin)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.path not in ("", "/") or parsed.query or parsed.fragment:
            errors.append("公开地址必须是无凭据的 HTTPS origin")
    except (TypeError, ValueError):
        errors.append("公开地址必须是无凭据的 HTTPS origin")

    paths = {}
    for key in ("media_root", "static_root", "backup_root"):
        value = config.get(key)
        if not isinstance(value, str) or not value or not Path(value).is_absolute():
            errors.append(f"{key} 必须是已存在的绝对目录")
            continue
        try:
            candidate = Path(value)
            if candidate.is_symlink() or not candidate.is_dir():
                raise ValueError()
            # Reject symlinks in any existing parent, not just the final name.
            if any(p.is_symlink() for p in (candidate, *candidate.parents)):
                raise ValueError()
            paths[key] = candidate.resolve(strict=True)
        except (OSError, ValueError, RuntimeError):
            errors.append(f"{key} 不是安全的现有目录")
    for left, right in (("media_root", "static_root"), ("media_root", "backup_root"), ("static_root", "backup_root")):
        if left in paths and right in paths and (paths[left] == paths[right] or paths[left] in paths[right].parents or paths[right] in paths[left].parents):
            errors.append(f"{left} 与 {right} 不得重叠")
    for key in ("min_free_bytes", "min_free_inodes"):
        value = config.get(key, 0)
        if type(value) is not int or value < 0:
            errors.append(f"{key} 必须为非负整数")
    if "backup_root" in paths and type(config.get("min_free_bytes", 0)) is int and config.get("min_free_bytes", 0) >= 0:
        try:
            if shutil.disk_usage(paths["backup_root"]).free < config.get("min_free_bytes", 0):
                errors.append("备份目录剩余空间不足")
        except OSError:
            errors.append("无法核对备份目录剩余空间")
    if "backup_root" in paths and type(config.get("min_free_inodes", 0)) is int and config.get("min_free_inodes", 0) > 0:
        if not hasattr(os, "statvfs"):
            errors.append("本平台无法核对 inode 余量")
        else:
            try:
                if os.statvfs(paths["backup_root"]).f_favail < config["min_free_inodes"]:
                    errors.append("备份目录 inode 余量不足")
            except OSError:
                errors.append("无法核对备份目录 inode 余量")
    warnings.append("检查不证明数据库、媒体或所有写入者处于同一一致性快照；不得据此执行联合备份")
    return {"ok": not errors, "errors": errors, "warnings": warnings, "backup_authorized": False}
