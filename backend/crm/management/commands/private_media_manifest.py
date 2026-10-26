import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from crm.services.private_media import (
    PrivateMediaStorageError,
    build_private_media_manifest,
    compare_private_media_manifest,
)


class Command(BaseCommand):
    help = "Create or verify a SHA256 manifest for the private MEDIA_ROOT tree."

    def add_arguments(self, parser):
        parser.add_argument("--media-root", help="Override MEDIA_ROOT for an isolated backup/restore check.")
        parser.add_argument("--output", help="Write the manifest JSON to this local path.")
        parser.add_argument("--verify", help="Verify the current tree against an existing manifest JSON file.")

    def handle(self, *args, **options):
        if options["output"] and options["verify"]:
            raise CommandError("--output and --verify cannot be used together.")
        try:
            manifest = build_private_media_manifest(options["media_root"])
        except PrivateMediaStorageError as exc:
            raise CommandError(str(exc)) from exc

        if options["verify"]:
            manifest_path = Path(options["verify"])
            try:
                expected = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                raise CommandError(f"Cannot read manifest: {manifest_path}") from exc
            differences = compare_private_media_manifest(expected, options["media_root"])
            if differences:
                raise CommandError("Private media restore verification failed: " + "; ".join(differences))
            self.stdout.write(self.style.SUCCESS("PASS private media manifest verification"))
            return

        payload = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
        if options["output"]:
            output_path = Path(options["output"])
            try:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(payload, encoding="utf-8")
            except OSError as exc:
                raise CommandError(f"Cannot write manifest: {output_path}") from exc
            self.stdout.write(self.style.SUCCESS(f"Wrote private media manifest: {output_path}"))
            return
        self.stdout.write(payload, ending="")
