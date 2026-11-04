"""Explicit PostgreSQL/private-media maintenance backup and isolated restore."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
import uuid


def _file_identity(path):
    info = Path(path).lstat()
    return info.st_dev, info.st_ino


def _unlink_owned(path, identity):
    if identity is None:
        return
    path = Path(path)
    try:
        current = _file_identity(path)
    except FileNotFoundError:
        return
    if current != identity:
        raise RuntimeError("Refusing to remove a staging path whose identity changed")
    path.unlink()


def _encrypted_backup(service, *, media_root, destination, key, encryption, crypt_file):
    destination = Path(destination)
    if not destination.parent.is_dir():
        raise ValueError("An existing backup destination directory is required")
    if os.path.lexists(destination):
        raise FileExistsError("Backup destination already exists")

    # The staging ciphertext is exclusive and shares the final directory so the
    # final name can be published with an atomic, no-replace hard link.
    staging = destination.parent / (".sunjack-encrypted-" + uuid.uuid4().hex + ".partial")
    staging_identity = None
    published = False
    try:
        with tempfile.TemporaryDirectory(prefix="sunjack-encrypted-backup-") as folder:
            plaintext = Path(folder) / "backup.zip"
            backup = service.backup(media_root=media_root, destination=plaintext)
            result = crypt_file(plaintext, staging, key=key, expected_sha256=backup["sha256"], **encryption)
            staging_identity = _file_identity(staging)
            crypt_file(staging, Path(folder) / "verified.zip", key=key,
                       expected_sha256=backup["sha256"], decrypt=True, **encryption)
            result["plaintext_sha256"] = backup["sha256"]
            result["encryption_roundtrip_verified"] = True
            if backup.get("staging_cleanup_warning"):
                result["plaintext_staging_cleanup_warning"] = backup["staging_cleanup_warning"]

        if _file_identity(staging) != staging_identity:
            raise RuntimeError("Staging ciphertext changed before publication")
        os.link(staging, destination, follow_symlinks=False)
        destination_identity = _file_identity(destination)
        if destination_identity != staging_identity:
            try:
                _unlink_owned(destination, staging_identity)
            except Exception as cleanup_error:
                cleanup_error.add_note("Unexpected published path cleanup was incomplete")
            raise RuntimeError("Published ciphertext identity did not match verified staging file")
        published = True
        try:
            _unlink_owned(staging, staging_identity)
            staging_identity = None
        except Exception as cleanup_error:
            result["staging_ciphertext_cleanup_warning"] = type(cleanup_error).__name__
        return result
    except Exception as error:
        if not published:
            try:
                _unlink_owned(staging, staging_identity)
            except Exception as cleanup_error:
                error.add_note("Owned staging ciphertext cleanup failed: " + type(cleanup_error).__name__)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("backup", "restore", "restore-encrypted-verify"))
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    try:
        config = json.loads(Path(args.config).read_text(encoding="utf-8"))
        allowed = {"connection", "pg_bin", "expected_database", "expected_system_identifier", "app_sha", "media_root", "destination", "destination_directory", "archive", "expected_sha256", "encrypted_sha256", "media_parent", "encryption", "receipt_signing", "receipt_output"}
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
                result = _encrypted_backup(service, media_root=config["media_root"], destination=destination,
                                           key=key, encryption=encryption, crypt_file=crypt_file)
            else:
                result = service.backup(media_root=config["media_root"], destination=destination)
            result["archive"] = str(destination)
        elif args.operation == "restore-encrypted-verify":
            from crm.services.operations_receipt import restore_and_sign
            encryption = dict(config["encryption"])
            if set(encryption) - {"key_file", "executable", "msys_paths"}:
                raise ValueError("Unsupported encryption configuration")
            key_path = Path(encryption.pop("key_file"))
            if not key_path.is_absolute() or key_path.is_symlink() or not key_path.is_file():
                raise ValueError("Separately provisioned key file required")
            with key_path.open("rb") as stream:
                key = stream.read(4097).rstrip(b"\r\n")
            if len(key) > 4096:
                raise ValueError("Invalid encryption key size")
            signer = config["receipt_signing"]
            if not isinstance(signer, dict) or set(signer) != {"executable", "private_key"}:
                raise ValueError("Independent signing key configuration required")
            receipt_path = Path(config["receipt_output"])
            if not receipt_path.is_absolute() or receipt_path.is_symlink() or receipt_path.exists():
                raise ValueError("New absolute receipt output required")
            receipt, restored = restore_and_sign(service, encrypted_archive=config["archive"],
                encrypted_sha256=config["encrypted_sha256"], plaintext_sha256=config["expected_sha256"],
                media_parent=config["media_parent"], gpg_executable=encryption["executable"], encryption_key=key,
                msys_paths=encryption.get("msys_paths", False), openssl_executable=signer["executable"], signing_key=signer["private_key"])
            try:
                from crm.services.operations_postgres import publish_archive
                with publish_archive(receipt_path) as output:
                    output.write(json.dumps(receipt, sort_keys=True).encode("utf-8"))
            except Exception as error:
                error.add_note("Verified restore exists; operator must inspect target " + restored["database"])
                raise
            result = {**restored, "receipt_file": str(receipt_path)}
            if output.staging_cleanup_warning:
                result["receipt_staging_cleanup_warning"] = output.staging_cleanup_warning
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
