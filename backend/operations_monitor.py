"""Exit nonzero when a verified backup is missing or overdue; safe for schedulers."""
import argparse
import json
from pathlib import Path
import sys

from crm.services.operations_monitor import check_backup_freshness


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    try:
        config = json.loads(Path(args.config).read_text(encoding="utf-8"))
        if set(config) != {"archive", "receipt_file", "receipt_verification", "maximum_backup_age_seconds"}:
            raise ValueError("Unexpected monitor configuration")
        receipt_file = Path(config.pop("receipt_file"))
        if not receipt_file.is_absolute() or receipt_file.is_symlink() or not receipt_file.is_file():
            raise ValueError("A separately stored receipt file is required")
        with receipt_file.open("rb") as stream:
            raw = stream.read(65537)
        if len(raw) > 65536:
            raise ValueError("Receipt file is too large")
        result = check_backup_freshness(**config, restore_receipt=json.loads(raw))
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception as error:
        print(json.dumps({"status": "ALERT", "error_type": type(error).__name__}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
