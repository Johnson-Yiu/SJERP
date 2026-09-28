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
        self.order.status = "confirmed"
        self.order.save(update_fields=["status"])
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

    def test_create_and_draft_update_resolve_the_same_unique_source(self):
        source = self.create_source()
        created = self.client.post("/api/purchase-orders/", {
            "supplier": self.supplier_a.id, "order": self.order.id, "order_date": "2026-08-23",
            "currency": "USD", "items": [{"sku": self.sku.id, "quantity": "1", "unit_price": "3"}],
        }, format="json")
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.data)
        self.assertEqual(PurchaseOrderItem.objects.get(purchase_order_id=created.data["id"]).supplier_sku_id, source.id)

        second_sku = SKU.objects.create(product=self.product, sku="SKU-SUPPLIER-UPDATE")
        second_source = SupplierSKU.objects.create(supplier=self.supplier_a, sku=second_sku, supplier_sku_code="A-UPDATE")
        payload = {
            "supplier": self.supplier_a.id, "order": self.order.id, "order_date": "2026-08-23", "currency": "USD",
            "exchange_rate": "1", "items": [
                {"sku": self.sku.id, "supplier_sku": source.id, "quantity": "1", "unit_price": "3"},
                {"sku": second_sku.id, "quantity": "2", "unit_price": "4"},
            ],
        }
        updated = self.client.put(f"/api/purchase-orders/{created.data['id']}/", payload, format="json")
        self.assertEqual(updated.status_code, status.HTTP_200_OK, updated.data)
        self.assertEqual(PurchaseOrderItem.objects.get(purchase_order_id=created.data["id"], sku=second_sku).supplier_sku_id, second_source.id)

    def test_order_source_ambiguity_requires_explicit_source_but_same_source_inherits(self):
        first = self.create_source(supplier_sku_code="A-ONE")
        second = self.create_source(supplier_sku_code="A-TWO")
        self.order.items.create(sku=self.sku, supplier_sku=first, quantity="1", unit_price="1")
        self.order.items.create(sku=self.sku, supplier_sku=second, quantity="1", unit_price="1")
        response = self.client.post("/api/purchase-orders/", {
            "supplier": self.supplier_a.id, "order": self.order.id, "order_date": "2026-08-23",
            "currency": "USD", "items": [{"sku": self.sku.id, "quantity": "1", "unit_price": "3"}],
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("多个采购来源", str(response.data))

        self.order.items.filter(supplier_sku=second).delete()
        response = self.client.post("/api/purchase-orders/", {
            "supplier": self.supplier_a.id, "order": self.order.id, "order_date": "2026-08-23",
            "currency": "USD", "items": [{"sku": self.sku.id, "quantity": "1", "unit_price": "3"}],
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(PurchaseOrderItem.objects.get(purchase_order_id=response.data["id"]).supplier_sku_id, first.id)

    def test_auto_supplier_source_uses_purchase_currency(self):
        for supplier, currency in ((self.supplier_a, "CNY"), (self.supplier_b, "EUR")):
            response = self.client.post("/api/purchase-orders/", {
                "supplier": supplier.id, "order_date": "2026-08-23", "currency": currency,
                "exchange_rate": "1", "items": [{"sku": self.sku.id, "quantity": "1", "unit_price": "3"}],
            }, format="json")
            self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
            source = PurchaseOrderItem.objects.get(purchase_order_id=response.data["id"]).supplier_sku
            self.assertEqual(source.currency, currency)
            self.assertEqual(source.purchase_price, Decimal("0"))

    def test_draft_supplier_change_requires_items_and_draft_rejects_inactive_source(self):
        source_a = self.create_source()
        source_b = self.create_source(self.supplier_b, supplier_sku_code="B-24V")
        draft = self.client.post("/api/purchase-orders/", {
            "supplier": self.supplier_a.id, "order_date": "2026-08-23", "currency": "USD",
            "items": [{"sku": self.sku.id, "supplier_sku": source_a.id, "quantity": "1", "unit_price": "3"}],
        }, format="json")
        self.assertEqual(draft.status_code, status.HTTP_201_CREATED, draft.data)
        rejected = self.client.patch(f"/api/purchase-orders/{draft.data['id']}/", {"supplier": self.supplier_b.id}, format="json")
        self.assertEqual(rejected.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("必须同时提交采购明细", str(rejected.data))

        source_b.is_active = False
        source_b.save(update_fields=["is_active"])
        payload = {"supplier": self.supplier_b.id, "order_date": "2026-08-23", "currency": "USD", "exchange_rate": "1", "items": [{"sku": self.sku.id, "supplier_sku": source_b.id, "quantity": "1", "unit_price": "3"}]}
        rejected = self.client.put(f"/api/purchase-orders/{draft.data['id']}/", payload, format="json")
        self.assertEqual(rejected.status_code, status.HTTP_400_BAD_REQUEST)

    def test_new_purchase_rejects_inactive_source_but_formal_history_remains_idempotent(self):
        source = self.create_source()
        source.is_active = False
        source.save(update_fields=["is_active"])
        rejected = self.client.post("/api/purchase-orders/", {
            "supplier": self.supplier_a.id, "order_date": "2026-08-23", "currency": "USD",
            "items": [{"sku": self.sku.id, "supplier_sku": source.id, "quantity": "1", "unit_price": "3"}],
        }, format="json")
        self.assertEqual(rejected.status_code, status.HTTP_400_BAD_REQUEST)

        source.is_active = True
        source.save(update_fields=["is_active"])
        created = self.client.post("/api/purchase-orders/", {
            "supplier": self.supplier_a.id, "order_date": "2026-08-23", "currency": "USD",
            "items": [{"sku": self.sku.id, "supplier_sku": source.id, "quantity": "1", "unit_price": "3"}],
        }, format="json")
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.data)
        self.assertEqual(self.client.post(f"/api/purchase-orders/{created.data['id']}/place/", {}, format="json").status_code, status.HTTP_200_OK)
        source.is_active = False
        source.save(update_fields=["is_active"])
        payload = {"supplier": self.supplier_a.id, "order_date": "2026-08-23", "currency": "USD", "exchange_rate": "1", "items": [{"sku": self.sku.id, "supplier_sku": source.id, "quantity": "1", "unit_price": "3"}]}
        self.assertEqual(self.client.put(f"/api/purchase-orders/{created.data['id']}/", payload, format="json").status_code, status.HTTP_200_OK)

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
