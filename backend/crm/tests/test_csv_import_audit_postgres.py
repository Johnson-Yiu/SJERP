from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.db import DatabaseError, connection, transaction
from django.test import TransactionTestCase

from crm.models import CSVImportBatch, CSVImportPreviewAudit, CSVImportRowAudit


AUDIT_TABLES = (
    (CSVImportBatch, "crm_csvimportbatch_truncate_guard"),
    (CSVImportRowAudit, "crm_csvimportrowaudit_truncate_guard"),
    (CSVImportPreviewAudit, "crm_csvimportpreviewaudit_truncate_guard"),
)


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

    def _assert_original_records_preserved(self):
        for model, record_id in (
            (CSVImportBatch, self.batch.pk),
            (CSVImportRowAudit, self.row.pk),
            (CSVImportPreviewAudit, self.preview.pk),
        ):
            self.assertEqual(model.objects.filter(pk=record_id).count(), 1)

    def _assert_truncate_guard_is_installed(self, model, trigger_name):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM pg_trigger
                WHERE tgrelid = %s::regclass
                  AND tgname = %s
                  AND NOT tgisinternal
                """,
                [model._meta.db_table, trigger_name],
            )
            self.assertEqual(cursor.fetchone()[0], 1)

    def test_raw_update_and_delete_are_rejected_for_all_audit_tables(self):
        for model, _trigger_name in AUDIT_TABLES:
            record_id = {
                CSVImportBatch: self.batch.pk,
                CSVImportRowAudit: self.row.pk,
                CSVImportPreviewAudit: self.preview.pk,
            }[model]
            table = connection.ops.quote_name(model._meta.db_table)
            with self.subTest(table=model._meta.db_table, operation="UPDATE"):
                self._assert_raw_statement_is_blocked(
                    f"UPDATE {table} SET id = id WHERE id = %s", [record_id]
                )
            with self.subTest(table=model._meta.db_table, operation="DELETE"):
                self._assert_raw_statement_is_blocked(
                    f"DELETE FROM {table} WHERE id = %s", [record_id]
                )
            self.assertEqual(model.objects.filter(pk=record_id).count(), 1)

    def test_truncate_is_rejected_for_each_audit_table_and_preserves_all_rows(self):
        for model, trigger_name in AUDIT_TABLES:
            table = connection.ops.quote_name(model._meta.db_table)
            with self.subTest(table=model._meta.db_table):
                self._assert_truncate_guard_is_installed(model, trigger_name)
                # CASCADE satisfies PostgreSQL's audit-table FK graph so the
                # migration 0094 statement trigger, not an FK check, rejects it.
                self._assert_raw_statement_is_blocked(
                    f"TRUNCATE TABLE {table} CASCADE"
                )
                self._assert_original_records_preserved()
