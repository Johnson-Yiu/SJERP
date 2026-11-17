"""Generate a NoCloud seed ISO for a disposable ALEX image boot test."""
import argparse
from io import BytesIO
import json
from pathlib import Path
import re
import uuid

import pycdlib


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("public_key", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    key = args.public_key.read_text(encoding="ascii").strip()
    if not re.fullmatch(r"ssh-ed25519 [A-Za-z0-9+/]+=*(?: [^\r\n]+)?", key):
        parser.error("expected exactly one Ed25519 SSH public key")
    config = {
        "users": [{
            "name": "erpverify",
            "shell": "/bin/bash",
            "lock_passwd": True,
            "ssh_authorized_keys": [key],
        }],
        "ssh_pwauth": False,
        "disable_root": True,
        "package_update": False,
        "package_upgrade": False,
    }
    files = {
        "meta-data": f"instance-id: sjerp-image-test-{uuid.uuid4()}\nlocal-hostname: sjerp-image-test\n",
        "user-data": "#cloud-config\n" + json.dumps(config) + "\n",
    }
    iso = pycdlib.PyCdlib()
    iso.new(interchange_level=3, vol_ident="CIDATA", joliet=3)
    try:
        for filename, text in files.items():
            content = text.encode("utf-8")
            iso.add_fp(BytesIO(content), len(content), iso_path=f"/{filename.upper().replace('-', '_')};1",
                       joliet_path=f"/{filename}")
        with args.output.open("xb") as handle:
            iso.write_fp(handle)
    finally:
        iso.close()
    iso.open(str(args.output))
    try:
        for filename, expected in files.items():
            extracted = BytesIO()
            iso.get_file_from_iso_fp(extracted, joliet_path=f"/{filename}")
            if extracted.getvalue() != expected.encode("utf-8"):
                raise ValueError(f"Seed verification failed: {filename}")
    finally:
        iso.close()


if __name__ == "__main__":
    main()
