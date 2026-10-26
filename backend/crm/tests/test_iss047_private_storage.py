import io
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.core.files.storage import FileSystemStorage
from django.test import SimpleTestCase

from crm.services.private_media import (
    PrivateMediaStorageError,
    build_private_media_manifest,
    compare_private_media_manifest,
)


class ISS047PrivateMediaStorageTests(SimpleTestCase):
    def test_manifest_is_relative_deterministic_and_sha256_verified(self):
        with TemporaryDirectory() as root:
            media_root = Path(root)
            (media_root / "follow-up-attachments/2026/10").mkdir(parents=True)
            (media_root / "sku-images/2026/10").mkdir(parents=True)
            (media_root / "follow-up-attachments/2026/10/a.txt").write_bytes(b"attachment")
            (media_root / "sku-images/2026/10/image.bin").write_bytes(b"image")

            manifest = build_private_media_manifest(media_root)

            self.assertEqual(manifest["file_count"], 2)
            self.assertEqual(manifest["total_bytes"], 15)
            self.assertTrue(all(not item["path"].startswith("/") for item in manifest["files"]))
            self.assertTrue(all(".." not in Path(item["path"]).parts for item in manifest["files"]))
            self.assertEqual(compare_private_media_manifest(manifest, media_root), [])

            (media_root / "sku-images/2026/10/image.bin").write_bytes(b"changed")
            self.assertIn("changed: sku-images/2026/10/image.bin", compare_private_media_manifest(manifest, media_root))

    def test_new_filesystem_storage_instance_reopens_file_after_restart_simulation(self):
        with TemporaryDirectory() as root:
            first_process_storage = FileSystemStorage(location=root)
            stored_name = first_process_storage.save("restart-check.txt", ContentFile(b"persistent bytes"))
            before_restart = build_private_media_manifest(root)

            # A new storage object models a service restart without changing
            # the mounted single-server volume.
            after_restart_storage = FileSystemStorage(location=root)
            with after_restart_storage.open(stored_name, "rb") as source:
                self.assertEqual(source.read(), b"persistent bytes")
            self.assertEqual(compare_private_media_manifest(before_restart, root), [])

    def test_management_command_can_write_and_verify_restore_manifest(self):
        with TemporaryDirectory() as root, TemporaryDirectory() as output:
            media_root = Path(root)
            (media_root / "certificates").mkdir()
            (media_root / "certificates/cert.pdf").write_bytes(b"certificate")
            manifest_path = Path(output) / "media-manifest.json"
            stdout = io.StringIO()

            call_command(
                "private_media_manifest",
                "--media-root",
                str(media_root),
                "--output",
                str(manifest_path),
                stdout=stdout,
            )
            self.assertIn("Wrote private media manifest", stdout.getvalue())
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["file_count"], 1)

            verified = io.StringIO()
            call_command(
                "private_media_manifest",
                "--media-root",
                str(media_root),
                "--verify",
                str(manifest_path),
                stdout=verified,
            )
            self.assertIn("PASS private media manifest verification", verified.getvalue())

            (media_root / "certificates/cert.pdf").write_bytes(b"tampered")
            with self.assertRaises(CommandError):
                call_command(
                    "private_media_manifest",
                    "--media-root",
                    str(media_root),
                    "--verify",
                    str(manifest_path),
                    stdout=io.StringIO(),
                )

    def test_symlink_is_rejected_in_private_media_inventory(self):
        with TemporaryDirectory() as root, TemporaryDirectory() as outside:
            outside_file = Path(outside) / "outside.txt"
            outside_file.write_bytes(b"must not be included")
            link = Path(root) / "escaped.txt"
            try:
                os.symlink(outside_file, link)
            except (OSError, NotImplementedError):
                self.skipTest("symlink creation is not available in this environment")
            with self.assertRaises(PrivateMediaStorageError):
                build_private_media_manifest(root)
