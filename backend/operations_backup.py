"""Explicit PostgreSQL/private-media maintenance backup and isolated restore."""
import argparse
import json
from pathlib import Path
import sys
import tempfile
import uuid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("backup", "restore"))
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    try:
        config = json.loads(Path(args.config).read_text(encoding="utf-8"))
        allowed = {"connection", "pg_bin", "expected_database", "expected_system_identifier", "app_sha", "media_root", "destination", "destination_directory", "archive", "expected_sha256", "media_parent", "encryption"}
        if not isinstance(config, dict) or set(config) - allowed:
            raise ValueError("Unsupported configuration")
        connection = config["connection"]
        if not isinstance(connection, dict) or set(connection) - {"host", "port", "user", "dbname", "passfile", "sslmode", "sslrootcert", "connect_timeout"}:
            raise ValueError("Only nonsecret connection options and a separate passfile path are accepted")
        if connection.get("dbname") != config["expected_database"]:
            raise ValueError("Database identity must be explicit")
        import os
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
        # Service helpers need Django settings, but this process never starts a web service.
        from crm.services.operations_postgres import MaintenanceBackup
        service = MaintenanceBackup(connection_options=connection, pg_bin=config["pg_bin"],
                                    expected_database=config["expected_database"], expected_system_identifier=config["expected_system_identifier"], app_sha=config["app_sha"])
        if args.operation == "backup":
            destination = config.get("destination")
            if "destination_directory" in config:
                if destination:
                    raise ValueError("Choose a destination or destination directory")
                parent = Path(config["destination_directory"])
                if not parent.is_absolute() or parent.is_symlink() or not parent.is_dir():
                    raise ValueError("An explicit existing backup directory is required")
                destination = parent / ("backup-" + uuid.uuid4().hex + (".gpg" if config.get("encryption") else ".zip"))
            if not destination:
                raise ValueError("Backup destination is required")
            if config.get("encryption"):
                from crm.services.operations_crypto import crypt_file
                encryption = dict(config["encryption"])
                if set(encryption) - {"key_file", "executable", "msys_paths"}:
                    raise ValueError("Unsupported encryption configuration")
                key_path = Path(encryption.pop("key_file"))
                if not key_path.is_absolute() or key_path.is_symlink() or not key_path.is_file():
                    raise ValueError("Separately provisioned key file required")
                if key_path.parent.resolve() == Path(destination).parent.resolve() or Path(config["media_root"]).resolve() in key_path.resolve().parents:
                    raise ValueError("Key must be separated from backup and media directories")
                with key_path.open("rb") as key_stream:
                    key = key_stream.read(4097).rstrip(b"\r\n")
                if len(key) > 4096:
                    raise ValueError("Invalid key size")
                with tempfile.TemporaryDirectory(prefix="sunjack-encrypted-backup-") as folder:
                    plaintext = Path(folder) / "backup.zip"
                    backup = service.backup(media_root=config["media_root"], destination=plaintext)
                    result = crypt_file(plaintext, destination, key=key, expected_sha256=backup["sha256"], **encryption)
                    crypt_file(destination, Path(folder) / "verified.zip", key=key, expected_sha256=backup["sha256"], decrypt=True, **encryption)
                    result["plaintext_sha256"] = backup["sha256"]
                    result["encryption_roundtrip_verified"] = True
            else:
                result = service.backup(media_root=config["media_root"], destination=destination)
            result["archive"] = str(destination)
        else:
            result = service.restore(archive=config["archive"], expected_sha256=config["expected_sha256"], media_parent=config["media_parent"])
        print(json.dumps({"status": "VERIFIED", **result}, sort_keys=True))
        return 0
    except Exception as error:
        print(json.dumps({"status": "FAILED", "error_type": type(error).__name__,
                          "cleanup_errors": getattr(error, "__notes__", [])}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
