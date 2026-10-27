import json
import zipfile

from django.core.management.base import BaseCommand, CommandError

from crm.services.backup_recovery import BackupRecoveryError, restore_consistent_backup


class Command(BaseCommand):
    help = "Verify and restore a single-archive SQLite and private-media backup into a new isolated directory."

    def add_arguments(self, parser):
        parser.add_argument("--archive", required=True, help="Backup .zip archive.")
        parser.add_argument("--target-dir", required=True, help="New or empty isolated restore directory.")
        parser.add_argument("--result-file", help="Optional structured result path for failed restores.")

    def handle(self, *args, **options):
        try:
            result = restore_consistent_backup(
                archive=options["archive"], target_dir=options["target_dir"], result_file=options.get("result_file")
            )
        except (BackupRecoveryError, OSError, ValueError, zipfile.BadZipFile) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
