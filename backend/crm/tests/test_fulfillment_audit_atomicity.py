from datetime import date
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.db import DatabaseError
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from crm.models import (
    Customer,
    FulfillmentIdempotency,
    InventoryMovement,
    OperationLog,
    Order,
    Product,
    PurchaseOrder,
    SKU,
    Supplier,
)
from crm.services.fulfillment import confirm_shipment, record_receipt


@override_settings(AUDIT_LOG_ENABLED=True)
class FulfillmentAuditAtomicityTests(TestCase):
    """Exercise fulfillment audit snapshots and rollback on the isolated test DB."""

    def setUp(self):
        user_model = get_user_model()
        self.operator = user_model.objects.create_superuser(
            username="iss006-fulfillment-audit-test",
            email="iss006-audit@example.test",
            password="test-only-password",
        )
        self.client = APIClient()
        self.client.force_authenticate(self.operator)
        self.customer = Customer.objects.create(code="ISS006-AUDIT-C", name="ISS-006 Audit Customer")
        self.supplier = Supplier.objects.create(code="FA", name="ISS-006 Audit Supplier")
        product = Product.objects.create(code="ISS006-AUDIT-P", name="ISS-006 Audit Product")
        self.sku = SKU.objects.create(product=product, sku="ISS006-AUDIT-SKU")
        self.event_date = date(2026, 10, 30)

    def create_purchase(self, purchase_no, quantity):
        purchase = PurchaseOrder.objects.create(
            purchase_no=purchase_no,
            supplier=self.supplier,
            order_date=self.event_date,
            status="ordered",
        )
        item = purchase.items.create(sku=self.sku, quantity=quantity, unit_price="3")
        return purchase, item

    def receive(self, purchase, item, quantity):
        return self.receive_with_key(purchase, item, quantity, key=f"iss006-audit-receive-{uuid4()}")

    def receive_with_key(self, purchase, item, quantity, *, key):
        return self.client.post(
            f"/api/purchase-orders/{purchase.pk}/receive/",
            {
                "purchase_item": item.pk,
                "receipt_date": self.event_date.isoformat(),
                "quantity": str(quantity),
                "unit_cost": "3",
            },
            format="json",
            HTTP_IDEMPOTENCY_KEY=key,
        )

    def receipt_audit_rows(self, purchase):
        return list(
            OperationLog.objects.filter(
                entity="crm.purchaseorder",
                object_id=str(purchase.pk),
                action_label="登记采购到货",
            ).order_by("pk")
        )

    def test_partial_then_complete_receipts_audit_authoritative_status_transitions(self):
        purchase, item = self.create_purchase("PO-ISS006-AUDIT-PARTIAL", 4)

        first = self.receive(purchase, item, 2)
        self.assertEqual(first.status_code, status.HTTP_201_CREATED, first.data)
        first_log = self.receipt_audit_rows(purchase)[0]
        self.assertEqual(first_log.operator, self.operator)
        self.assertEqual(first_log.before_data["status"], "ordered")
        self.assertEqual(first_log.after_data["status"], "partial")
        self.assertEqual(first_log.changed_fields, ["status"])

        second = self.receive(purchase, item, 2)
        self.assertEqual(second.status_code, status.HTTP_201_CREATED, second.data)
        rows = self.receipt_audit_rows(purchase)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1].operator, self.operator)
        self.assertEqual(rows[1].before_data["status"], "partial")
        self.assertEqual(rows[1].after_data["status"], "completed")
        self.assertEqual(rows[1].changed_fields, ["status"])
        purchase.refresh_from_db()
        self.assertEqual(purchase.status, "completed")

    def test_receipt_audit_write_failure_rolls_back_receipt_inventory_and_key(self):
        purchase, item = self.create_purchase("PO-ISS006-AUDIT-RECEIPT-FAILURE", 4)
        key = f"iss006-audit-receipt-failure-{uuid4()}"
        before_movements = InventoryMovement.objects.filter(sku=self.sku).count()

        with patch("crm.views.record_operation", side_effect=DatabaseError("injected audit write failure")):
            with self.assertRaises(DatabaseError):
                self.receive_with_key(purchase, item, 2, key=key)

        item.refresh_from_db()
        purchase.refresh_from_db()
        self.assertEqual(item.receipts.count(), 0)
        self.assertEqual(item.received_quantity, Decimal("0"))
        self.assertEqual(purchase.status, "ordered")
        self.assertEqual(InventoryMovement.objects.filter(sku=self.sku).count(), before_movements)
        self.assertFalse(FulfillmentIdempotency.objects.filter(key=key).exists())
        self.assertFalse(self.receipt_audit_rows(purchase))

    def test_final_shipment_audits_authoritative_order_status_transition(self):
        order = Order.objects.create(
            order_no="SO-ISS006-AUDIT-FINAL",
            customer=self.customer,
            order_date=self.event_date,
            status="confirmed",
        )
        item = order.items.create(sku=self.sku, quantity="2", unit_price="5")
        InventoryMovement.objects.create(
            movement_no="IM-ISS006-AUDIT-STOCK",
            movement_date=self.event_date,
            type="purchase_in",
            sku=self.sku,
            quantity=Decimal("2"),
        )

        response = self.client.post(
            f"/api/orders/{order.pk}/ship/",
            {
                "shipment_date": self.event_date.isoformat(),
                "items": [{"order_item": item.pk, "quantity": "2"}],
            },
            format="json",
            HTTP_IDEMPOTENCY_KEY=f"iss006-audit-shipment-{uuid4()}",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        audit = OperationLog.objects.get(
            entity="crm.order",
            object_id=str(order.pk),
            action_label="确认订单发货",
        )
        self.assertEqual(audit.operator, self.operator)
        self.assertEqual(audit.before_data["status"], "confirmed")
        self.assertEqual(audit.after_data["status"], "shipped")
        self.assertEqual(audit.changed_fields, ["status"])
        order.refresh_from_db()
        self.assertEqual(order.status, "shipped")

    def test_shipment_audit_write_failure_rolls_back_shipment_inventory_and_key(self):
        order = Order.objects.create(
            order_no="SO-ISS006-AUDIT-SHIPMENT-FAILURE",
            customer=self.customer,
            order_date=self.event_date,
            status="confirmed",
        )
        item = order.items.create(sku=self.sku, quantity="2", unit_price="5")
        InventoryMovement.objects.create(
            movement_no="IM-ISS006-AUDIT-SHIPMENT-FAILURE-STOCK",
            movement_date=self.event_date,
            type="purchase_in",
            sku=self.sku,
            quantity=Decimal("2"),
        )
        key = f"iss006-audit-shipment-failure-{uuid4()}"
        before_movements = InventoryMovement.objects.filter(sku=self.sku).count()

        with patch("crm.views.record_operation", side_effect=DatabaseError("injected audit write failure")):
            with self.assertRaises(DatabaseError):
                self.client.post(
                    f"/api/orders/{order.pk}/ship/",
                    {
                        "shipment_date": self.event_date.isoformat(),
                        "items": [{"order_item": item.pk, "quantity": "2"}],
                    },
                    format="json",
                    HTTP_IDEMPOTENCY_KEY=key,
                )

        order.refresh_from_db()
        self.assertEqual(order.status, "confirmed")
        self.assertEqual(order.shipments.count(), 0)
        self.assertEqual(InventoryMovement.objects.filter(sku=self.sku).count(), before_movements)
        self.assertFalse(FulfillmentIdempotency.objects.filter(key=key).exists())
        self.assertFalse(OperationLog.objects.filter(action_label="确认订单发货").exists())

    def make_receipt_for_reversal(self, purchase_no="PO-ISS006-AUDIT-REVERSAL", quantity=3):
        purchase, item = self.create_purchase(purchase_no, quantity)
        receipt = record_receipt(
            item,
            {"receipt_date": self.event_date, "quantity": Decimal(quantity), "unit_cost": Decimal("3")},
        )
        receipt.refresh_from_db()
        purchase.refresh_from_db()
        return purchase, receipt

    def reverse_url(self, purchase, receipt):
        return f"/api/purchase-orders/{purchase.pk}/receipts/{receipt.pk}/reverse/"

    def test_receipt_reversal_success_records_audit_and_reverses_inventory(self):
        purchase, receipt = self.make_receipt_for_reversal()

        response = self.client.post(self.reverse_url(purchase, receipt), {"reason": "隔离测试冲销"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        receipt.refresh_from_db()
        purchase.refresh_from_db()
        self.assertIsNotNone(receipt.reversal_inventory_movement_id)
        self.assertEqual(purchase.status, "ordered")
        reversal = InventoryMovement.objects.get(pk=receipt.reversal_inventory_movement_id)
        self.assertEqual(reversal.type, "adjust_out")
        audit = OperationLog.objects.get(
            entity="crm.purchaseorder",
            object_id=str(purchase.pk),
            action_label="冲销采购入库",
        )
        self.assertEqual(audit.operator, self.operator)

    def test_reversal_business_validation_failure_preserves_receipt_and_inventory(self):
        purchase, receipt = self.make_receipt_for_reversal(
            "PO-ISS006-AUDIT-VALIDATION", quantity=3,
        )
        order = Order.objects.create(
            order_no="SO-ISS006-AUDIT-CONSUMED",
            customer=self.customer,
            order_date=self.event_date,
            status="confirmed",
        )
        item = order.items.create(sku=self.sku, quantity="2", unit_price="5")
        confirm_shipment(order, {
            "shipment_date": self.event_date,
            "items": [{"order_item": item.pk, "quantity": Decimal("2")}],
        })
        movement_ids_before = set(InventoryMovement.objects.filter(sku=self.sku).values_list("pk", flat=True))

        response = self.client.post(self.reverse_url(purchase, receipt), {"reason": "库存已被销售消耗"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertIn("实际库存不足", response.data["detail"])
        receipt.refresh_from_db()
        purchase.refresh_from_db()
        self.assertIsNone(receipt.reversal_inventory_movement_id)
        self.assertIsNone(receipt.reversed_at)
        self.assertEqual(receipt.reversal_reason, "")
        self.assertEqual(purchase.status, "completed")
        self.assertEqual(set(InventoryMovement.objects.filter(sku=self.sku).values_list("pk", flat=True)), movement_ids_before)
        self.assertFalse(OperationLog.objects.filter(action_label="冲销采购入库").exists())

    def test_audit_write_failure_rolls_back_receipt_reversal_and_inventory_movement(self):
        purchase, receipt = self.make_receipt_for_reversal(
            "PO-ISS006-AUDIT-WRITE-FAILURE", quantity=3,
        )
        original_movement_id = receipt.inventory_movement_id
        before_movement_ids = set(InventoryMovement.objects.filter(sku=self.sku).values_list("pk", flat=True))

        with patch("crm.views.record_operation", side_effect=DatabaseError("injected audit write failure")):
            with self.assertRaises(DatabaseError):
                self.client.post(self.reverse_url(purchase, receipt), {"reason": "注入审计故障"}, format="json")

        receipt.refresh_from_db()
        purchase.refresh_from_db()
        self.assertEqual(receipt.inventory_movement_id, original_movement_id)
        self.assertIsNone(receipt.reversal_inventory_movement_id)
        self.assertIsNone(receipt.reversed_at)
        self.assertEqual(receipt.reversal_reason, "")
        self.assertEqual(purchase.status, "completed")
        self.assertEqual(set(InventoryMovement.objects.filter(sku=self.sku).values_list("pk", flat=True)), before_movement_ids)
        self.assertFalse(OperationLog.objects.filter(action_label="冲销采购入库").exists())
