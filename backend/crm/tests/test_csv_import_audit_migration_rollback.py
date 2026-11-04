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
        finally:
            # Earlier reverse steps may have committed before the audit guard
            # refuses its own reversal. Restore the entire current schema.
            MigrationExecutor(connection).migrate(latest_targets)

        self.assertTrue(set(latest_targets).issubset(MigrationRecorder(connection).applied_migrations()))
        self.assertIn(self.guard_migration, MigrationRecorder(connection).applied_migrations())
        self.assertTrue(CSVImportPreviewAudit.objects.filter(pk=preview.pk).exists())
        self.assertTrue(CSVImportBatch.objects.filter(pk=batch.pk).exists())
        self.assertTrue(CSVImportRowAudit.objects.filter(pk=row.pk).exists())

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
