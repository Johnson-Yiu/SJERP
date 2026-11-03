"""Control-flow tests run everywhere; PostgreSQL SQL/lock tests never run on SQLite."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, Mock, patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.db import DatabaseError, close_old_connections, connection, connections, transaction
from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.migrations.executor import MigrationExecutor
from django.test import SimpleTestCase, TransactionTestCase
from django.test.runner import DiscoverRunner

from crm.models import CSVImportBatch, CSVImportPreviewAudit, CSVImportRowAudit
from crm.postgres_test_cleanup import (
    GUARD_FUNCTION, TRUNCATE_GUARDS, REVIEW_TABLE, REVIEW_TRIGGER, active_truncate_guards, assert_truncate_guards_enabled,
    bind_created_test_database, execute_test_flush, test_teardown_patch as teardown_patch,
)
from crm.test_runner import DevelopmentAccessTestRunner


class CleanupControlFlowTests(SimpleTestCase):
    """Mocks verify refusal paths/hook scope, not PostgreSQL transactional DDL."""

    def setUp(self):
        self.name = "test_sunjack_" + "a" * 32
        self.conn = MagicMock()
        self.conn.vendor = "postgresql"
        self.conn.alias = "default"
        self.conn.in_atomic_block = False
        self.conn.get_autocommit.return_value = True
        self.conn.settings_dict = {
            "NAME": self.name, "HOST": "127.0.0.1", "PORT": "5432", "USER": "test_owner",
            "OPTIONS": {}, "TEST": {"NAME": None, "MIRROR": None},
        }
        self.conn.ops.quote_name.side_effect = lambda name: f'"{name}"'
        self.cursor = self.conn.cursor.return_value.__enter__.return_value
        self.cursor.fetchone.return_value = (self.name, "public")
        self.cursor.fetchall.return_value = [
            (table, trigger, "O", 34, GUARD_FUNCTION, "public")
            for table, trigger in TRUNCATE_GUARDS.items()
        ]
        self.binding = bind_created_test_database(self.conn, "source_db", self.name)

    def set_guard_state(self, exists, applied):
        def result():
            statement = self.cursor.execute.call_args.args[0]
            return (exists, applied) if "to_regclass" in statement else (self.name, "public")
        self.cursor.fetchone.side_effect = result
        guards = dict(TRUNCATE_GUARDS)
        if exists and applied:
            guards[REVIEW_TABLE] = REVIEW_TRIGGER
        self.cursor.fetchall.return_value = [(table, trigger, "O", 34, GUARD_FUNCTION, "public") for table, trigger in guards.items()]

    def test_ordinary_database_or_nonrandom_name_is_not_enrolled(self):
        for name in ("source_db", "test_source_db", "test_sunjack_not_random"):
            with self.subTest(name=name), self.assertRaises(ImproperlyConfigured):
                bind_created_test_database(self.conn, "source_db", name)
        self.conn.cursor.assert_not_called()

    def test_config_identity_changes_are_rejected_before_sql(self):
        self.conn.settings_dict["NAME"] = "source_db"
        with self.assertRaises(ImproperlyConfigured):
            execute_test_flush(self.conn, self.binding, Mock(), ["TRUNCATE something"])
        self.conn.cursor.assert_not_called()

    def test_live_database_or_schema_mismatch_is_rejected_before_ddl(self):
        for actual in (("source_db", "public"), (self.name, "other_schema")):
            self.cursor.fetchone.return_value = actual
            with self.subTest(actual=actual), self.assertRaises(ImproperlyConfigured):
                execute_test_flush(self.conn, self.binding, Mock(), [])
        self.assertFalse(any("ALTER" in str(call) for call in self.cursor.execute.call_args_list))

    def test_existing_atomic_block_is_rejected(self):
        self.conn.in_atomic_block = True
        with self.assertRaises(ImproperlyConfigured):
            execute_test_flush(self.conn, self.binding, Mock(), [])

    def test_missing_or_disabled_guard_fails_before_disabling_anything(self):
        self.set_guard_state(False, False)
        native = Mock()
        disabled = list(self.cursor.fetchall.return_value)
        disabled[0] = (*disabled[0][:2], "D", *disabled[0][3:])
        for guards in ([], disabled):
            self.cursor.fetchall.return_value = guards
            with self.subTest(guards=guards):
                with patch("crm.postgres_test_cleanup.transaction.atomic", return_value=nullcontext()):
                    with self.assertRaises(ImproperlyConfigured):
                        execute_test_flush(self.conn, self.binding, native, ["TRUNCATE something"])
        native.assert_not_called()
        self.assertFalse(any("DISABLE" in str(call) for call in self.cursor.execute.call_args_list))

    def test_success_locks_before_disabling_and_reenables_all_guards(self):
        self.set_guard_state(True, True)
        events = []
        self.cursor.execute.side_effect = lambda sql, *args: events.append(sql)
        native = Mock(side_effect=lambda sql: events.append("native flush"))
        with patch("crm.postgres_test_cleanup.transaction.atomic", return_value=nullcontext()):
            execute_test_flush(self.conn, self.binding, native, ["TRUNCATE something"])
        lock = next(i for i, sql in enumerate(events) if sql.startswith("LOCK TABLE"))
        disabled = [i for i, sql in enumerate(events) if "DISABLE TRIGGER" in sql]
        enabled = [i for i, sql in enumerate(events) if "ENABLE TRIGGER" in sql]
        self.assertEqual((len(disabled), len(enabled)), (4, 4))
        self.assertIn(REVIEW_TABLE, active_truncate_guards(self.conn))
        self.assertLess(lock, min(disabled))
        self.assertLess(max(disabled), events.index("native flush"))
        self.assertLess(events.index("native flush"), min(enabled))

    def test_pre_0096_cleanup_checks_three_original_guards(self):
        self.set_guard_state(False, False)
        events = []
        self.cursor.execute.side_effect = lambda sql, *args: events.append(sql)
        with patch("crm.postgres_test_cleanup.transaction.atomic", return_value=nullcontext()):
            execute_test_flush(self.conn, self.binding, Mock(), [])
        self.assertEqual(sum("DISABLE TRIGGER" in sql for sql in events), 3)
        self.assertEqual(sum("ENABLE TRIGGER" in sql for sql in events), 3)

    def test_migration_table_mismatch_fails_before_guard_changes(self):
        for exists, applied in ((True, False), (False, True)):
            self.set_guard_state(exists, applied)
            with self.subTest(exists=exists, applied=applied), patch("crm.postgres_test_cleanup.transaction.atomic", return_value=nullcontext()):
                with self.assertRaises(ImproperlyConfigured):
                    execute_test_flush(self.conn, self.binding, Mock(), [])
        self.assertFalse(any("DISABLE TRIGGER" in str(call) for call in self.cursor.execute.call_args_list))

    def test_native_failure_leaves_atomic_context_with_exception(self):
        self.set_guard_state(False, False)
        atomic = MagicMock()
        atomic.__exit__.return_value = False
        native = Mock(side_effect=RuntimeError("injected SQL cleanup failure"))
        with patch("crm.postgres_test_cleanup.transaction.atomic", return_value=atomic):
            with self.assertRaisesRegex(RuntimeError, "injected SQL"):
                execute_test_flush(self.conn, self.binding, native, [])
        self.assertIs(atomic.__exit__.call_args.args[0], RuntimeError)

    def test_hook_is_scoped_to_fixture_teardown_and_restored_on_error(self):
        native = self.conn.ops.execute_sql_flush
        case = Mock()
        case._databases_names.return_value = ["default"]

        def teardown(_case):
            self.conn.ops.execute_sql_flush(["synthetic flush"])
            raise RuntimeError("fixture error")

        with patch.object(TransactionTestCase, "_fixture_teardown", teardown):
            with patch("crm.postgres_test_cleanup.connections", {"default": self.conn}):
                with patch("crm.postgres_test_cleanup.execute_test_flush") as cleanup:
                    with teardown_patch({"default": self.binding}):
                        self.assertIs(self.conn.ops.execute_sql_flush, native)
                        with self.assertRaisesRegex(RuntimeError, "fixture error"):
                            TransactionTestCase._fixture_teardown(case)
                        self.assertIs(self.conn.ops.execute_sql_flush, native)
                    cleanup.assert_called_once_with(self.conn, self.binding, native, ["synthetic flush"])

    def test_runner_rejects_reuse_parallel_custom_name_and_remote_host(self):
        for option in ("keepdb", "parallel", "custom_name", "remote"):
            runner = DevelopmentAccessTestRunner(verbosity=0, interactive=False)
            self.conn.settings_dict["TEST"]["NAME"] = "custom" if option == "custom_name" else None
            self.conn.settings_dict["HOST"] = "remote.example" if option == "remote" else "127.0.0.1"
            runner.keepdb = option == "keepdb"
            runner.parallel = 2 if option == "parallel" else 0
            with self.subTest(option=option), patch("crm.test_runner.connections") as pool:
                pool.all.return_value = [self.conn]
                with patch.object(DiscoverRunner, "setup_databases") as native:
                    with self.assertRaises(ImproperlyConfigured):
                        runner.setup_databases(aliases={"default": False})
                    native.assert_not_called()

    def test_runner_restores_name_configuration_if_setup_fails(self):
        runner = DevelopmentAccessTestRunner(verbosity=0, interactive=False)
        with patch("crm.test_runner.connections") as pool:
            pool.all.return_value = [self.conn]
            pool.__getitem__.return_value = self.conn
            with patch.object(DiscoverRunner, "setup_databases", side_effect=RuntimeError("setup failure")):
                with self.assertRaisesRegex(RuntimeError, "setup failure"):
                    runner.setup_databases(aliases={"default": False})
            self.assertIsNone(self.conn.settings_dict["TEST"]["NAME"])

    def test_runner_refuses_connection_overrides_before_database_setup(self):
        for options, host in (({"dbname": "source_db"}, "127.0.0.1"),
                              ({"hostaddr": "192.0.2.1"}, "127.0.0.1"),
                              ({"service": "external"}, "127.0.0.1"), ({}, "")):
            self.conn.settings_dict["OPTIONS"] = options
            self.conn.settings_dict["HOST"] = host
            runner = DevelopmentAccessTestRunner(verbosity=0, interactive=False)
            with self.subTest(options=options, host=host), patch("crm.test_runner.connections") as pool:
                pool.all.return_value = [self.conn]
                with patch.object(DiscoverRunner, "setup_databases") as native:
                    with self.assertRaises(ImproperlyConfigured):
                        runner.setup_databases(aliases={"default": False})
                    native.assert_not_called()

    def test_runner_refuses_libpq_environment_before_database_setup(self):
        for key in ("PGHOSTADDR", "PGSERVICE", "PGDATABASE", "PGOPTIONS"):
            with self.subTest(key=key), patch.dict("os.environ", {key: "synthetic-override"}):
                with patch("crm.test_runner.connections") as pool:
                    pool.all.return_value = [self.conn]
                    with patch.object(DiscoverRunner, "setup_databases") as native:
                        with self.assertRaises(ImproperlyConfigured):
                            DevelopmentAccessTestRunner(verbosity=0).setup_databases()
                        native.assert_not_called()

    def exercise_setup_failure(self, phase, drop_fails=False):
        runner = DevelopmentAccessTestRunner(verbosity=0, interactive=False)
        source = self.conn.settings_dict["NAME"]
        global_db = {"NAME": "separate_global_source", "TEST": {"NAME": None}}
        self.conn.creation._get_test_db_name.side_effect = lambda: self.conn.settings_dict["TEST"]["NAME"]
        targets = []

        def create(**_kwargs):
            self.assertIs(self.conn._nodb_cursor.__func__, BaseDatabaseWrapper._nodb_cursor)
            target = self.conn.creation._create_test_db(verbosity=0, autoclobber=True)
            targets.append(target)
            self.conn.settings_dict["NAME"] = target
            global_db["NAME"] = target
            if phase == "migration":
                raise RuntimeError("injected migration failure")
            return "old config"

        if phase == "collision":
            self.conn.creation._execute_create_test_db.side_effect = RuntimeError("injected collision")
        binding = patch("crm.test_runner.bind_created_test_database", side_effect=RuntimeError("injected enrollment failure"))
        with patch.object(runner, "_destroy_owned_database") as drop, patch("crm.test_runner.connections") as pool:
            if drop_fails:
                drop.side_effect = RuntimeError("injected drop failure")
            pool.all.return_value = [self.conn]
            pool.__getitem__.return_value = self.conn
            with patch("crm.test_runner.settings", SimpleNamespace(DATABASES={"default": global_db})):
                with patch.object(DiscoverRunner, "setup_databases", side_effect=create):
                    with binding if phase == "enrollment" else nullcontext():
                        with self.assertRaisesRegex(RuntimeError, "injected") as raised:
                            runner.setup_databases(aliases={"default": False})
        self.assertEqual(self.conn.settings_dict["NAME"], source)
        self.assertEqual(global_db["NAME"], "separate_global_source")
        self.assertIsNone(self.conn.settings_dict["TEST"]["NAME"])
        self.assertIsNone(global_db["TEST"]["NAME"])
        if phase == "collision":
            drop.assert_not_called()
        else:
            drop.assert_called_once()
            self.assertIs(drop.call_args.args[0][0], self.conn)
            self.assertEqual(drop.call_args.args[0][1], targets[0])
        if drop_fails:
            self.assertIn("manual isolated cleanup required", raised.exception.__notes__[0])

    def test_partial_setup_failure_cleans_created_database_and_restores_both_settings(self):
        self.exercise_setup_failure("migration")

    def test_enrollment_failure_cleans_created_database_and_restores_both_settings(self):
        self.exercise_setup_failure("enrollment")

    def test_creation_collision_never_drops_an_existing_database(self):
        self.exercise_setup_failure("collision")

    def test_failed_database_drop_is_reported_and_configuration_is_restored(self):
        self.exercise_setup_failure("migration", drop_fails=True)

    def test_runner_enrolls_only_generated_database_and_uninstalls_hook(self):
        runner = DevelopmentAccessTestRunner(verbosity=0, interactive=False)
        source = self.conn.settings_dict["NAME"]
        original_teardown = TransactionTestCase._fixture_teardown

        def create(**_kwargs):
            generated = self.conn.settings_dict["TEST"]["NAME"]
            self.assertRegex(generated, r"^test_sunjack_[0-9a-f]{32}$")
            self.assertNotEqual(generated, source)
            self.conn.settings_dict["NAME"] = generated
            return [(self.conn, source, True)]

        def destroy(old_config, **_kwargs):
            self.assertEqual(old_config, [])
            self.assertEqual(self.conn.settings_dict["NAME"], self.conn.settings_dict["TEST"]["NAME"])
            self.conn.settings_dict["NAME"] = source

        with patch("crm.test_runner.connections") as pool:
            pool.all.return_value = [self.conn]
            pool.__getitem__.return_value = self.conn
            with patch.object(DiscoverRunner, "setup_databases", side_effect=create):
                with patch.object(DiscoverRunner, "teardown_databases", side_effect=destroy):
                    old_config = runner.setup_databases(aliases={"default": False})
                    try:
                        self.assertIsNot(TransactionTestCase._fixture_teardown, original_teardown)
                    finally:
                        runner.teardown_databases(old_config)
        self.assertIs(TransactionTestCase._fixture_teardown, original_teardown)
        self.assertIsNone(self.conn.settings_dict["TEST"]["NAME"])

    def test_multiple_postgres_aliases_and_mirrors_are_rejected_before_setup(self):
        second = MagicMock(vendor="postgresql", alias="second")
        for pool_contents, mirror in (([self.conn, second], None), ([self.conn], "other")):
            self.conn.settings_dict["TEST"]["MIRROR"] = mirror
            with self.subTest(mirror=mirror), patch("crm.test_runner.connections") as pool:
                pool.all.return_value = pool_contents
                with patch.object(DiscoverRunner, "setup_databases") as create:
                    with self.assertRaises(ImproperlyConfigured):
                        DevelopmentAccessTestRunner(verbosity=0).setup_databases()
                    create.assert_not_called()

    def test_destroy_uses_owned_name_and_original_destination_despite_live_drift(self):
        class FakeConnection:
            instances = []

            def __init__(self, config, alias):
                self.settings_dict = config
                self.alias = alias
                self.close = Mock()
                self.creation = Mock()
                self._nodb_cursor = Mock()
                self.instances.append(self)

        enrolled = {**self.conn.settings_dict, "NAME": "source_db", "TEST": {"NAME": self.name}, "OPTIONS": {}}
        live = FakeConnection({**enrolled, "NAME": "source_db", "HOST": "192.0.2.1"}, "default")
        runner = DevelopmentAccessTestRunner(verbosity=0)
        runner._destroy_owned_database((live, self.name, enrolled))
        cleanup = FakeConnection.instances[-1]
        self.assertIsNot(cleanup, live)
        self.assertEqual(cleanup.settings_dict["NAME"], self.name)
        self.assertEqual(cleanup.settings_dict["HOST"], "127.0.0.1")
        cleanup.creation._destroy_test_db.assert_called_once_with(self.name, 0)
        live.creation._destroy_test_db.assert_not_called()
        cleanup.close.assert_called_once()

    def test_teardown_attempts_all_owned_drops_and_reports_survivors(self):
        runner = DevelopmentAccessTestRunner(verbosity=0)
        first = (self.conn, "test_sunjack_" + "1" * 32, {})
        second = (self.conn, "test_sunjack_" + "2" * 32, {})
        runner._pg_created = [first, second]
        with patch.object(runner, "_destroy_owned_database", side_effect=[RuntimeError("drop failed"), None]) as drop:
            with patch.object(DiscoverRunner, "teardown_databases"):
                with self.assertRaisesRegex(RuntimeError, "could not be destroyed") as raised:
                    runner.teardown_databases([])
        self.assertEqual([call.args[0] for call in drop.call_args_list], [second, first])
        self.assertEqual(runner._pg_created, [second])
        self.assertIn(second[1], raised.exception.__notes__[0])

    def test_runner_never_delegates_drifted_postgres_connection_to_native_destroy(self):
        runner = DevelopmentAccessTestRunner(verbosity=0)
        record = (self.conn, self.name, {})
        runner._pg_created = [record]
        runner._pg_test_targets = {"default": (self.conn, "source_db", self.name)}
        self.conn.settings_dict["NAME"] = "source_db"
        self.conn.vendor = "sqlite"
        with patch.object(runner, "_destroy_owned_database") as drop:
            with patch.object(DiscoverRunner, "teardown_databases") as native:
                runner.teardown_databases([(self.conn, "source_db", True)])
        drop.assert_called_once_with(record)
        native.assert_called_once_with([])


@unittest.skipUnless(connection.vendor == "postgresql", "requires real isolated PostgreSQL")
class PostgreSQLTestCleanupLifecycleTests(TransactionTestCase):
    def create_audits(self):
        user = get_user_model().objects.create_user(username="isolation-probe-user")
        preview = CSVImportPreviewAudit.objects.create(
            entity="customers", file_sha256="c" * 64, operator=user, status="ready",
        )
        batch = CSVImportBatch.objects.create(
            entity="customers", file_sha256="c" * 64, operator=user, preview=preview, status="failed",
        )
        CSVImportRowAudit.objects.create(batch=batch, row_number=2, result="failed")
        return preview.pk

    def assert_truncate_rejected(self):
        assert_truncate_guards_enabled(connection)
        for table in active_truncate_guards(connection):
            with self.subTest(table=table), self.assertRaises(DatabaseError) as error:
                with transaction.atomic():
                    with connection.cursor() as cursor:
                        cursor.execute(f'TRUNCATE TABLE "public".{connection.ops.quote_name(table)} CASCADE')
            self.assertIn("append-only", str(error.exception))

    def run_probe(self, body):
        class Probe(TransactionTestCase):
            def test_probe(inner):
                body()

        result = unittest.TestResult()
        unittest.TestSuite([Probe("test_probe")]).run(result)
        return result

    def test_three_triggers_exist_and_normal_truncate_is_rejected(self):
        self.create_audits()
        self.assert_truncate_rejected()
        self.assertEqual(CSVImportPreviewAudit.objects.count(), 1)

    def test_transaction_testcase_cleanup_empties_tables_and_restores_guards(self):
        result = self.run_probe(self.create_audits)
        self.assertTrue(result.wasSuccessful(), result.errors + result.failures)
        self.assertEqual(result.testsRun, 1)
        for model in (CSVImportPreviewAudit, CSVImportBatch, CSVImportRowAudit):
            self.assertFalse(model.objects.exists())
        self.assert_truncate_rejected()

    def test_regular_backend_flush_outside_teardown_remains_protected(self):
        with self.assertRaises(DatabaseError):
            connection.ops.execute_sql_flush(['TRUNCATE TABLE "public"."crm_csvimportpreviewaudit" CASCADE'])
        self.assert_truncate_rejected()

    def test_pre_0096_migration_cleanup_and_restore_preserve_guard_contract(self):
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        try:
            executor.migrate([("crm", "0095_merge_fulfillment_idempotency")])
            self.assertEqual(active_truncate_guards(connection), TRUNCATE_GUARDS)
            self.assert_truncate_rejected()
            result = self.run_probe(lambda: None)
            self.assertTrue(result.wasSuccessful(), result.errors + result.failures)
            self.assert_truncate_rejected()
        finally:
            MigrationExecutor(connection).migrate(latest)
        self.assertIn(REVIEW_TABLE, active_truncate_guards(connection))
        self.assert_truncate_rejected()

    def test_failure_after_truncate_rolls_back_data_and_guard_changes(self):
        preview_id = self.create_audits()
        native = connection.ops.execute_sql_flush

        def fail_after_truncate(sql):
            native(sql)
            raise RuntimeError("injected failure after native TRUNCATE")

        with patch.object(connection.ops, "execute_sql_flush", fail_after_truncate):
            result = self.run_probe(lambda: None)
        self.assertFalse(result.wasSuccessful())
        self.assertEqual(len(result.errors), 1)
        self.assertIn("injected failure after native TRUNCATE", result.errors[0][1])
        self.assertTrue(CSVImportPreviewAudit.objects.filter(pk=preview_id).exists())
        self.assertEqual(CSVImportBatch.objects.count(), 1)
        self.assertEqual(CSVImportRowAudit.objects.count(), 1)
        self.assert_truncate_rejected()

    def test_sql_error_during_cleanup_restores_guards_and_allows_retry(self):
        preview_id = self.create_audits()

        def sql_error(_sql):
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 / 0")

        with patch.object(connection.ops, "execute_sql_flush", sql_error):
            result = self.run_probe(lambda: None)
        self.assertFalse(result.wasSuccessful())
        self.assertEqual(len(result.errors), 1)
        self.assertTrue(CSVImportPreviewAudit.objects.filter(pk=preview_id).exists())
        self.assert_truncate_rejected()
        retry = self.run_probe(lambda: None)
        self.assertTrue(retry.wasSuccessful(), retry.errors + retry.failures)
        self.assertFalse(CSVImportPreviewAudit.objects.exists())
        self.assert_truncate_rejected()

    def test_other_session_cannot_use_temporarily_disabled_guards(self):
        native = connection.ops.execute_sql_flush
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_backend_pid()")
            main_pid = cursor.fetchone()[0]

        def outsider():
            close_old_connections()
            try:
                with connections["default"].cursor() as cursor:
                    cursor.execute("SET lock_timeout = '200ms'")
                    cursor.execute("SELECT pg_backend_pid()")
                    pid = cursor.fetchone()[0]
                    try:
                        cursor.execute('TRUNCATE TABLE "public"."crm_csvimportpreviewaudit" CASCADE')
                    except DatabaseError as error:
                        return pid, getattr(error.__cause__, "sqlstate", None)
                    return pid, "unexpected-success"
            finally:
                connections.close_all()

        def verify_exclusive_lock_then_flush(sql):
            with ThreadPoolExecutor(max_workers=1) as executor:
                pid, sqlstate = executor.submit(outsider).result(timeout=5)
            self.assertNotEqual(pid, main_pid)
            self.assertEqual(sqlstate, "55P03", "Other sessions must hit the exclusive lock")
            native(sql)

        with patch.object(connection.ops, "execute_sql_flush", verify_exclusive_lock_then_flush):
            result = self.run_probe(self.create_audits)
        self.assertTrue(result.wasSuccessful(), result.errors + result.failures)
        self.assert_truncate_rejected()
