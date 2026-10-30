import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings


class LegacyQaToolSafetyTests(SimpleTestCase):
    def test_business_flow_command_is_retired(self):
        with self.assertRaisesRegex(CommandError, "is retired"):
            call_command("run_business_flow_checks")

    def test_edge_business_flow_command_is_retired(self):
        with self.assertRaisesRegex(CommandError, "is retired"):
            call_command("run_edge_business_flow_checks")

    @override_settings(
        APP_STAGE="production",
        DATABASES={"default": {"ENGINE": "django.db.backends.postgresql", "NAME": "business"}},
    )
    def test_seed_demo_rejects_deployed_stage(self):
        from crm.management.commands.seed_demo import Command

        with self.assertRaisesRegex(CommandError, "APP_STAGE=development"):
            Command()._assert_safe_runtime()

    @override_settings(
        APP_STAGE="development",
        DATABASES={"default": {"ENGINE": "django.db.backends.postgresql", "NAME": "business"}},
    )
    def test_seed_demo_rejects_non_sqlite_database(self):
        from crm.management.commands.seed_demo import Command

        with self.assertRaisesRegex(CommandError, "非 SQLite"):
            Command()._assert_safe_runtime()

    @override_settings(
        APP_STAGE="development",
        DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": "shared.sqlite3"}},
    )
    def test_seed_demo_rejects_explicit_database_without_isolation_identity(self):
        from crm.management.commands.seed_demo import Command

        missing_identity = {
            "DATABASE_URL": "sqlite:///shared.sqlite3",
            "ISOLATED_TEST_ROOT": "",
            "ISOLATED_TEST_RUN_ID": "",
            "ISOLATED_TEST_TOKEN": "",
            "ISOLATED_TEST_DATABASE": "",
            "ISOLATED_TEST_MEDIA_ROOT": "",
        }
        with patch.dict(os.environ, missing_identity, clear=False):
            with self.assertRaisesRegex(CommandError, "未标记的 DATABASE_URL"):
                Command()._assert_safe_runtime()

    def test_seed_demo_accepts_only_existing_checkout_default_database(self):
        from crm.management.commands.seed_demo import Command

        with tempfile.TemporaryDirectory(prefix="sunjack-seed-default-") as temp_root:
            base_dir = Path(temp_root)
            database_path = base_dir / "db.sqlite3"
            database_path.touch()
            with patch.dict(os.environ, {"DATABASE_URL": ""}, clear=False):
                with override_settings(
                    APP_STAGE="development",
                    BASE_DIR=base_dir,
                    DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": str(database_path)}},
                ):
                    Command()._assert_safe_runtime()

    def test_seed_demo_rejects_unmarked_sqlite_outside_checkout(self):
        from crm.management.commands.seed_demo import Command

        with tempfile.TemporaryDirectory(prefix="sunjack-seed-shared-") as temp_root:
            database_path = Path(temp_root) / "shared.sqlite3"
            database_path.touch()
            with patch.dict(os.environ, {"DATABASE_URL": ""}, clear=False):
                with override_settings(
                    APP_STAGE="development",
                    DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": str(database_path)}},
                ):
                    with self.assertRaisesRegex(CommandError, "仅允许当前工作树"):
                        Command()._assert_safe_runtime()

    def test_seed_demo_rejects_additional_database_alias(self):
        from crm.management.commands.seed_demo import Command

        with override_settings(
            APP_STAGE="development",
            DATABASES={
                "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": "db.sqlite3"},
                "reporting": {"ENGINE": "django.db.backends.sqlite3", "NAME": "reporting.sqlite3"},
            },
        ):
            with self.assertRaisesRegex(CommandError, "额外数据库连接"):
                Command()._assert_safe_runtime()

    def test_seed_demo_rejects_missing_default_database_file(self):
        from crm.management.commands.seed_demo import Command

        with tempfile.TemporaryDirectory(prefix="sunjack-seed-missing-") as temp_root:
            with patch.dict(os.environ, {"DATABASE_URL": ""}, clear=False):
                with override_settings(
                    APP_STAGE="development",
                    BASE_DIR=Path(temp_root),
                    DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": str(Path(temp_root) / "db.sqlite3")}},
                ):
                    with self.assertRaisesRegex(CommandError, "已由迁移创建"):
                        Command()._assert_safe_runtime()

    def test_seed_demo_accepts_marked_isolated_sqlite(self):
        from crm.management.commands.seed_demo import Command

        with tempfile.TemporaryDirectory(prefix="sunjack-seed-isolated-") as temp_root:
            root = Path(temp_root) / "run"
            root.mkdir()
            database_path = root / "db.sqlite3"
            database_path.touch()
            media_path = root / "media"
            media_path.mkdir()
            run_id = "seed-demo-unit"
            token = "isolated-token"
            marker = {"runId": run_id, "token": token, "root": str(root.resolve())}
            (root / ".sunjack-playwright-isolation.json").write_text(json.dumps(marker), encoding="utf-8")
            isolated_env = {
                "APP_STAGE": "development",
                "DATABASE_URL": f"sqlite:///{database_path.as_posix()}",
                "ISOLATED_TEST_ROOT": str(root),
                "ISOLATED_TEST_RUN_ID": run_id,
                "ISOLATED_TEST_TOKEN": token,
                "ISOLATED_TEST_DATABASE": str(database_path),
                "ISOLATED_TEST_MEDIA_ROOT": str(media_path),
            }
            with patch.dict(os.environ, isolated_env, clear=False):
                with override_settings(
                    APP_STAGE="development",
                    BASE_DIR=root,
                    MEDIA_ROOT=media_path,
                    MEDIA_STORAGE_BACKEND="django.core.files.storage.FileSystemStorage",
                    RBAC_ENFORCEMENT=False,
                    DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": str(database_path)}},
                ):
                    Command()._assert_safe_runtime()
