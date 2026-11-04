"""Run the production restore CLI as root for an ephemeral Linux acceptance."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def _write_private_file(path, content):
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())


def main():
    if os.environ.get("GITHUB_ACTIONS") != "true" or os.geteuid() != 0:
        raise RuntimeError("This signer requires the task-owned Linux recovery identity")
    source = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    encryption_key = sys.stdin.buffer.readline(4097).rstrip(b"\r\n")
    if not encryption_key or len(encryption_key) > 4096:
        raise ValueError("Invalid synthetic encryption key")

    backend = Path(__file__).resolve().parents[2]
    temp_root = os.environ.get("TMPDIR")
    with tempfile.TemporaryDirectory(prefix="sunjack-receipt-cli-", dir=temp_root) as temporary:
        private_root = Path(temporary)
        os.chmod(private_root, 0o700)
        key_file = private_root / "encryption.key"
        _write_private_file(key_file, encryption_key)
        cli_config = {
            "connection": source["connection"],
            "pg_bin": source["pg_bin"],
            "expected_database": source["database"],
            "expected_system_identifier": source["system_identifier"],
            "app_sha": os.environ["GITHUB_SHA"],
            "archive": source["archive"],
            "expected_sha256": source["plaintext_sha256"],
            "encrypted_sha256": source["cipher_sha256"],
            "media_parent": source["media_parent"],
            "encryption": {"key_file": str(key_file), "executable": source["gpg"]},
            "receipt_signing": {"executable": source["openssl"], "private_key": source["signing_key"]},
            "receipt_output": source["receipt_output"],
        }
        if "receipt_read_group" in source:
            cli_config["receipt_read_group"] = source["receipt_read_group"]
        config_file = private_root / "operations-backup.json"
        _write_private_file(config_file, json.dumps(cli_config, sort_keys=True).encode("utf-8"))

        process = subprocess.run(
            [sys.executable, str(backend / "operations_backup.py"), "restore-encrypted-verify",
             "--config", str(config_file)],
            capture_output=True, text=True, timeout=600,
        )
        try:
            result = json.loads(process.stdout)
        except (json.JSONDecodeError, TypeError) as error:
            raise RuntimeError("operations_backup CLI returned invalid JSON") from error
        if process.returncode != 0 or result.get("status") != "VERIFIED":
            raise RuntimeError("operations_backup CLI failed: " + str(result.get("error_type", "unknown error")))
        if result.get("receipt_file") != source["receipt_output"]:
            raise RuntimeError("operations_backup CLI published to an unexpected receipt path")
        print(json.dumps({
            "status": "VERIFIED",
            "receipt_file": result["receipt_file"],
            "database": result["database"],
            "media_root": result["media_root"],
            "verified": result["verified"],
            "audit_truncate_rejected": result["audit_truncate_rejected"],
        }, sort_keys=True))


if __name__ == "__main__":
    main()
