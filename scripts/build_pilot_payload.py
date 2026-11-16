"""Package a verified ERP release and its offline Python wheels."""
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from build_pilot_release import verify


def build(release: Path, wheels: Path, output: Path) -> None:
    verify(release)
    manifest = json.loads((release / "RELEASE.json").read_text(encoding="utf-8"))
    wheel_paths = sorted(wheels.iterdir())
    if not wheel_paths or any(
        not path.is_file() or path.is_symlink() or path.suffix != ".whl"
        for path in wheel_paths
    ):
        raise ValueError("Wheelhouse must contain only regular .whl files")

    payload = {
        f"release/{relative}": release / relative
        for relative in manifest["files"]
    }
    payload["release/RELEASE.json"] = release / "RELEASE.json"
    payload.update({f"wheelhouse/{path.name}": path for path in wheel_paths})
    records = {}
    with ZipFile(output, "x", compression=ZIP_DEFLATED) as archive:
        for name, path in sorted(payload.items()):
            content = path.read_bytes()
            digest = hashlib.sha256(content).hexdigest()
            if name.startswith("release/") and name != "release/RELEASE.json":
                if manifest["files"][name.removeprefix("release/")]["sha256"] != digest:
                    raise ValueError(f"Release changed during packaging: {name}")
            info = ZipInfo(name)
            info.compress_type = ZIP_DEFLATED
            archive.writestr(info, content)
            records[name] = {"bytes": len(content), "sha256": digest}
        index = {"commit": manifest["commit"], "files": records}
        archive.writestr(
            ZipInfo("PAYLOAD.json"),
            json.dumps(index, sort_keys=True, indent=2) + "\n",
        )

    with ZipFile(output) as archive:
        if archive.testzip() is not None:
            raise ValueError("ZIP verification failed")
        for name, record in records.items():
            if hashlib.sha256(archive.read(name)).hexdigest() != record["sha256"]:
                raise ValueError(f"Payload verification failed: {name}")
    with output.open("rb") as handle:
        digest = hashlib.file_digest(handle, "sha256").hexdigest()
    print(f"{manifest['commit']}: {len(records)} files; SHA-256 {digest}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("release", type=Path)
    parser.add_argument("wheels", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    build(args.release, args.wheels, args.output)
