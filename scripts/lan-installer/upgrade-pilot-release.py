"""Switch a staged ERP release after a fresh maintenance backup."""
import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time


CHECK_DATABASE = r"""
import os
from django.db import connections
connection = connections['default']
connection.ensure_connection()
with connection.cursor() as cursor:
    cursor.execute(
        "SELECT current_database(), current_user, system_identifier::text, "
        "current_setting('server_version_num')::int FROM pg_control_system()"
    )
    row = cursor.fetchone()
expected = (os.environ['SJERP_UPGRADE_DB'], os.environ['SJERP_UPGRADE_ROLE'],
            os.environ['SJERP_UPGRADE_CLUSTER'])
if row[:3] != expected or row[3] // 10000 != 17:
    raise SystemExit('迁移连接的数据库、角色或集群与预期不符')
"""


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def run(*command, **kwargs):
    return subprocess.run(command, check=True, text=True, **kwargs)


@contextmanager
def locked(root):
    with (root / ".upgrade.lock").open("a") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def write_new(path, data):
    with path.open("x", encoding="utf-8") as handle:
        json.dump(data, handle)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def verify_version(path):
    commit = path.name
    if not re.fullmatch(r"[a-f0-9]{40}", commit) or path.is_symlink():
        raise ValueError("版本目录无效")
    if load(path / "release/RELEASE.json")["commit"] != commit:
        raise ValueError("版本目录与发布清单不符")
    if not re.fullmatch(r"[a-f0-9]{64}", (path / "READY").read_text().strip()):
        raise ValueError("版本尚未暂存完成")


def upgrade(args):
    root = args.root.resolve(strict=True)
    current_link = root / "current"
    versions = root / "versions"
    state = root / "upgrade-in-progress.json"
    pending = root / "upgrade-backup.json"
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", args.instance):
        raise ValueError("实例名无效")
    if not re.fullmatch(r"[a-f0-9]{40}", args.commit) or not current_link.is_symlink():
        raise ValueError("目标提交无效或实例缺少 current 链接")
    if not args.maintenance_role or not args.database or not args.system_identifier.isdecimal() or not args.media:
        raise ValueError("迁移数据库、角色和集群身份必须明确")
    media = args.media.resolve(strict=True)
    unit = f"sjerp-local@{args.instance}.service"
    # Only the same stable current link should be referenced by the unit and Nginx.
    with locked(root):
        if state.exists():
            raise RuntimeError("存在未完成的升级，请依照备份恢复流程处理")
        current = current_link.resolve(strict=True)
        candidate = versions / args.commit
        if current.parent != versions or current == candidate:
            raise ValueError("当前版本与目标版本无效或相同")
        verify_version(current)
        verify_version(candidate)
        service_state = run("systemctl", "show", "--property=ActiveState", "--value",
                            unit, capture_output=True).stdout.strip()
        if service_state != "inactive":
            raise RuntimeError("先进入维护窗口并停止对应 ERP 服务")
        expected = {"from": current.name, "to": candidate.name, "database": args.database,
                    "system_identifier": args.system_identifier}
        if args.action == "backup":
            if pending.exists():
                raise RuntimeError("已有待用备份记录，请先核对现有维护窗口")
            if not all((args.checkout, args.backup_config, args.media)):
                raise ValueError("备份需要维护检出、备份配置及媒体目录")
            result = run(
                current / "venv/bin/python", Path(__file__).with_name("backup-before-upgrade.py"),
                current, candidate, args.checkout, args.backup_config,
                "--database", args.database, "--system-identifier", args.system_identifier,
                "--media", args.media, capture_output=True,
            )
            receipt = json.loads(result.stdout)
            if receipt["status"] != "VERIFIED" or any(receipt[key] != value for key, value in expected.items()):
                raise ValueError("备份回执与当前升级不匹配")
            write_new(pending, {**receipt, "created_at": time.time(), "instance": args.instance, "media": str(media)})
            print(f"联合备份已核对：{receipt['archive']}")
            return

        if not args.migration_env:
            raise ValueError("激活需要独立迁移环境配置")
        receipt = load(pending)
        if (receipt["status"] != "VERIFIED" or receipt["instance"] != args.instance
                or receipt["media"] != str(media)
                or not 0 <= time.time() - receipt["created_at"] <= 3600
                or any(receipt[key] != value for key, value in expected.items())):
            raise ValueError("备份回执与当前升级不匹配或超过一小时")
        archive = Path(receipt["archive"])
        if archive.is_symlink() or digest(archive) != receipt["sha256"]:
            raise ValueError("备份归档摘要校验失败")

        values = load(args.migration_env)
        if not isinstance(values, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in values.items()):
            raise ValueError("迁移环境必须是字符串键值的 JSON 对象")
        allowed = {"APP_STAGE", "DJANGO_ALLOWED_HOSTS", "DJANGO_SECRET_KEY",
                   "DATABASE_URL", "PGPASSFILE", "MEDIA_ROOT"}
        if values.keys() != allowed or values["APP_STAGE"] not in {"staging", "production"}:
            raise ValueError("迁移环境字段不完整或运行阶段无效")
        if Path(values["MEDIA_ROOT"]).resolve(strict=True) != media:
            raise ValueError("迁移媒体目录与备份不一致")
        if os.statvfs(media).f_flag & os.ST_RDONLY:
            raise ValueError("媒体卷仍为只读，请先完成备份后维护切换")
        env = {"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", **values,
               "SJERP_UPGRADE_DB": args.database, "SJERP_UPGRADE_ROLE": args.maintenance_role,
               "SJERP_UPGRADE_CLUSTER": args.system_identifier}
        manage = candidate / "release/backend/manage.py"
        python = candidate / "venv/bin/python"
        run(python, manage, "shell", "-c", CHECK_DATABASE, cwd=manage.parent, env=env)
        run(python, manage, "migrate", "--plan", cwd=manage.parent, env=env)
        write_new(state, receipt)
        try:
            run(python, manage, "migrate", "--noinput", cwd=manage.parent, env=env)
            with tempfile.TemporaryDirectory(prefix=".sjerp-switch-", dir=root) as folder:
                replacement = Path(folder) / "current"
                replacement.symlink_to(candidate, target_is_directory=True)
                os.replace(replacement, current_link)
            run("systemctl", "start", unit)
            run("systemctl", "is-active", "--quiet", unit)
        except BaseException:
            subprocess.run(("systemctl", "stop", unit), check=False)
            raise
        # Acknowledge only after systemd's start-pre and HTTP readiness checks pass.
        pending.unlink()
        state.unlink()
        print(f"升级完成：{current.name} → {candidate.name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("backup", "activate"))
    parser.add_argument("root", type=Path)
    parser.add_argument("commit")
    parser.add_argument("--instance", required=True)
    parser.add_argument("--database", required=True)
    parser.add_argument("--system-identifier", required=True)
    parser.add_argument("--maintenance-role", required=True)
    parser.add_argument("--checkout", type=Path)
    parser.add_argument("--backup-config", type=Path)
    parser.add_argument("--media", type=Path)
    parser.add_argument("--migration-env", type=Path)
    upgrade(parser.parse_args())
