"""Real historical model/migration probes on a disposable test database."""
from datetime import date

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class HistoricalMigrationProbes(TransactionTestCase):
    def test_0080_empty_history_and_reverse_forward_preserve_legacy_rows(self):
        executor = MigrationExecutor(connection)
        leaves = executor.loader.graph.leaf_nodes()
        try:
            executor.migrate([("crm", "0079_shared_report_template")])
            apps = executor.loader.project_state([("crm", "0079_shared_report_template")]).apps
            customer = apps.get_model("crm", "Customer").objects.create(code="M80", name="Historical customer")
            supplier = apps.get_model("crm", "Supplier").objects.create(code="M8", name="Historical supplier")
            order = apps.get_model("crm", "Order").objects.create(
                order_no="AUDIT-80", customer=customer, order_date=date(2026, 11, 3), status="confirmed")
            purchase = apps.get_model("crm", "PurchaseOrder").objects.create(
                purchase_no="AUDIT-80", supplier=supplier, order_date=date(2026, 11, 3), status="ordered")
            before_order = apps.get_model("crm", "Order").objects.values().get(pk=order.pk)
            before_purchase = apps.get_model("crm", "PurchaseOrder").objects.values().get(pk=purchase.pk)
            for cycle in range(2):
                executor = MigrationExecutor(connection)
                executor.migrate([("crm", "0080_formal_party_snapshots")])
                apps80 = executor.loader.project_state([("crm", "0080_formal_party_snapshots")]).apps
                after_order = apps80.get_model("crm", "Order").objects.values().get(pk=order.pk)
                after_purchase = apps80.get_model("crm", "PurchaseOrder").objects.values().get(pk=purchase.pk)
                self.assertEqual({k: after_order[k] for k in before_order}, before_order)
                self.assertEqual({k: after_purchase[k] for k in before_purchase}, before_purchase)
                for key in after_order.keys() - before_order.keys():
                    self.assertEqual(after_order[key], "")
                for key in after_purchase.keys() - before_purchase.keys():
                    self.assertEqual(after_purchase[key], "")
                print("MIGRATION_0080_CYCLE_PASS", cycle, "all legacy columns equal; new party fields empty")
                if cycle == 0:
                    MigrationExecutor(connection).migrate([("crm", "0079_shared_report_template")])
        finally:
            MigrationExecutor(connection).migrate(leaves)

    def test_0012_backfills_current_master_without_historical_provenance(self):
        executor = MigrationExecutor(connection)
        leaves = executor.loader.graph.leaf_nodes()
        try:
            executor.migrate([("crm", "0011_quote_pi_fields_and_sku_image")])
            apps = executor.loader.project_state([("crm", "0011_quote_pi_fields_and_sku_image")]).apps
            customer = apps.get_model("crm", "Customer").objects.create(code="M12", name="ORIGINAL NAME")
            quote = apps.get_model("crm", "Quote").objects.create(
                quote_no="AUDIT-M12", customer=customer, quote_date=date(2026, 1, 1), status="sent")
            apps.get_model("crm", "Customer").objects.filter(pk=customer.pk).update(name="CURRENT AT MIGRATION")
            executor = MigrationExecutor(connection)
            executor.migrate([("crm", "0012_quote_saved_pi_snapshots")])
            apps12 = executor.loader.project_state([("crm", "0012_quote_saved_pi_snapshots")]).apps
            row = apps12.get_model("crm", "Quote").objects.get(pk=quote.pk)
            self.assertEqual(row.buyer_company_name, "CURRENT AT MIGRATION")
            print("GAP_MIGRATION_0012_PROVENANCE", row.buyer_company_name)
        finally:
            MigrationExecutor(connection).migrate(leaves)
