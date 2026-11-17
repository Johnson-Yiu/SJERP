"""Generate a NoCloud seed ISO for a disposable ALEX image boot test."""
import argparse
import hashlib
from io import BytesIO
import json
from contextlib import ExitStack
from pathlib import Path
import re
import shlex
import uuid

import pycdlib


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("public_key", type=Path)
    parser.add_argument("output", type=Path)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--upgrade", nargs=6, metavar="INPUT", help="rehearsal script, Git pack, target ZIP, staging script, upgrade driver, backup driver")
    modes.add_argument("--business-test", type=Path, help="isolated test account and restart check")
    modes.add_argument("--team-tls", nargs=3, metavar=("SCRIPT", "CA", "LEAF"))
    modes.add_argument("--lan-test", type=Path, help="isolated guest LAN HTTPS configuration")
    modes.add_argument("--encrypted-admin", nargs=2, metavar=("SCRIPT", "ENVELOPE"))
    modes.add_argument("--admin-console", type=Path, help="one-shot interactive administrator setup")
    modes.add_argument("--activate", type=Path, help="isolated test activation script")
    modes.add_argument("--offline", nargs=6, metavar="INPUT",
                        help="system tar, ERP zip, install script, stage script, bootstrap, APT manifest SHA")
    parser.add_argument("--activate-after", type=Path, help="activation script to run after offline staging")
    args = parser.parse_args()
    if args.activate_after and not args.offline:
        parser.error("--activate-after requires --offline")
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
    payload = {}
    if args.offline:
        *paths, apt_digest = args.offline
        if not re.fullmatch(r"[a-f0-9]{64}", apt_digest):
            parser.error("invalid APT manifest SHA")
        payload = dict(zip(("system.tar", "erp.zip", "install.sh", "stage.py", "boot.sh"),
                           (Path(path) for path in paths), strict=True))
        hashes = {}
        for name, path in payload.items():
            with path.open("rb") as handle:
                hashes[name] = hashlib.file_digest(handle, "sha256").hexdigest()
        command = ["sh", "-ec",
                   "d=$(mktemp -d); mount -o ro,nosuid,nodev,noexec /dev/disk/by-label/CIDATA \"$d\"; "
                   "trap 'umount \"$d\"; rmdir \"$d\"' EXIT; "
                   f"echo '{hashes['boot.sh']}  '\"$d/boot.sh\" | sha256sum -c -; "
                   'sh "$d/boot.sh" ' + " ".join([*(hashes[name] for name in list(payload)[:4]), apt_digest])]
        config["write_files"] = [
            {"path": "/usr/local/sbin/sjerp-offline-firstboot", "permissions": "0700",
             "content": "#!/bin/sh\nexec " + shlex.join(command) + "\n"},
            {"path": "/etc/systemd/system/sjerp-offline-firstboot.service", "permissions": "0644",
             "content": (
                 "[Unit]\nDescription=Resume SJERP offline installation\n"
                 "After=cloud-final.service\n"
                 "ConditionPathExists=!/srv/sjerp/versions/96276dffa07c11fb60720a439269df8c36031f7a/READY\n"
                 "[Service]\nType=oneshot\nExecStart=/usr/local/sbin/sjerp-offline-firstboot\n"
                 "TimeoutStartSec=30min\n"
                 "[Install]\nWantedBy=multi-user.target\n"
             )},
        ]
        config["runcmd"] = [["systemctl", "daemon-reload"],
                            ["systemctl", "--no-block", "enable", "--now", "sjerp-offline-firstboot.service"]]
    if args.activate_after:
        config["write_files"].extend([
            {"path": "/usr/local/sbin/sjerp-activate-offline-test", "permissions": "0700",
             "content": args.activate_after.read_text(encoding="utf-8")},
            {"path": "/etc/systemd/system/sjerp-test-activation.service", "permissions": "0644",
             "content": (
                 "[Unit]\nDescription=Activate isolated SJERP instance\n"
                 "Requires=sjerp-offline-firstboot.service\n"
                 "After=cloud-final.service sjerp-offline-firstboot.service\n"
                 "ConditionPathExists=!/srv/sjerp/current\n"
                 "[Service]\nType=oneshot\nExecStart=/usr/local/sbin/sjerp-activate-offline-test\n"
                 "TimeoutStartSec=15min\n[Install]\nWantedBy=multi-user.target\n"
             )},
        ])
        config["runcmd"].append(
            ["systemctl", "--no-block", "enable", "--now", "sjerp-test-activation.service"]
        )
    if args.activate:
        config["ssh_deletekeys"] = False
        config["write_files"] = [
            {"path": "/usr/local/sbin/sjerp-activate-offline-test", "permissions": "0700",
             "content": args.activate.read_text(encoding="utf-8")},
        ]
        config["runcmd"] = [["/usr/bin/systemd-run", "--unit=sjerp-test-activation",
                            "/usr/local/sbin/sjerp-activate-offline-test"]]
    if args.upgrade:
        config["ssh_deletekeys"] = False
        payload = dict(zip(("rehearse.py", "source.pack", "target.zip", "stage.py",
                            "upgrade-pilot-release.py", "backup-before-upgrade.py"),
                           map(Path, args.upgrade), strict=True))
        wrapper = (
            "#!/bin/sh\nset -eu\n"
            "d=$(mktemp -d)\n"
            "trap 'if mountpoint -q \"$d\"; then umount \"$d\"; fi; rmdir \"$d\"' EXIT\n"
            'mount -o ro,nosuid,nodev,noexec /dev/disk/by-label/CIDATA "$d"\n'
            'python3 "$d/rehearse.py" "$d"\n'
        )
        config["write_files"] = [{"path": "/usr/local/sbin/sjerp-test-upgrade", "permissions": "0700",
                                  "content": wrapper}]
        config["runcmd"] = [["/usr/bin/systemd-run", "--unit=sjerp-test-upgrade",
                            "/usr/local/sbin/sjerp-test-upgrade"]]
    if args.lan_test:
        config["ssh_deletekeys"] = False
        config["write_files"] = [
            {"path": "/usr/local/sbin/sjerp-enable-test-lan", "permissions": "0700",
             "content": args.lan_test.read_text(encoding="utf-8")},
        ]
        config["runcmd"] = [["/usr/bin/systemd-run", "--unit=sjerp-test-lan",
                            "/usr/local/sbin/sjerp-enable-test-lan"]]
    if args.business_test:
        config["ssh_deletekeys"] = False
        config["write_files"] = [
            {"path": "/usr/local/sbin/sjerp-prepare-test-business", "permissions": "0700",
             "content": args.business_test.read_text(encoding="utf-8")},
        ]
        config["runcmd"] = [["/usr/bin/systemd-run", "--unit=sjerp-test-business",
                            "/usr/local/sbin/sjerp-prepare-test-business"]]
    if args.admin_console:
        config["ssh_deletekeys"] = False
        config["write_files"] = [
            {"path": "/usr/local/sbin/sjerp-create-test-admin.py", "permissions": "0644",
             "content": args.admin_console.read_text(encoding="utf-8")},
            {"path": "/etc/systemd/system/sjerp-admin-console.service", "permissions": "0644",
             "content": (
                 "[Unit]\nDescription=Interactive ALEX ERP administrator setup\n"
                 "Requires=sjerp-local@a.service\nAfter=sjerp-local@a.service\n"
                 "Conflicts=getty@tty2.service\nAfter=getty@tty2.service\n"
                 "[Service]\nType=simple\nUser=sjerp-a\nGroup=sjerp-a\n"
                 "WorkingDirectory=/srv/sjerp/current/release/backend\n"
                 "EnvironmentFile=/etc/sjerp/a/runtime.env\nEnvironment=PYTHONPATH=/srv/sjerp/current/release/backend\n"
                 "ExecStart=/srv/sjerp/current/venv/bin/python /usr/local/sbin/sjerp-create-test-admin.py\n"
                 "StandardInput=tty-force\nStandardOutput=tty\nStandardError=tty\n"
                 "TTYPath=/dev/tty2\nTTYReset=yes\nTTYVHangup=yes\nRuntimeMaxSec=15min\n"
             )},
        ]
        config["runcmd"] = [["systemctl", "daemon-reload"],
                            ["systemctl", "--no-block", "start", "sjerp-admin-console.service"]]
    if args.encrypted_admin:
        script, envelope = map(Path, args.encrypted_admin)
        encoded = envelope.read_text(encoding="ascii").strip()
        if not re.fullmatch(r"[a-zA-Z0-9+/]{342}==", encoded):
            parser.error("invalid RSA-2048 OAEP envelope")
        config["ssh_deletekeys"] = False
        config["write_files"] = [
            {"path": "/usr/local/sbin/sjerp-create-encrypted-admin.py", "permissions": "0700",
             "content": script.read_text(encoding="utf-8")},
            {"path": "/etc/systemd/system/sjerp-encrypted-admin.service", "permissions": "0600",
             "content": (
                 "[Unit]\nDescription=Create the ALEX ERP administrator once\n"
                 "Requires=sjerp-local@a.service\nAfter=sjerp-local@a.service\n"
                 "[Service]\nType=oneshot\n"
                 "WorkingDirectory=/srv/sjerp/current/release/backend\n"
                 "EnvironmentFile=/etc/sjerp/a/runtime.env\nEnvironment=PYTHONPATH=/srv/sjerp/current/release/backend\n"
                 f"Environment=SJERP_ADMIN_PASSWORD_ENVELOPE={encoded}\n"
                 "ExecStart=/srv/sjerp/current/venv/bin/python /usr/local/sbin/sjerp-create-encrypted-admin.py\n"
             )},
        ]
        config["runcmd"] = [["systemctl", "daemon-reload"],
                            ["systemctl", "--no-block", "start", "sjerp-encrypted-admin.service"]]
    if args.team_tls:
        script, ca, leaf = map(Path, args.team_tls)
        config["ssh_deletekeys"] = False
        config["write_files"] = [
            {"path": "/usr/local/sbin/sjerp-enable-team-https", "permissions": "0700",
             "content": script.read_text(encoding="utf-8")},
            {"path": "/var/lib/sjerp-team-tls/sjerp-alex-ca.pem", "permissions": "0644",
             "content": ca.read_text(encoding="ascii")},
            {"path": "/var/lib/sjerp-team-tls/sjerp-alex-server.pem", "permissions": "0644",
             "content": leaf.read_text(encoding="ascii")},
        ]
        config["runcmd"] = [["/usr/bin/systemd-run", "--unit=sjerp-team-https",
                            "/usr/local/sbin/sjerp-enable-team-https"]]
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
        with ExitStack() as sources:
            for file_number, (name, path) in enumerate(payload.items()):
                handle = sources.enter_context(path.open("rb"))
                iso.add_fp(handle, path.stat().st_size, iso_path=f"/FILE{file_number:05d}.BIN;1",
                           joliet_path=f"/{name}")
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
        for name, path in payload.items():
            with path.open("rb") as expected, iso.open_file_from_iso(joliet_path=f"/{name}") as actual:
                if hashlib.file_digest(expected, "sha256").digest() != hashlib.file_digest(actual, "sha256").digest():
                    raise ValueError(f"Seed payload verification failed: {name}")
    finally:
        iso.close()


if __name__ == "__main__":
    main()
