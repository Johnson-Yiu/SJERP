from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.db import DatabaseError, connection, transaction
from django.test import TransactionTestCase

from crm.models import CSVImportBatch, CSVImportPreviewAudit, CSVImportRowAudit


@skipUnless(connection.vendor == "postgresql", "requires an isolated PostgreSQL test database")
class CsvImportAuditPostgresAppendOnlyTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
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
                self._assert_raw_statement_is_blocked(f"TRUNCATE TABLE {table}")
            self.assertEqual(model.objects.filter(pk=record_id).count(), 1)
