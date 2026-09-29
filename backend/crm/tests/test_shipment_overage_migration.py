from datetime import date

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


MIGRATION_0069 = [("crm", "0069_backfill_purchase_cost_allocations")]
MIGRATION_0070 = [("crm", "0070_shipmentitem_overage_reversal_links")]


class ShipmentOverageLinkMigrationTests(TransactionTestCase):
    """Exercise 0070 against the real pre-migration schema and data."""

    reset_sequences = True

    def setUp(self):
        super().setUp()
        self.executor = MigrationExecutor(connection)
        self.executor.migrate(MIGRATION_0069)
        self.apps = self.executor.loader.project_state(MIGRATION_0069).apps

    def tearDown(self):
        self.executor.loader.build_graph()
        self.executor.migrate(self.executor.loader.graph.leaf_nodes())
        super().tearDown()

    def make_shipment(self, suffix, *, customer_addon=False, duplicate_plans=False):
        Customer = self.apps.get_model("crm", "Customer")
        Product = self.apps.get_model("crm", "Product")
        SKU = self.apps.get_model("crm", "SKU")
        Order = self.apps.get_model("crm", "Order")
        OrderItem = self.apps.get_model("crm", "OrderItem")
        Shipment = self.apps.get_model("crm", "Shipment")
        ShipmentItem = self.apps.get_model("crm", "ShipmentItem")
        PaymentPlan = self.apps.get_model("crm", "PaymentPlan")

        customer = Customer.objects.create(code=f"MC{suffix}", name=f"Migration customer {suffix}")
        product = Product.objects.create(code=f"MP{suffix}", name=f"Migration product {suffix}")
        sku = SKU.objects.create(sku=f"MSKU-{suffix}", product=product)
        order = Order.objects.create(order_no=f"SO-MIG-{suffix}", customer=customer, order_date=date(2032, 1, 1))
        source = OrderItem.objects.create(order=order, sku=sku, quantity=10, unit_price=5)
        supplement = OrderItem.objects.create(order=order, sku=sku, quantity=2, unit_price=5)
        shipment = Shipment.objects.create(
            shipment_no=f"SH-MIG-{suffix}", order=order, shipment_date=date(2032, 1, 2), status="confirmed"
        )
        normal = ShipmentItem.objects.create(shipment=shipment, order_item=source, sku=sku, quantity=10)
        overage = ShipmentItem.objects.create(
            shipment=shipment,
            order_item=supplement,
            sku=sku,
            quantity=2,
            is_overage=True,
            overage_reason="customer_addon" if customer_addon else "gift_or_sample",
            creates_supplement=True,
        )
        plans = []
        if customer_addon:
            plans.append(PaymentPlan.objects.create(
                order=order,
                direction="receivable",
                currency="USD",
                planned_amount=10,
                notes=f"发货单 {shipment.shipment_no} 客户追加",
            ))
            if duplicate_plans:
                plans.append(PaymentPlan.objects.create(
                    order=order,
                    direction="receivable",
                    currency="USD",
                    planned_amount=20,
                    notes=f"发货单 {shipment.shipment_no} 客户追加",
                ))
        return normal, overage, source, plans

    def test_backfills_only_unambiguous_historical_overage_links(self):
        normal, unique_addon, source, unique_plans = self.make_shipment("A", customer_addon=True)
        _, ambiguous_addon, _, ambiguous_plans = self.make_shipment("B", customer_addon=True, duplicate_plans=True)

        self.executor = MigrationExecutor(connection)
        self.executor.migrate(MIGRATION_0070)
        apps = self.executor.loader.project_state(MIGRATION_0070).apps
        ShipmentItem = apps.get_model("crm", "ShipmentItem")

        migrated_unique = ShipmentItem.objects.get(pk=unique_addon.pk)
        migrated_ambiguous = ShipmentItem.objects.get(pk=ambiguous_addon.pk)
        migrated_normal = ShipmentItem.objects.get(pk=normal.pk)
        self.assertEqual(migrated_unique.source_order_item_id, source.pk)
        self.assertEqual(migrated_unique.generated_payment_plan_id, unique_plans[0].pk)
        self.assertIsNone(migrated_ambiguous.generated_payment_plan_id)
        self.assertEqual(len(ambiguous_plans), 2)
        self.assertIsNone(migrated_normal.source_order_item_id)
        self.assertIsNone(migrated_normal.generated_payment_plan_id)
