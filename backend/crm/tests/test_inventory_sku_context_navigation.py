from datetime import date

from django.test import TestCase
from rest_framework.test import APIClient

from crm.models import (
    Customer,
    InventoryMovement,
    Order,
    Product,
    PurchaseOrder,
    SKU,
    Shipment,
    ShipmentItem,
    Supplier,
)


class InventorySkuContextNavigationApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.day = date(2026, 10, 5)
        self.customer = Customer.objects.create(code="P2C3-C", name="PCR-010 Buyer")
        self.focus_supplier = Supplier.objects.create(code="P2", name="PCR-010 Focus Supplier")
        self.other_supplier = Supplier.objects.create(code="P3", name="PCR-010 Other Supplier")
        product = Product.objects.create(code="P2C3-P", name="PCR-010 Product")
        self.sku = SKU.objects.create(sku="P2C3-SKU", product=product)
        self.other_sku = SKU.objects.create(sku="P2C3-OTHER", product=product)
        self.order = Order.objects.create(
            order_no="SO-P2C3-001", customer=self.customer, order_date=self.day, status="confirmed"
        )
        self.order_item = self.order.items.create(sku=self.sku, quantity=5, unit_price=10)

    def make_purchase(self, suffix, *, supplier=None, status="ordered", skus=None):
        purchase = PurchaseOrder.objects.create(
            purchase_no=f"PO-P2C3-{suffix}", supplier=supplier or self.focus_supplier,
            order_date=self.day, status=status,
        )
        for sku in skus if skus is not None else [self.sku]:
            purchase.items.create(sku=sku, quantity=2, unit_price=3)
        return purchase

    def purchase_ids(self, **params):
        response = self.client.get("/api/purchase-orders/", params)
        self.assertEqual(response.status_code, 200, response.data)
        data = response.data.get("results", response.data)
        return [row["id"] for row in data]

    def test_sku_filter_includes_matches_excludes_non_matches_and_deduplicates_multi_line_purchase(self):
        matched = self.make_purchase("MULTI", skus=[self.sku, self.sku])
        unrelated = self.make_purchase("OTHER", skus=[self.other_sku])

        ids = self.purchase_ids(sku=self.sku.id)

        self.assertEqual(ids, [matched.id])
        self.assertNotIn(unrelated.id, ids)

    def test_sku_filter_combines_with_status_and_pending_receipt(self):
        ordered = self.make_purchase("ORDERED", status="ordered")
        partial = self.make_purchase("PARTIAL", status="partial")
        completed = self.make_purchase("COMPLETE", status="completed")

        self.assertEqual(self.purchase_ids(sku=self.sku.id, status="partial"), [partial.id])
        self.assertEqual(
            set(self.purchase_ids(sku=self.sku.id, pending_receipt="1")),
            {ordered.id, partial.id},
        )
        self.assertEqual(
            self.purchase_ids(sku=self.sku.id, status="partial", pending_receipt="1"),
            [partial.id],
        )
        self.assertNotIn(completed.id, self.purchase_ids(sku=self.sku.id, pending_receipt="1"))

    def test_sku_filter_combines_with_search(self):
        matched = self.make_purchase("SEARCH-FOCUS", supplier=self.focus_supplier)
        other_supplier_match = self.make_purchase("SEARCH-OTHER", supplier=self.other_supplier)
        unrelated_sku = self.make_purchase("SEARCH-NOSKU", skus=[self.other_sku])

        self.assertEqual(
            self.purchase_ids(sku=self.sku.id, search="Focus Supplier"),
            [matched.id],
        )
        self.assertNotIn(other_supplier_match.id, self.purchase_ids(sku=self.sku.id, search="Focus Supplier"))
        self.assertNotIn(unrelated_sku.id, self.purchase_ids(sku=self.sku.id, search="Focus Supplier"))

    def test_inventory_detail_keeps_record_ids_needed_for_context_navigation(self):
        purchase = self.make_purchase("DETAIL")
        movement = InventoryMovement.objects.create(
            movement_no="IM-P2C3-001", movement_date=self.day, type="adjust_in",
            sku=self.sku, quantity=2,
        )
        shipment = Shipment.objects.create(
            shipment_no="SH-P2C3-001", order=self.order, shipment_date=self.day, status="draft",
        )
        ShipmentItem.objects.create(
            shipment=shipment, order_item=self.order_item, sku=self.sku, quantity=1,
        )

        response = self.client.get(f"/api/skus/{self.sku.id}/inventory-detail/")

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual([row["id"] for row in response.data["purchases"]], [purchase.id])
        self.assertEqual([row["id"] for row in response.data["orders"]], [self.order.id])
        self.assertEqual([row["id"] for row in response.data["movements"]], [movement.id])
        self.assertEqual(response.data["shipments"][0]["order"], self.order.id)
