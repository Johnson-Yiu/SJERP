"""Encryption and explicit receipt-driven retention for operations backups."""
import argparse
import json
from pathlib import Path
import sys

from crm.services.operations_crypto import crypt_file
from crm.services.operations_retention import prune_verified


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("encrypt", "decrypt", "prune"))
    parser.add_argument("--config", required=True)
    parser.add_argument("--execute-prune", action="store_true")
    args = parser.parse_args()
    try:
        config = json.loads(Path(args.config).read_text(encoding="utf-8"))
        if args.operation == "prune":
            if set(config) - {"root", "owner_id", "receipts", "keep", "minimum_age_seconds"}:
                raise ValueError("Unsupported retention configuration")
            result = prune_verified(**config, execute=args.execute_prune)
        else:
            if args.execute_prune or set(config) - {"source", "destination", "executable", "key_file", "expected_sha256", "msys_paths"}:
                raise ValueError("Unsupported encryption configuration")
            key_path = Path(config.pop("key_file"))
            if not key_path.is_absolute() or key_path.is_symlink() or not key_path.is_file():
                raise ValueError("Separately provisioned key file required")
            with key_path.open("rb") as stream:
                key = stream.read(4097)
            if len(key) > 4096:
                raise ValueError("Invalid key size")
            if key_path.resolve() in (Path(config["source"]).resolve(), Path(config["destination"]).resolve()):
                raise ValueError("Key and archive paths must differ")
            result = crypt_file(**config, key=key.rstrip(b"\r\n"), decrypt=args.operation == "decrypt")
        print(json.dumps({"status": "VERIFIED", **result}, sort_keys=True))
        return 0
    except Exception as error:
        print(json.dumps({"status": "FAILED", "error_type": type(error).__name__,
                          "cleanup_errors": getattr(error, "__notes__", [])}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
