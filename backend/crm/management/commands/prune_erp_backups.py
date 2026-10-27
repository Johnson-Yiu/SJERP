import json

from django.core.management.base import BaseCommand, CommandError

from crm.services.backup_recovery import BackupRecoveryError, prune_backup_archives


class Command(BaseCommand):
    help = "Plan or apply the 7 daily, 4 weekly and 3 monthly backup retention policy."

    def add_arguments(self, parser):
        parser.add_argument("--directory", required=True, help="Backup directory.")
        parser.add_argument("--apply", action="store_true", help="Delete archives outside the retention policy.")

    def handle(self, *args, **options):
        try:
            result = prune_backup_archives(options["directory"], apply=options["apply"])
        except (BackupRecoveryError, OSError, ValueError) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
