"""Run and verify a fresh encrypted backup before an ERP version switch."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def release_sha(version):
    digest = (version / "READY").read_text(encoding="ascii").strip()
    sha = read_json(version / "release/RELEASE.json")["commit"]
    if not re.fullmatch(r"[a-f0-9]{64}", digest) or not re.fullmatch(r"[a-f0-9]{40}", sha):
        raise ValueError("版本暂存标记或发布提交无效")
    if version.resolve().name != sha:
        raise ValueError("版本目录与发布提交不一致")
    return sha


def run_backup(args):
    current = release_sha(args.current)
    candidate = release_sha(args.candidate)
    if current == candidate:
        raise ValueError("目标提交与当前提交相同")
    config = read_json(args.config)
    if (config["app_sha"], config["expected_database"], str(config["expected_system_identifier"])) != (
        current, args.database, args.system_identifier
    ):
        raise ValueError("备份配置与当前发布、数据库或集群标识不匹配")
    if Path(config["media_root"]).resolve(strict=True) != args.media.resolve(strict=True):
        raise ValueError("备份媒体目录与当前实例不匹配")
    if not config.get("encryption") or not config.get("destination_directory") or config.get("destination"):
        raise ValueError("升级前须使用独立归档目录生成新的加密备份")
    destination = Path(config["destination_directory"]).resolve(strict=True)
    result = subprocess.run(
        [sys.executable, args.checkout.resolve(strict=True) / "backend/operations_backup.py",
         "backup", "--config", args.config.resolve(strict=True)],
        cwd=args.checkout, check=True, stdout=subprocess.PIPE, text=True,
    )
    receipt = json.loads(result.stdout)
    if receipt["status"] != "VERIFIED" or receipt.get("encryption_roundtrip_verified") is not True:
        raise ValueError("联合备份未返回加密回读通过结果")
    archive = Path(receipt["archive"])
    if (archive.is_symlink() or archive.resolve(strict=True).parent != destination
            or not re.fullmatch(r"backup-[a-f0-9]{32}\.gpg", archive.name)):
        raise ValueError("归档路径与本次备份配置不匹配")
    with archive.open("rb") as handle:
        digest = hashlib.file_digest(handle, "sha256").hexdigest()
    if digest != receipt["sha256"] or not re.fullmatch(r"[a-f0-9]{64}", receipt["plaintext_sha256"]):
        raise ValueError("发布后的归档摘要不匹配")
    print(json.dumps({
        "status": "VERIFIED", "from": current, "to": candidate,
        "database": args.database, "system_identifier": args.system_identifier,
        "archive": str(archive), "sha256": digest, "plaintext_sha256": receipt["plaintext_sha256"],
    }))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("current", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("checkout", type=Path)
    parser.add_argument("config", type=Path)
    parser.add_argument("--database", required=True)
    parser.add_argument("--system-identifier", required=True)
    parser.add_argument("--media", type=Path, required=True)
    run_backup(parser.parse_args())
