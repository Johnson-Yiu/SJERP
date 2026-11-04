from django.contrib.auth import get_user_model
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.recorder import MigrationRecorder
from django.test import TransactionTestCase

from crm.models import CSVImportBatch, CSVImportPreviewAudit, CSVImportRowAudit


class CsvImportAuditMigrationRollbackTests(TransactionTestCase):
    reset_sequences = True
    guard_migration = ("crm", "0094_csv_import_audit_truncate_guard")
    parent_migration = ("crm", "0093_csv_import_preview_audit")

    def _migrate_to_latest(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())

    def test_reverse_is_refused_while_any_audit_history_exists(self):
        latest = MigrationExecutor(connection).loader.graph.leaf_nodes()
        operator = get_user_model().objects.create_user(
            username="csv-audit-rollback-operator",
            password="isolated-test-only",
        )
        preview = CSVImportPreviewAudit.objects.create(
            entity="customers",
            file_sha256="b" * 64,
            operator=operator,
            status="ready",
        )
        batch = CSVImportBatch.objects.create(
            entity="customers",
            file_sha256="b" * 64,
            operator=operator,
            preview=preview,
            status="failed",
        )
        row = CSVImportRowAudit.objects.create(
            batch=batch,
            row_number=2,
            business_key="ROLLBACK-GUARD",
            result="failed",
        )

        executor = MigrationExecutor(connection)
        latest_targets = tuple(executor.loader.graph.leaf_nodes())
        try:
            with self.assertRaisesRegex(RuntimeError, "Refusing to reverse CSV import audit protection"):
                executor.migrate([self.parent_migration])

            self.assertIn(self.guard_migration, MigrationRecorder(connection).applied_migrations())
            self.assertTrue(CSVImportPreviewAudit.objects.filter(pk=preview.pk).exists())
            self.assertTrue(CSVImportBatch.objects.filter(pk=batch.pk).exists())
            self.assertTrue(CSVImportRowAudit.objects.filter(pk=row.pk).exists())
        finally:
            # MigrationExecutor commits each successfully reversed migration
            # before reaching 0094's refusal, so restore the full graph even
            # when the expected refusal occurs partway through the rollback.
            MigrationExecutor(connection).migrate(latest_targets)

        self.assertTrue(set(latest_targets).issubset(MigrationRecorder(connection).applied_migrations()))
        self.assertIn(self.guard_migration, MigrationRecorder(connection).applied_migrations())
        self.assertIn("crm_historytakeoverapplication", connection.introspection.table_names())

    def test_empty_audit_tables_allow_reverse_and_forward_migration(self):
        self.assertFalse(CSVImportPreviewAudit.objects.exists())
        self.assertFalse(CSVImportBatch.objects.exists())
        self.assertFalse(CSVImportRowAudit.objects.exists())
        try:
            executor = MigrationExecutor(connection)
            executor.migrate([self.parent_migration])
            self.assertNotIn(self.guard_migration, MigrationRecorder(connection).applied_migrations())
        finally:
            self._migrate_to_latest()
        self.assertIn(self.guard_migration, MigrationRecorder(connection).applied_migrations())

    def test_empty_audit_schema_can_be_removed_and_rebuilt(self):
        tables = {model._meta.db_table for model in (
            CSVImportBatch, CSVImportRowAudit, CSVImportPreviewAudit,
        )}
        self.assertFalse(CSVImportBatch.objects.exists())
        self.assertFalse(CSVImportRowAudit.objects.exists())
        self.assertFalse(CSVImportPreviewAudit.objects.exists())
        try:
            executor = MigrationExecutor(connection)
            executor.migrate([("crm", "0089_operationlog_operator_protect")])
            self.assertTrue(tables.isdisjoint(connection.introspection.table_names()))
            applied = MigrationRecorder(connection).applied_migrations()
            for migration in (
                "0091_csv_import_audit", "0092_merge_fulfillment_and_csv_audit",
                "0093_csv_import_preview_audit", "0094_csv_import_audit_truncate_guard",
            ):
                self.assertNotIn(("crm", migration), applied)
        finally:
            self._migrate_to_latest()
        self.assertTrue(tables.issubset(connection.introspection.table_names()))
        self.assertIn(self.guard_migration, MigrationRecorder(connection).applied_migrations())
        self.assertFalse(CSVImportBatch.objects.exists())
        self.assertFalse(CSVImportRowAudit.objects.exists())
        self.assertFalse(CSVImportPreviewAudit.objects.exists())
