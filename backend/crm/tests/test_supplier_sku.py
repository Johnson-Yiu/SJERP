from datetime import date
from decimal import Decimal

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from crm.models import Customer, InventoryMovement, Order, Product, PurchaseOrder, PurchaseOrderItem, SKU, Supplier, SupplierSKU
from crm.services.fulfillment import record_receipt


class SupplierSKUApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        customer = Customer.objects.create(code="C-SUPPLIER-SKU", name="Supplier SKU Buyer")
        self.product = Product.objects.create(code="P-SUPPLIER-SKU", name="Supplier SKU Product")
        self.sku = SKU.objects.create(product=self.product, sku="SKU-SUPPLIER-SKU", display_name_cn="内部灯具")
        self.order = Order.objects.create(order_no="SO-SUPPLIER-SKU", customer=customer, order_date=date(2026, 8, 23))
        self.supplier_a = Supplier.objects.create(name="供应商 A", code="SA")
        self.supplier_b = Supplier.objects.create(name="供应商 B", code="SB")

    def source_payload(self, supplier=None, **overrides):
        payload = {
            "supplier": (supplier or self.supplier_a).id,
            "sku": self.sku.id,
            "supplier_model": "SUP-A-24V",
            "supplier_product_name": "供应商产品名称",
            "supplier_sku_code": "A-24V-BLACK",
            "supplier_barcode": "690000000001",
            "purchase_price": "2.5000",
            "currency": "USD",
            "moq": "10",
            "lead_time_days": 12,
            "is_active": True,
            "is_preferred": False,
            "remarks": "英文说明书批次由供应商编码区分",
        }
        payload.update(overrides)
        return payload

    def create_source(self, supplier=None, **overrides):
        response = self.client.post("/api/supplier-skus/", self.source_payload(supplier, **overrides), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        return SupplierSKU.objects.get(pk=response.data["id"])

    def test_one_internal_sku_can_have_many_supplier_sources(self):
        first = self.create_source()
        second = self.create_source(self.supplier_b, supplier_sku_code="B-24V-BLACK")

        self.assertEqual(SupplierSKU.objects.filter(sku=self.sku).count(), 2)
        response = self.client.get("/api/supplier-skus/", {"sku": self.sku.id, "is_active": "1"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        rows = response.data["results"]
        self.assertEqual({row["id"] for row in rows}, {first.id, second.id})

    def test_same_supplier_code_is_rejected_but_other_supplier_code_is_allowed(self):
        self.create_source()
        duplicate = self.client.post("/api/supplier-skus/", self.source_payload(), format="json")
        self.assertEqual(duplicate.status_code, status.HTTP_400_BAD_REQUEST)

        other_supplier = self.client.post(
            "/api/supplier-skus/",
            self.source_payload(self.supplier_b, supplier_sku_code="A-24V-BLACK"),
            format="json",
        )
        self.assertEqual(other_supplier.status_code, status.HTTP_201_CREATED, other_supplier.data)

    def test_preferred_source_is_exclusive_and_can_be_activated(self):
        first = self.create_source(is_preferred=True)
        second = self.create_source(self.supplier_b, supplier_sku_code="B-24V-BLACK")

        response = self.client.post(f"/api/supplier-skus/{second.id}/set-preferred/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertFalse(first.is_preferred)
        self.assertTrue(second.is_preferred)

    def test_supplier_source_search_returns_internal_sku(self):
        self.create_source(supplier_sku_code="EN-MANUAL-BATCH-7", supplier_model="VENDOR-EN-7")
        for term in ("EN-MANUAL-BATCH-7", "VENDOR-EN-7"):
            response = self.client.get("/api/skus/", {"search": term})
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn(self.sku.id, [row["id"] for row in response.data["results"]])

    def test_purchase_keeps_supplier_snapshot_and_inventory_traces_optional_source(self):
        source = self.create_source()
        response = self.client.post(
            "/api/purchase-orders/",
            {
                "supplier": self.supplier_a.id,
                "order": self.order.id,
                "order_date": "2026-08-23",
                "currency": "USD",
                "items": [{"sku": self.sku.id, "supplier_sku": source.id, "quantity": "10", "unit_price": "3.0000"}],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(self.client.post(f"/api/purchase-orders/{response.data['id']}/place/", {}, format="json").status_code, status.HTTP_200_OK)
        item = PurchaseOrderItem.objects.get(purchase_order_id=response.data["id"])
        self.assertEqual(item.supplier_sku_id, source.id)
        self.assertEqual(item.supplier_name_snapshot, self.supplier_a.name)
        self.assertEqual(item.supplier_model_snapshot, "SUP-A-24V")
        self.assertEqual(item.supplier_sku_code_snapshot, "A-24V-BLACK")
        self.assertEqual(item.unit_price, Decimal("3.0000"))

        source.supplier_model = "SUP-A-24V-NEW"
        source.purchase_price = Decimal("4.0000")
        source.save(update_fields=["supplier_model", "purchase_price", "updated_at"])
        item.refresh_from_db()
        self.assertEqual(item.supplier_model_snapshot, "SUP-A-24V")
        self.assertEqual(item.unit_price, Decimal("3.0000"))

        receipt = record_receipt(item, {"receipt_date": date(2026, 8, 24), "quantity": Decimal("10"), "unit_cost": Decimal("3")})
        movement = InventoryMovement.objects.get(pk=receipt.inventory_movement_id)
        self.assertEqual(movement.sku_id, self.sku.id)
        self.assertEqual(movement.supplier_sku_id, source.id)

    def test_purchase_rejects_source_from_other_supplier_or_sku(self):
        source = self.create_source()
        response = self.client.post(
            "/api/purchase-orders/",
            {
                "purchase_no": "PO-SUPPLIER-MISMATCH",
                "supplier": self.supplier_b.id,
                "order": self.order.id,
                "order_date": "2026-08-23",
                "items": [{"sku": self.sku.id, "supplier_sku": source.id, "quantity": "1", "unit_price": "3"}],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_referenced_supplier_source_cannot_be_deleted_but_unreferenced_can(self):
        referenced = self.create_source()
        purchase = PurchaseOrder.objects.create(
            purchase_no="PO-SUPPLIER-DELETE",
            supplier=self.supplier_a,
            order=self.order,
            order_date=date(2026, 8, 23),
        )
        PurchaseOrderItem.objects.create(purchase_order=purchase, sku=self.sku, supplier_sku=referenced, quantity=1, unit_price=2)
        response = self.client.delete(f"/api/supplier-skus/{referenced.id}/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        unused = self.create_source(self.supplier_b, supplier_sku_code="B-UNUSED")
        response = self.client.delete(f"/api/supplier-skus/{unused.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
