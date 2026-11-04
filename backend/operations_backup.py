"""Explicit PostgreSQL/private-media maintenance backup and isolated restore."""
import argparse
import json
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("backup", "restore"))
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    try:
        config = json.loads(Path(args.config).read_text(encoding="utf-8"))
        allowed = {"connection", "pg_bin", "expected_database", "expected_system_identifier", "app_sha", "media_root", "destination", "archive", "expected_sha256", "media_parent"}
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
            result = service.backup(media_root=config["media_root"], destination=config["destination"])
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
