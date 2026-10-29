from datetime import date
from decimal import Decimal
import threading

from django.contrib.auth import get_user_model
from django.db import close_old_connections, connection
from django.test import TestCase, TransactionTestCase, override_settings, skipUnlessDBFeature
from rest_framework import status
from rest_framework.test import APIClient

from crm.models import (
    Customer,
    FulfillmentIdempotency,
    GoodsReceipt,
    InventoryMovement,
    OperationLog,
    Order,
    Product,
    PurchaseOrder,
    Shipment,
    SKU,
    Supplier,
)


class FulfillmentIdempotencyApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(username="iss006-idempotency-user")
        self.client.force_authenticate(self.user)
        self.customer = Customer.objects.create(code="ISS006-C", name="ISS-006 Buyer")
        product = Product.objects.create(code="ISS006-P", name="ISS-006 Light")
        self.sku = SKU.objects.create(product=product, sku="ISS006-SKU")
        self.supplier = Supplier.objects.create(code="ISS006-S", name="ISS-006 Supplier")

    def post(self, path, payload, key):
        return self.client.post(path, payload, format="json", HTTP_IDEMPOTENCY_KEY=key)

    def purchase(self, quantity="4"):
        order = Order.objects.create(
            order_no=f"ISS006-SO-R-{PurchaseOrder.objects.count()}",
            customer=self.customer,
            order_date=date(2026, 10, 29),
            status="confirmed",
        )
        purchase = PurchaseOrder.objects.create(
            purchase_no=f"ISS006-PO-{PurchaseOrder.objects.count()}",
            supplier=self.supplier,
            order=order,
            order_date=date(2026, 10, 29),
            status="ordered",
        )
        item = purchase.items.create(sku=self.sku, quantity=quantity, unit_price="3")
        return purchase, item

    def order_with_stock(self, quantity="2"):
        order = Order.objects.create(
            order_no=f"ISS006-SO-S-{Order.objects.count()}",
            customer=self.customer,
            order_date=date(2026, 10, 29),
            status="confirmed",
        )
        item = order.items.create(sku=self.sku, quantity=quantity, unit_price="5")
        InventoryMovement.objects.create(
            movement_no=f"ISS006-IN-{InventoryMovement.objects.count()}",
            movement_date=date(2026, 10, 29),
            type="purchase_in",
            sku=self.sku,
            quantity=quantity,
        )
        return order, item

    @override_settings(AUDIT_LOG_ENABLED=True)
    def test_receipt_replay_returns_original_result_and_does_not_audit_twice(self):
        purchase, item = self.purchase()
        payload = {"purchase_item": item.pk, "receipt_date": "2026-10-29", "quantity": "2", "unit_cost": "3"}

        first = self.post(f"/api/purchase-orders/{purchase.pk}/receive/", payload, "iss006-receipt-1")
        replay = self.post(f"/api/purchase-orders/{purchase.pk}/receive/", payload, "iss006-receipt-1")

        self.assertEqual(first.status_code, status.HTTP_201_CREATED, first.data)
        self.assertEqual(replay.status_code, status.HTTP_201_CREATED, replay.data)
        self.assertEqual(replay.data, first.data)
        self.assertEqual(replay.headers.get("Idempotent-Replay"), "true")
        self.assertEqual(GoodsReceipt.objects.filter(purchase_item=item).count(), 1)
        self.assertEqual(InventoryMovement.objects.filter(source_type="receipt").count(), 1)
        self.assertEqual(FulfillmentIdempotency.objects.filter(key="iss006-receipt-1", status="succeeded").count(), 1)
        self.assertEqual(OperationLog.objects.filter(action_label="登记采购到货").count(), 1)

    def test_same_receipt_key_with_changed_content_is_rejected(self):
        purchase, item = self.purchase()
        first = self.post(
            f"/api/purchase-orders/{purchase.pk}/receive/",
            {"purchase_item": item.pk, "receipt_date": "2026-10-29", "quantity": "1", "unit_cost": "3"},
            "iss006-receipt-conflict",
        )
        conflict = self.post(
            f"/api/purchase-orders/{purchase.pk}/receive/",
            {"purchase_item": item.pk, "receipt_date": "2026-10-29", "quantity": "2", "unit_cost": "3"},
            "iss006-receipt-conflict",
        )

        self.assertEqual(first.status_code, status.HTTP_201_CREATED, first.data)
        self.assertEqual(conflict.status_code, status.HTTP_409_CONFLICT, conflict.data)
        self.assertIn("不同", conflict.data["detail"])
        self.assertEqual(GoodsReceipt.objects.filter(purchase_item=item).count(), 1)

    def test_distinct_receipt_keys_allow_two_identical_business_operations(self):
        purchase, item = self.purchase(quantity="4")
        payload = {"purchase_item": item.pk, "receipt_date": "2026-10-29", "quantity": "1", "unit_cost": "3"}

        first = self.post(f"/api/purchase-orders/{purchase.pk}/receive/", payload, "iss006-receipt-a")
        second = self.post(f"/api/purchase-orders/{purchase.pk}/receive/", payload, "iss006-receipt-b")

        self.assertEqual(first.status_code, status.HTTP_201_CREATED, first.data)
        self.assertEqual(second.status_code, status.HTTP_201_CREATED, second.data)
        self.assertNotEqual(first.data["id"], second.data["id"])
        self.assertEqual(GoodsReceipt.objects.filter(purchase_item=item).count(), 2)

    def test_failed_receipt_does_not_leave_idempotency_or_inventory_side_effects(self):
        purchase, item = self.purchase(quantity="1")
        failed_payload = {"purchase_item": item.pk, "receipt_date": "2026-10-29", "quantity": "2", "unit_cost": "3"}
        failed = self.post(f"/api/purchase-orders/{purchase.pk}/receive/", failed_payload, "iss006-receipt-failed")

        self.assertEqual(failed.status_code, status.HTTP_400_BAD_REQUEST, failed.data)
        self.assertEqual(FulfillmentIdempotency.objects.filter(key="iss006-receipt-failed").count(), 0)
        self.assertEqual(GoodsReceipt.objects.count(), 0)
        self.assertEqual(InventoryMovement.objects.filter(source_type="receipt").count(), 0)

        recovered = self.post(
            f"/api/purchase-orders/{purchase.pk}/receive/",
            {**failed_payload, "quantity": "1"},
            "iss006-receipt-failed",
        )
        self.assertEqual(recovered.status_code, status.HTTP_201_CREATED, recovered.data)

    def test_shipment_replay_preserves_inventory_and_supplement_side_effects(self):
        order, item = self.order_with_stock(quantity="2")
        payload = {"shipment_date": "2026-10-29", "items": [{"order_item": item.pk, "quantity": "2"}]}

        first = self.post(f"/api/orders/{order.pk}/ship/", payload, "iss006-shipment-1")
        replay = self.post(f"/api/orders/{order.pk}/ship/", payload, "iss006-shipment-1")

        self.assertEqual(first.status_code, status.HTTP_201_CREATED, first.data)
        self.assertEqual(replay.status_code, status.HTTP_201_CREATED, replay.data)
        self.assertEqual(replay.data, first.data)
        self.assertEqual(Shipment.objects.filter(order=order, status="confirmed").count(), 1)
        self.assertEqual(InventoryMovement.objects.filter(order=order, source_type="shipment").count(), 1)
        self.assertEqual(FulfillmentIdempotency.objects.filter(key="iss006-shipment-1", status="succeeded").count(), 1)

    def test_distinct_shipment_keys_allow_two_partial_shipments(self):
        order, item = self.order_with_stock(quantity="2")
        payload = {"shipment_date": "2026-10-29", "items": [{"order_item": item.pk, "quantity": "1"}]}

        first = self.post(f"/api/orders/{order.pk}/ship/", payload, "iss006-shipment-a")
        second = self.post(f"/api/orders/{order.pk}/ship/", payload, "iss006-shipment-b")

        self.assertEqual(first.status_code, status.HTTP_201_CREATED, first.data)
        self.assertEqual(second.status_code, status.HTTP_201_CREATED, second.data)
        self.assertNotEqual(first.data["id"], second.data["id"])
        self.assertEqual(Shipment.objects.filter(order=order, status="confirmed").count(), 2)
        self.assertEqual(InventoryMovement.objects.filter(order=order, source_type="shipment").count(), 2)

    def test_missing_key_is_rejected_before_business_side_effects(self):
        purchase, item = self.purchase()
        response = self.client.post(
            f"/api/purchase-orders/{purchase.pk}/receive/",
            {"purchase_item": item.pk, "receipt_date": "2026-10-29", "quantity": "1", "unit_cost": "3"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertIn("Idempotency-Key", response.data["detail"])
        self.assertEqual(GoodsReceipt.objects.count(), 0)


@skipUnlessDBFeature("supports_transactions")
class FulfillmentIdempotencyDatabaseTests(TransactionTestCase):
    """The unique-key race is executed in PostgreSQL CI/deployment checks."""

    def test_postgresql_concurrent_duplicate_requests_are_serialized(self):
        if connection.vendor != "postgresql":
            self.skipTest("本地 SQLite 不提供 PostgreSQL 并发锁语义；需在 PostgreSQL 环境执行。")
        user = get_user_model().objects.create_user(username="iss006-concurrent-user")
        customer = Customer.objects.create(code="ISS006-PC", name="ISS-006 PostgreSQL Buyer")
        sku = SKU.objects.create(product=Product.objects.create(code="ISS006-PP", name="ISS-006 PG Light"), sku="ISS006-PSKU")
        order = Order.objects.create(order_no="ISS006-PSO", customer=customer, order_date=date(2026, 10, 29), status="confirmed")
        item = order.items.create(sku=sku, quantity="2", unit_price="5")
        InventoryMovement.objects.create(movement_no="ISS006-PIN", movement_date=date(2026, 10, 29), type="purchase_in", sku=sku, quantity="2")
        barrier = threading.Barrier(2)
        results = []

        def submit():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                client = APIClient()
                client.force_authenticate(user)
                response = client.post(
                    f"/api/orders/{order.pk}/ship/",
                    {"shipment_date": "2026-10-29", "items": [{"order_item": item.pk, "quantity": "2"}]},
                    format="json",
                    HTTP_IDEMPOTENCY_KEY="iss006-concurrent-shipment",
                )
                results.append(response.status_code)
            finally:
                close_old_connections()

        threads = [threading.Thread(target=submit) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=20)
        self.assertEqual(sorted(results), [201, 201])
        self.assertEqual(Shipment.objects.filter(order=order, status="confirmed").count(), 1)
        self.assertEqual(InventoryMovement.objects.filter(order=order, source_type="shipment").count(), 1)
