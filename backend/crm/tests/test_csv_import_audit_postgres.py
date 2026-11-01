from types import SimpleNamespace
from unittest import TestCase as PlainTestCase
from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import DatabaseError, connection, transaction
from django.test import TransactionTestCase

from crm.test_runner import DevelopmentAccessTestRunner
from crm.models import CSVImportBatch, CSVImportPreviewAudit, CSVImportRowAudit


class CsvAuditTestRunnerScopeTests(PlainTestCase):
    def test_cleanup_exception_is_limited_to_generated_postgres_test_database(self):
        runner = DevelopmentAccessTestRunner()
        runner._configured_database_names = {"default": "sunjack_ci"}
        runner._test_database_names = {"default": "test_sunjack_ci"}
        runner._generated_test_databases = {"default": True}
        database = SimpleNamespace(
            alias="default",
            vendor="postgresql",
            settings_dict={"NAME": "test_sunjack_ci"},
        )

        self.assertTrue(runner._is_generated_postgres_test_database(database))

        database.settings_dict["NAME"] = "sunjack_ci"
        self.assertFalse(runner._is_generated_postgres_test_database(database))
        database.settings_dict["NAME"] = "test_sunjack_ci"
        database.vendor = "sqlite"
        self.assertFalse(runner._is_generated_postgres_test_database(database))
        database.vendor = "postgresql"
        runner._generated_test_databases["default"] = False
        self.assertFalse(runner._is_generated_postgres_test_database(database))


@skipUnless(connection.vendor == "postgresql", "requires an isolated PostgreSQL test database")
class CsvImportAuditPostgresAppendOnlyTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self._create_audit_rows()

    def _create_audit_rows(self):
        self.operator = get_user_model().objects.create_user(
            username="csv-audit-postgres-test-operator",
            password="isolated-test-only",
        )
        self.preview = CSVImportPreviewAudit.objects.create(
            entity="customers",
            file_sha256="a" * 64,
            operator=self.operator,
            status="ready",
        )
        self.batch = CSVImportBatch.objects.create(
            entity="customers",
            file_sha256="a" * 64,
            operator=self.operator,
            preview=self.preview,
            status="failed",
        )
        self.row = CSVImportRowAudit.objects.create(
            batch=self.batch,
            row_number=2,
            business_key="PG-APPEND-ONLY",
            result="failed",
            error_message="synthetic test row",
        )

    def _assert_raw_statement_is_blocked(self, sql, params=()):
        with self.assertRaises(DatabaseError) as raised:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(sql, params)
        self.assertIn("append-only", str(raised.exception).lower())

    def test_django_flush_cleans_test_rows_and_restores_truncate_guards(self):
        for _ in range(2):
            call_command(
                "flush",
                verbosity=0,
                interactive=False,
                database=connection.alias,
                reset_sequences=False,
                inhibit_post_migrate=True,
            )

            self.assertEqual(CSVImportBatch.objects.count(), 0)
            self.assertEqual(CSVImportRowAudit.objects.count(), 0)
            self.assertEqual(CSVImportPreviewAudit.objects.count(), 0)
            self._assert_raw_statement_is_blocked(
                f"TRUNCATE TABLE {connection.ops.quote_name(CSVImportBatch._meta.db_table)} CASCADE"
            )

            # Reusing the same synthetic identity after cleanup must not leave
            # duplicates or a temporarily disabled guard behind.
            self._create_audit_rows()
            self.assertEqual(CSVImportBatch.objects.filter(status="failed").count(), 1)
            self.assertEqual(
                CSVImportRowAudit.objects.filter(business_key="PG-APPEND-ONLY").count(), 1
            )
            self.assertEqual(
                CSVImportPreviewAudit.objects.filter(file_sha256="a" * 64).count(), 1
            )

    def test_raw_update_delete_and_truncate_are_rejected_for_all_audit_tables(self):
        records = (
            (CSVImportBatch, self.batch.pk),
            (CSVImportRowAudit, self.row.pk),
            (CSVImportPreviewAudit, self.preview.pk),
        )
        for model, record_id in records:
            table = connection.ops.quote_name(model._meta.db_table)
            with self.subTest(table=model._meta.db_table, operation="UPDATE"):
                self._assert_raw_statement_is_blocked(
                    f"UPDATE {table} SET id = id WHERE id = %s", [record_id]
                )
            with self.subTest(table=model._meta.db_table, operation="DELETE"):
                self._assert_raw_statement_is_blocked(
                    f"DELETE FROM {table} WHERE id = %s", [record_id]
                )
            with self.subTest(table=model._meta.db_table, operation="TRUNCATE"):
                self._assert_raw_statement_is_blocked(f"TRUNCATE TABLE {table} CASCADE")
            self.assertEqual(model.objects.filter(pk=record_id).count(), 1)
