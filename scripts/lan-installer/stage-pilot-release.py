"""Verify and stage an offline ERP release without activating it."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import venv
from zipfile import ZipFile


def stage(bundle: Path, expected: str, versions: Path) -> None:
    versions = versions.resolve(strict=True)
    with bundle.open("rb") as handle:
        if hashlib.file_digest(handle, "sha256").hexdigest() != expected.lower():
            raise ValueError("离线包 SHA-256 不匹配")
        handle.seek(0)
        with ZipFile(handle) as archive:
            index = json.loads(archive.read("PAYLOAD.json"))
            commit = index["commit"]
            if not re.fullmatch(r"[a-f0-9]{40}", commit):
                raise ValueError("无效的发布提交")
            files = index["files"]
            names = archive.namelist()
            if len(names) != len(files) + 1 or set(names) != files.keys() | {"PAYLOAD.json"}:
                raise ValueError("归档文件与清单不一致")
            target = versions / commit
            # A venv embeds its absolute path. Build it at its final location.
            # READY is written only after every file and dependency passes verification.
            target.mkdir(mode=0o700)
            try:
                for name, record in files.items():
                    relative = PurePosixPath(name)
                    if (relative.as_posix() != name or relative.is_absolute()
                            or ".." in relative.parts or "\\" in name
                            or relative.parts[0] not in {"release", "wheelhouse"}):
                        raise ValueError(f"无效的载荷路径：{name}")
                    content = archive.read(name)
                    if (len(content) != record["bytes"]
                            or hashlib.sha256(content).hexdigest() != record["sha256"]):
                        raise ValueError(f"载荷文件校验失败：{name}")
                    destination = target / relative
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes(content)
                release = target / "release"
                manifest = json.loads((release / "RELEASE.json").read_text(encoding="utf-8"))
                if manifest["commit"] != commit:
                    raise ValueError("应用清单提交与载荷不一致")

                venv.EnvBuilder(with_pip=True).create(target / "venv")
                python = target / "venv/bin/python"
                subprocess.run([
                    python, "-m", "pip", "--isolated", "install", "--no-index",
                    "--find-links", target / "wheelhouse",
                    "-r", release / "backend/requirements.lock",
                    "-r", release / "docs/deployment/sjerp-local-service-requirements.txt",
                ], check=True)
                subprocess.run([python, "-m", "pip", "--isolated", "check"], check=True)
                (target / "READY").write_text(expected.lower() + "\n", encoding="ascii")
            except BaseException:
                shutil.rmtree(target)
                raise
    print(f"离线版本就绪：{target}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("sha256")
    parser.add_argument("versions", type=Path)
    args = parser.parse_args()
    if sys.platform != "linux" or sys.version_info < (3, 12):
        parser.error("需要 Linux 和 Python 3.12 或更新版本")
    stage(args.bundle, args.sha256, args.versions)
