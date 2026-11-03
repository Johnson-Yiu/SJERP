from datetime import date

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class QuoteTemplateMigrationTests(TransactionTestCase):
    def test_forward_and_reverse_preserve_historical_quote(self):
        executor = MigrationExecutor(connection)
        old = [("crm", "0095_merge_fulfillment_idempotency")]
        new = [("crm", "0096_quote_pi_template_snapshots")]
        executor.migrate(old)
        state = executor.loader.project_state(old).apps
        customer = state.get_model("crm", "Customer").objects.create(
            code="MIGRATION-SYNTH", name="Synthetic old buyer", country="Germany"
        )
        quote = state.get_model("crm", "Quote").objects.create(
            quote_no="MIGRATION-SYNTH", customer_id=customer.pk,
            quote_date=date(2025, 1, 1), buyer_company_name="Historical buyer",
        )
        try:
            executor = MigrationExecutor(connection)
            executor.migrate(new)
            updated = executor.loader.project_state(new).apps.get_model("crm", "Quote").objects.get(pk=quote.pk)
            self.assertEqual(updated.pi_template_snapshots, {})
            self.assertEqual(updated.buyer_company_name, "Historical buyer")
            executor = MigrationExecutor(connection)
            executor.migrate(old)
            restored = executor.loader.project_state(old).apps.get_model("crm", "Quote").objects.get(pk=quote.pk)
            self.assertEqual(restored.buyer_company_name, "Historical buyer")
        finally:
            executor = MigrationExecutor(connection)
            executor.migrate(executor.loader.graph.leaf_nodes())
