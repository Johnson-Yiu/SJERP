from datetime import date
from decimal import Decimal

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from crm.models import Customer, InventoryMovement, Order, Product, PurchaseOrder, Shipment, SKU, Supplier
from crm.services.fulfillment import allocate_order, sku_metrics


class Iss006FulfillmentRequestIdempotencyTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.day = date(2026, 10, 28)
        self.customer = Customer.objects.create(code="ISS006-TEST-CUSTOMER", name="ISS-006 测试客户")
        self.supplier = Supplier.objects.create(code="ISS006-TEST-SUPPLIER", name="ISS-006 测试供应商")
        product = Product.objects.create(code="ISS006-TEST-PRODUCT", name="ISS-006 测试产品")
        self.receipt_sku = SKU.objects.create(product=product, sku="ISS006-TEST-RECEIPT", unit="pcs")
        self.shipment_sku = SKU.objects.create(product=product, sku="ISS006-TEST-SHIPMENT", unit="pcs")

    def test_receipt_replay_returns_original_without_second_inventory_write(self):
        purchase = PurchaseOrder.objects.create(
            purchase_no="PO-ISS006-TEST",
            supplier=self.supplier,
            order_date=self.day,
            status="ordered",
            currency="USD",
        )
        item = purchase.items.create(sku=self.receipt_sku, quantity=Decimal("10"), unit_price=Decimal("2"))
        request_key = "iss006-receipt-retry-1"
        payload = {
            "purchase_item": item.pk,
            "receipt_date": str(self.day),
            "quantity": "5",
            "unit_cost": "2",
        }

        first = self.client.post(f"/api/purchase-orders/{purchase.pk}/receive/", payload, format="json", HTTP_IDEMPOTENCY_KEY=request_key)
        replay = self.client.post(f"/api/purchase-orders/{purchase.pk}/receive/", payload, format="json", HTTP_IDEMPOTENCY_KEY=request_key)

        self.assertEqual(first.status_code, status.HTTP_201_CREATED, first.data)
        self.assertEqual(replay.status_code, first.status_code, replay.data)
        self.assertEqual(replay["Idempotent-Replay"], "true")
        self.assertEqual(replay.data["id"], first.data["id"])
        self.assertEqual(item.receipts.count(), 1)
        self.assertEqual(InventoryMovement.objects.filter(source_type="receipt", sku=self.receipt_sku).count(), 1)
        self.assertEqual(sku_metrics(self.receipt_sku)["actual_quantity"], Decimal("5.00"))

    def test_receipt_key_conflict_does_not_apply_changed_payload(self):
        purchase = PurchaseOrder.objects.create(
            purchase_no="PO-ISS006-CONFLICT",
            supplier=self.supplier,
            order_date=self.day,
            status="ordered",
            currency="USD",
        )
        item = purchase.items.create(sku=self.receipt_sku, quantity=Decimal("10"), unit_price=Decimal("2"))
        payload = {
            "request_key": "iss006-receipt-conflict-1",
            "purchase_item": item.pk,
            "receipt_date": str(self.day),
            "quantity": "5",
            "unit_cost": "2",
        }
        self.assertEqual(self.client.post(f"/api/purchase-orders/{purchase.pk}/receive/", payload, format="json", HTTP_IDEMPOTENCY_KEY=payload["request_key"]).status_code, status.HTTP_201_CREATED)
        changed = {**payload, "quantity": "4"}

        response = self.client.post(f"/api/purchase-orders/{purchase.pk}/receive/", changed, format="json", HTTP_IDEMPOTENCY_KEY=payload["request_key"])

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT, response.data)
        self.assertIn("Idempotency-Key", response.data["detail"])
        self.assertEqual(item.receipts.count(), 1)
        self.assertEqual(sku_metrics(self.receipt_sku)["actual_quantity"], Decimal("5.00"))

    def test_shipment_replay_returns_original_without_second_inventory_write(self):
        order = Order.objects.create(
            order_no="SO-ISS006-TEST",
            customer=self.customer,
            order_date=self.day,
            status="confirmed",
            currency="USD",
        )
        item = order.items.create(sku=self.shipment_sku, quantity=Decimal("10"), unit_price=Decimal("3"))
        InventoryMovement.objects.create(
            movement_no="IM-ISS006-TEST",
            movement_date=self.day,
            type="adjust_in",
            sku=self.shipment_sku,
            quantity=Decimal("10"),
            source_type="manual",
        )
        allocate_order(order)
        request_key = "iss006-shipment-retry-1"
        payload = {
            "shipment_date": str(self.day),
            "items": [{"order_item": item.pk, "quantity": "5"}],
        }

        first = self.client.post(f"/api/orders/{order.pk}/ship/", payload, format="json", HTTP_IDEMPOTENCY_KEY=request_key)
        replay = self.client.post(f"/api/orders/{order.pk}/ship/", payload, format="json", HTTP_IDEMPOTENCY_KEY=request_key)

        self.assertEqual(first.status_code, status.HTTP_201_CREATED, first.data)
        self.assertEqual(replay.status_code, first.status_code, replay.data)
        self.assertEqual(replay["Idempotent-Replay"], "true")
        self.assertEqual(replay.data["id"], first.data["id"])
        self.assertEqual(Shipment.objects.filter(order=order).count(), 1)
        self.assertEqual(InventoryMovement.objects.filter(source_type="shipment", sku=self.shipment_sku).count(), 1)
        self.assertEqual(sku_metrics(self.shipment_sku)["actual_quantity"], Decimal("5.00"))
