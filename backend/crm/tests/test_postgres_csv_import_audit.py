import unittest
from unittest.mock import MagicMock, Mock

from django.contrib.auth import get_user_model
from django.db import DatabaseError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase

from crm.models import CSVImportBatch, CSVImportRowAudit
from crm.test_runner import guarded_csv_audit_flush_sql


class CSVImportAuditTestFlushSQLTests(unittest.TestCase):
    def test_postgres_flush_temporarily_disables_only_installed_guards(self):
        db_connection = MagicMock()
        db_connection.vendor = "postgresql"
        db_connection.ops.quote_name.side_effect = lambda identifier: f'"{identifier}"'
        cursor = db_connection.cursor.return_value.__enter__.return_value
        cursor.fetchall.return_value = [("crm_csv_import_batch_truncate_guard",)]
        original_sql_flush = Mock(return_value=["TRUNCATE crm_csvimportbatch;"])

        statements = guarded_csv_audit_flush_sql(
            db_connection,
            original_sql_flush,
            style=None,
            tables=["crm_csvimportbatch", "crm_csvimportrowaudit"],
            reset_sequences=True,
            allow_cascade=True,
        )

        self.assertEqual(
            statements,
            [
                'ALTER TABLE "crm_csvimportbatch" DISABLE TRIGGER "crm_csv_import_batch_truncate_guard";',
                "TRUNCATE crm_csvimportbatch;",
                'ALTER TABLE "crm_csvimportbatch" ENABLE TRIGGER "crm_csv_import_batch_truncate_guard";',
            ],
        )
        cursor.execute.assert_called_once()
        original_sql_flush.assert_called_once_with(
            None,
            ["crm_csvimportbatch", "crm_csvimportrowaudit"],
            reset_sequences=True,
            allow_cascade=True,
        )


class CSVImportAuditTruncateMigrationTests(TransactionTestCase):
    """The forward and reverse guard migration must preserve existing history."""

    def test_forward_and_reverse_migration_preserve_existing_audit_rows(self):
        operator = get_user_model().objects.create_user(username="csv-migration-audit")
        batch = CSVImportBatch.objects.create(
            entity="customers",
            file_sha256="a" * 64,
            operator=operator,
            status="succeeded",
            total_rows=1,
            created_rows=1,
        )
        row = CSVImportRowAudit.objects.create(
            batch=batch,
            row_number=2,
            business_key="MIGRATION-PRESERVE",
            result="created",
            after_data={"code": "MIGRATION-PRESERVE"},
        )
        batch_before = dict(
            CSVImportBatch.objects.filter(pk=batch.pk).values(
                "id", "batch_id", "entity", "file_sha256", "status", "total_rows", "created_rows", "failed_rows", "failure_reason"
            ).get()
        )
        row_before = dict(
            CSVImportRowAudit.objects.filter(pk=row.pk).values(
                "id", "batch_id", "row_number", "business_key", "result", "before_data", "after_data", "error_message"
            ).get()
        )

        try:
            MigrationExecutor(connection).migrate([("crm", "0092_merge_fulfillment_and_csv_audit")])
            self.assertEqual(
                dict(CSVImportBatch.objects.filter(pk=batch.pk).values(*batch_before.keys()).get()),
                batch_before,
            )
            self.assertEqual(
                dict(CSVImportRowAudit.objects.filter(pk=row.pk).values(*row_before.keys()).get()),
                row_before,
            )

            MigrationExecutor(connection).migrate([("crm", "0093_csv_import_audit_truncate_guard")])
            self.assertEqual(
                dict(CSVImportBatch.objects.filter(pk=batch.pk).values(*batch_before.keys()).get()),
                batch_before,
            )
            self.assertEqual(
                dict(CSVImportRowAudit.objects.filter(pk=row.pk).values(*row_before.keys()).get()),
                row_before,
            )
        finally:
            # Keep the test database at the migration leaf even if an assertion fails.
            MigrationExecutor(connection).migrate([("crm", "0093_csv_import_audit_truncate_guard")])


@unittest.skipUnless(connection.vendor == "postgresql", "PostgreSQL CSV audit trigger tests require PostgreSQL")
class PostgreSQLCSVImportAuditAppendOnlyTests(TestCase):
    def setUp(self):
        operator = get_user_model().objects.create_user(username="pg-csv-audit-operator")
        # Keep a batch with no child rows so its raw DELETE is not rejected by a
        # foreign-key constraint instead of the append-only trigger.
        self.batch_without_rows = CSVImportBatch.objects.create(
            entity="customers",
            file_sha256="b" * 64,
            operator=operator,
            status="succeeded",
        )
        self.batch_with_row = CSVImportBatch.objects.create(
            entity="customers",
            file_sha256="c" * 64,
            operator=operator,
            status="succeeded",
            total_rows=1,
            created_rows=1,
        )
        self.row = CSVImportRowAudit.objects.create(
            batch=self.batch_with_row,
            row_number=2,
            business_key="PG-APPEND-ONLY",
            result="created",
            after_data={"code": "PG-APPEND-ONLY"},
        )

    def assert_trigger_rejects(self, sql, params=None):
        with self.assertRaises(DatabaseError) as raised:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(sql, params)
        cause = raised.exception.__cause__
        sqlstate = getattr(cause, "sqlstate", None) or getattr(cause, "pgcode", None)
        self.assertEqual(sqlstate, "42501", "The statement must be rejected by the append-only trigger, not another constraint.")

    def test_raw_update_of_batch_is_rejected(self):
        table = connection.ops.quote_name(CSVImportBatch._meta.db_table)
        self.assert_trigger_rejects(
            f"UPDATE {table} SET failure_reason = %s WHERE id = %s",
            ["tampered", self.batch_without_rows.pk],
        )
        self.assertEqual(CSVImportBatch.objects.get(pk=self.batch_without_rows.pk).failure_reason, "")

    def test_raw_delete_of_batch_is_rejected(self):
        table = connection.ops.quote_name(CSVImportBatch._meta.db_table)
        self.assert_trigger_rejects(f"DELETE FROM {table} WHERE id = %s", [self.batch_without_rows.pk])
        self.assertTrue(CSVImportBatch.objects.filter(pk=self.batch_without_rows.pk).exists())

    def test_raw_update_of_row_audit_is_rejected(self):
        table = connection.ops.quote_name(CSVImportRowAudit._meta.db_table)
        self.assert_trigger_rejects(
            f"UPDATE {table} SET business_key = %s WHERE id = %s",
            ["tampered", self.row.pk],
        )
        self.assertEqual(CSVImportRowAudit.objects.get(pk=self.row.pk).business_key, "PG-APPEND-ONLY")

    def test_raw_delete_of_row_audit_is_rejected(self):
        table = connection.ops.quote_name(CSVImportRowAudit._meta.db_table)
        self.assert_trigger_rejects(f"DELETE FROM {table} WHERE id = %s", [self.row.pk])
        self.assertTrue(CSVImportRowAudit.objects.filter(pk=self.row.pk).exists())

    def test_raw_truncate_of_batch_is_rejected_by_batch_guard(self):
        batch_table = connection.ops.quote_name(CSVImportBatch._meta.db_table)
        row_table = connection.ops.quote_name(CSVImportRowAudit._meta.db_table)
        row_trigger = connection.ops.quote_name("crm_csv_import_row_audit_truncate_guard")

        # TRUNCATE CASCADE must include the referencing row table. Temporarily
        # disable its guard inside a rolled-back DDL transaction so this test
        # proves the batch table's own statement trigger rejects the operation.
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(f"ALTER TABLE {row_table} DISABLE TRIGGER {row_trigger}")
            self.assert_trigger_rejects(f"TRUNCATE TABLE {batch_table} CASCADE")
            with connection.cursor() as cursor:
                cursor.execute(f"ALTER TABLE {row_table} ENABLE TRIGGER {row_trigger}")

        self.assertEqual(CSVImportBatch.objects.count(), 2)
        self.assertEqual(CSVImportRowAudit.objects.count(), 1)

    def test_raw_truncate_of_row_audit_is_rejected(self):
        table = connection.ops.quote_name(CSVImportRowAudit._meta.db_table)
        self.assert_trigger_rejects(f"TRUNCATE TABLE {table}")
        self.assertTrue(CSVImportRowAudit.objects.filter(pk=self.row.pk).exists())
