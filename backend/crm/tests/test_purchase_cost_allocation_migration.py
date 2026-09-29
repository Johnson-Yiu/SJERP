from datetime import date

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


MIGRATION_0068 = [("crm", "0068_documentnumbersequence")]
MIGRATION_0069 = [("crm", "0069_backfill_purchase_cost_allocations")]


class PurchaseCostAllocationMigrationTests(TransactionTestCase):
    """Exercise the data migration against the actual historical app state."""

    reset_sequences = True

    def setUp(self):
        super().setUp()
        self.executor = MigrationExecutor(connection)
        self.executor.migrate(MIGRATION_0068)
        self.apps = self.executor.loader.project_state(MIGRATION_0068).apps

    def tearDown(self):
        self.executor.loader.build_graph()
        self.executor.migrate(self.executor.loader.graph.leaf_nodes())
        super().tearDown()

    def make_purchase(self, *, order=True, version=0):
        Customer = self.apps.get_model("crm", "Customer")
        Supplier = self.apps.get_model("crm", "Supplier")
        Product = self.apps.get_model("crm", "Product")
        SKU = self.apps.get_model("crm", "SKU")
        Order = self.apps.get_model("crm", "Order")
        PurchaseOrder = self.apps.get_model("crm", "PurchaseOrder")
        PurchaseOrderItem = self.apps.get_model("crm", "PurchaseOrderItem")
        suffix = str(PurchaseOrder.objects.count() + 1)
        customer = Customer.objects.create(code=f"MC{suffix}", name=f"Migration Customer {suffix}")
        supplier = Supplier.objects.create(code=f"M{suffix}", name=f"Migration Supplier {suffix}")
        product = Product.objects.create(code=f"MP{suffix}", name=f"Migration Product {suffix}")
        sku = SKU.objects.create(sku=f"MSKU-{suffix}", product=product)
        sales_order = Order.objects.create(order_no=f"SO-MIG-{suffix}", customer=customer, order_date=date(2031, 1, 1)) if order else None
        purchase = PurchaseOrder.objects.create(purchase_no=f"PO-MIG-{suffix}", supplier=supplier, order=sales_order, order_date=date(2031, 1, 1), cost_allocation_version=version)
        item = PurchaseOrderItem.objects.create(purchase_order=purchase, sku=sku, quantity=100, unit_price=2)
        return purchase, item, sales_order

    def test_backfill_historical_default_and_existing_allocations(self):
        Allocation = self.apps.get_model("crm", "PurchaseCostAllocation")
        order_purchase, order_item, order = self.make_purchase(order=True)
        inventory_purchase, inventory_item, _ = self.make_purchase(order=False)
        manual_purchase, manual_item, manual_order = self.make_purchase(order=True, version=1)
        Allocation.objects.create(purchase_item=manual_item, target_type="order", order=manual_order, quantity=60)
        Allocation.objects.create(purchase_item=manual_item, target_type="inventory", quantity=40)
        retained_purchase, retained_item, retained_order = self.make_purchase(order=True)
        Allocation.objects.create(purchase_item=retained_item, target_type="order", order=retained_order, quantity=60)
        Allocation.objects.create(purchase_item=retained_item, target_type="inventory", quantity=40)

        self.executor = MigrationExecutor(connection)
        self.executor.migrate(MIGRATION_0069)
        apps = self.executor.loader.project_state(MIGRATION_0069).apps
        NewAllocation = apps.get_model("crm", "PurchaseCostAllocation")
        NewPurchase = apps.get_model("crm", "PurchaseOrder")
        self.assertEqual(list(NewAllocation.objects.filter(purchase_item_id=order_item.id).values_list("target_type", "order_id", "quantity")), [("order", order.id, 100)])
        self.assertEqual(list(NewAllocation.objects.filter(purchase_item_id=inventory_item.id).values_list("target_type", "order_id", "quantity")), [("inventory", None, 100)])
        self.assertEqual(
            list(NewAllocation.objects.filter(purchase_item_id=manual_item.id).values_list("target_type", "order_id", "quantity")),
            [("order", manual_order.id, 60), ("inventory", None, 40)],
        )
        self.assertEqual(
            list(NewAllocation.objects.filter(purchase_item_id=retained_item.id).values_list("target_type", "order_id", "quantity")),
            [("order", retained_order.id, 60), ("inventory", None, 40)],
        )
        self.assertEqual(NewPurchase.objects.get(pk=order_purchase.id).cost_allocation_version, 0)

