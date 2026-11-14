"""Build or verify an SJERP LAN pilot release directory."""

import argparse
from hashlib import file_digest
from io import BytesIO
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from tempfile import TemporaryDirectory
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = "RELEASE.json"
OPERATIONS = (
    "archive", "backup", "copy", "local_environment", "monitor",
    "preflight", "runtime_http",
)
BACKEND = {
    "backend/manage.py", "backend/requirements.txt", "backend/requirements.lock",
    *(f"backend/operations_{name}.py" for name in OPERATIONS),
}
FRONTEND_BUILD = {
    "frontend/index.html", "frontend/package.json", "frontend/package-lock.json",
    "frontend/vite.config.js",
}


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def build_input(path):
    return (
        path in FRONTEND_BUILD
        or path.startswith(("frontend/src/", "frontend/public/"))
    )


def runtime_input(path):
    parts = path.split("/")
    if any(part.startswith(".") for part in parts):
        return False
    if path.startswith("docs/deployment/"):
        return path.endswith((".md", ".example", ".example.json", ".txt"))
    if path.startswith("templates/"):
        return path.endswith((".xlsx", ".html", ".png", ".jpg", ".jpeg", ".svg", ".woff2"))
    if path.startswith(("backend/config/", "backend/crm/")):
        return (
            "tests" not in parts
            and Path(path).name not in {"seed_demo.py", "postgres_test_cleanup.py"}
            and path.endswith((".py", ".html", ".xlsx", ".png", ".jpg", ".jpeg", ".svg", ".woff2"))
        )
    return path in BACKEND


def file_records(directory):
    records = {}
    for file in sorted(directory.rglob("*")):
        if file.is_symlink() or (os.name == "nt" and file.is_junction()):
            raise ValueError(f"Unexpected link in release: {file}")
        if file.is_file() and file != directory / MANIFEST:
            with file.open("rb") as handle:
                records[file.relative_to(directory).as_posix()] = {
                    "bytes": file.stat().st_size,
                    "sha256": file_digest(handle, "sha256").hexdigest(),
                }
    return records


def verify(directory):
    manifest = json.loads((directory / MANIFEST).read_text(encoding="utf-8"))
    if manifest["files"] != file_records(directory):
        raise ValueError("Release file list or SHA-256 digest differs from the manifest.")
    print(f'{manifest["commit"]}: {len(manifest["files"])} files verified')


def build(commit, output, offline):
    if (
        not re.fullmatch(r"[0-9a-f]{40}", commit)
        or git("rev-parse", commit + "^{commit}").decode().strip() != commit
    ):
        raise ValueError("Provide the full lowercase commit SHA.")
    if output.exists() or output.is_symlink():
        raise ValueError("Output directory must be new.")
    tracked = git("ls-tree", "-rz", "--name-only", commit).decode("utf-8").split("\0")
    paths = [path for path in tracked if runtime_input(path) or build_input(path)]
    if not (BACKEND | FRONTEND_BUILD).issubset(paths):
        raise ValueError("Required runtime or build files are missing from the commit.")
    source_paths = ["backend", "frontend/src", *sorted(FRONTEND_BUILD), "docs/deployment", "templates"]
    if any(path.startswith("frontend/public/") for path in paths):
        source_paths.append("frontend/public")
    archive = git("archive", "--format=zip", commit, "--", *source_paths)
    with TemporaryDirectory(prefix=".sjerp-release-", dir=output.parent) as temporary:
        stage = Path(temporary)
        source = stage / "source"
        release = stage / "release"
        with ZipFile(BytesIO(archive)) as zipped:
            for path in paths:
                if zipped.getinfo(path).external_attr >> 28 == 10:
                    raise ValueError(f"Unexpected link in Git tree: {path}")
                zipped.extract(path, source if build_input(path) else release)

        npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
        if not npm:
            raise ValueError("npm is required on the build machine.")
        env = {name: value for name, value in os.environ.items() if not name.startswith("VITE_")}
        frontend = source / "frontend"
        install = [npm, "ci", "--include=dev", "--no-audit", "--no-fund"]
        if offline:
            install.append("--offline")
        subprocess.run(install, cwd=frontend, env=env, check=True)
        subprocess.run([npm, "run", "build"], cwd=frontend, env=env, check=True)
        dist = frontend / "dist"
        if not (dist / "index.html").is_file():
            raise ValueError("Production build did not produce an index.")
        shutil.copytree(dist, release / "frontend/dist")
        for name in ("package.json", "package-lock.json"):
            shutil.copy2(frontend / name, release / "frontend" / name)
        manifest = {
            "commit": commit,
            "node": subprocess.check_output(["node", "--version"], text=True).strip(),
            "npm": subprocess.check_output([npm, "--version"], text=True).strip(),
            "files": file_records(release),
        }
        (release / MANIFEST).write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
        )
        output.mkdir()
        for entry in sorted(release.iterdir(), key=lambda item: item.name == MANIFEST):
            entry.rename(output / entry.name)
    verify(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build_command = commands.add_parser("build")
    build_command.add_argument("commit")
    build_command.add_argument("directory", type=Path)
    build_command.add_argument("--offline", action="store_true", help="Use the existing npm cache.")
    verify_command = commands.add_parser("verify")
    verify_command.add_argument("directory", type=Path)
    args = parser.parse_args()
    if args.command == "verify":
        verify(args.directory)
    else:
        build(args.commit, args.directory.absolute(), args.offline)


if __name__ == "__main__":
    main()
