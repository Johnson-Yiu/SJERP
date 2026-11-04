"""Recovery-role subprocess for an ephemeral CI service; never prints key bytes."""
import json
import os
from pathlib import Path
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

from crm.services.operations_postgres import MaintenanceBackup
from crm.services.operations_receipt import restore_and_sign


def main():
    if os.environ.get("GITHUB_ACTIONS") != "true" or os.geteuid() != 0:
        raise RuntimeError("This test signer requires the task-owned Linux CI recovery role")
    config = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    key = sys.stdin.buffer.readline(4097).rstrip(b"\r\n")
    if len(key) > 4096:
        raise ValueError("Invalid synthetic encryption key")
    service = MaintenanceBackup(connection_options=config["connection"], pg_bin=config["pg_bin"],
        expected_database=config["database"], expected_system_identifier=config["system_identifier"], app_sha=os.environ["GITHUB_SHA"])
    receipt, restored = restore_and_sign(service, encrypted_archive=config["archive"], encrypted_sha256=config["cipher_sha256"],
        plaintext_sha256=config["plaintext_sha256"], media_parent=config["media_parent"], gpg_executable=config["gpg"],
        encryption_key=key, openssl_executable=config["openssl"], signing_key=config["signing_key"])
    print(json.dumps({"receipt": receipt, "restored": restored}))


if __name__ == "__main__":
    main()
