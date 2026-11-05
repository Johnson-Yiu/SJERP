from datetime import date

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class PartyVersionMigrationProtectionTests(TransactionTestCase):
    def test_country_snapshot_blocks_cross_migration_partial_downgrade(self):
        before_version = [('crm', '0109_quote_buyer_country_snapshot')]
        current_version = [('crm', '0110_party_version')]
        executor = MigrationExecutor(connection)
        executor.migrate(before_version)
        apps = executor.loader.project_state(before_version).apps
        Customer = apps.get_model('crm', 'Customer')
        Quote = apps.get_model('crm', 'Quote')
        customer = Customer.objects.create(code='PV-MIG-C', name='Synthetic buyer')
        quote = Quote.objects.create(quote_no='PV-MIG-Q', customer_id=customer.pk,
                                     quote_date=date(2026, 11, 5), buyer_country_snapshot='Germany')
        try:
            MigrationExecutor(connection).migrate(current_version)
            with self.assertRaisesMessage(RuntimeError, '拒绝回退'):
                MigrationExecutor(connection).migrate([('crm', '0108_history_append_only_truncate')])
            executor = MigrationExecutor(connection)
            self.assertIn(('crm', '0110_party_version'), executor.loader.applied_migrations)
            self.assertIn(('crm', '0109_quote_buyer_country_snapshot'), executor.loader.applied_migrations)
            state = executor.loader.project_state(current_version).apps
            self.assertEqual(state.get_model('crm', 'Quote').objects.get(pk=quote.pk).buyer_country_snapshot, 'Germany')
        finally:
            MigrationExecutor(connection).migrate(MigrationExecutor(connection).loader.graph.leaf_nodes())
