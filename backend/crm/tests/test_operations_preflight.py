import tempfile
from pathlib import Path
from unittest import TestCase, mock

from crm.services.operations_readiness import inspect_config


class OperationsPreflightTests(TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="sunjack-operations-preflight-")
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        for name in ("media", "static", "backup"):
            (root / name).mkdir()
        self.config = {"public_origin": "https://erp.example.invalid", "media_root": str(root / "media"),
                       "static_root": str(root / "static"), "backup_root": str(root / "backup"),
                       "min_free_bytes": 0, "min_free_inodes": 0}

    def test_safe_inputs_never_authorize_backup(self):
        result = inspect_config(self.config)
        self.assertTrue(result["ok"])
        self.assertFalse(result["backup_authorized"])
        self.assertTrue(result["warnings"])

    def test_http_and_embedded_credentials_rejected_without_echo(self):
        for origin in ("http://erp.example.invalid", "https://synthetic:secret@example.invalid", "https://erp.example.invalid:notaport"):
            with self.subTest(origin=origin):
                result = inspect_config({**self.config, "public_origin": origin})
                self.assertFalse(result["ok"])
                self.assertNotIn("secret", str(result))

    def test_unknown_secret_field_rejected_without_echo(self):
        result = inspect_config({**self.config, "password": "synthetic-secret"})
        self.assertFalse(result["ok"])
        self.assertNotIn("synthetic-secret", str(result))

    def test_overlapping_roots_and_relative_paths_rejected(self):
        for changes in ({"static_root": self.config["media_root"]}, {"backup_root": "relative"}):
            with self.subTest(changes=changes):
                self.assertFalse(inspect_config({**self.config, **changes})["ok"])

    def test_insufficient_space_and_invalid_threshold_rejected(self):
        with mock.patch("crm.services.operations_readiness.shutil.disk_usage", return_value=mock.Mock(free=1)):
            self.assertFalse(inspect_config({**self.config, "min_free_bytes": 2})["ok"])
        self.assertFalse(inspect_config({**self.config, "min_free_bytes": True})["ok"])

    def test_requested_inode_check_fails_closed_when_unavailable(self):
        with mock.patch("crm.services.operations_readiness.shutil.disk_usage", return_value=mock.Mock(free=100)):
            with mock.patch("crm.services.operations_readiness.os.statvfs", None, create=True):
                with mock.patch("crm.services.operations_readiness.hasattr", return_value=False):
                    self.assertFalse(inspect_config({**self.config, "min_free_inodes": 1})["ok"])
