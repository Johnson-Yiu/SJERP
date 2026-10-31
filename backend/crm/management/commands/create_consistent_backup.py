import json

from django.core.management.base import BaseCommand, CommandError

from crm.services.backup_recovery import BackupRecoveryError, create_consistent_backup


class Command(BaseCommand):
    help = "Create a quiesced, single-archive SQLite and private-media backup."

    def add_arguments(self, parser):
        parser.add_argument("--database", help="File-backed SQLite database to snapshot.")
        parser.add_argument("--media-root", help="Override the private MEDIA_ROOT.")
        parser.add_argument("--output-dir", required=True, help="Local backup directory.")
        parser.add_argument("--backup-id", help="Stable archive identifier for scheduled runs.")
        parser.add_argument(
            "--quiesced",
            action="store_true",
            help="Confirm the ERP process has stopped DB and media writes for this operation.",
        )
        parser.add_argument("--encrypted-output", help="Optional .age output path for an independent encrypted copy.")
        parser.add_argument("--age-recipient", help="Public age recipient; private keys are never read by this command.")
        parser.add_argument("--status-file", help="Write structured PASS/FAILED status for monitoring.")
        parser.add_argument(
            "--tighten-permissions",
            action="store_true",
            help="Explicitly change an existing POSIX backup directory to owner-only 0700 after reviewing ownership.",
        )

    def handle(self, *args, **options):
        try:
            result = create_consistent_backup(
                database=options.get("database"),
                media_root=options.get("media_root"),
                output_dir=options["output_dir"],
                backup_id=options.get("backup_id"),
                quiesced=options["quiesced"],
                encrypted_output=options.get("encrypted_output"),
                age_recipient=options.get("age_recipient"),
                status_file=options.get("status_file"),
                tighten_permissions=options["tighten_permissions"],
            )
        except (BackupRecoveryError, OSError, ValueError) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
