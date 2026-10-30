from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import DatabaseError
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from crm.audit import record_operation
from crm.models import (
    Customer,
    InventoryMovement,
    OperationLog,
    Order,
    Product,
    SKU,
    ShipmentItem,
)
from crm.services.fulfillment import confirm_shipment, sku_metrics


@override_settings(AUDIT_LOG_ENABLED=True)
class InventoryReversalAuditAtomicityTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        operator = user_model.objects.create_superuser(
            username="iss006-reversal-audit-test",
            email="iss006-reversal-audit@example.test",
            password="test-only-password",
        )
        self.client = APIClient()
        self.client.force_authenticate(operator)
        self.day = date(2026, 10, 30)
        self.customer = Customer.objects.create(
            code="ISS006-REV-AUDIT-C",
            name="ISS-006 Reversal Audit Customer",
        )
        product = Product.objects.create(
            code="ISS006-REV-AUDIT-P",
            name="ISS-006 Reversal Audit Product",
        )
        self.sku = SKU.objects.create(product=product, sku="ISS006-REV-AUDIT-SKU")

    def create_shipment(self, suffix):
        order = Order.objects.create(
            order_no=f"SO-ISS006-REV-AUDIT-{suffix}",
            customer=self.customer,
            order_date=self.day,
            status="confirmed",
        )
        item = order.items.create(sku=self.sku, quantity=Decimal("2"), unit_price=Decimal("5"))
        InventoryMovement.objects.create(
            movement_no=f"IM-ISS006-REV-AUDIT-STOCK-{suffix}",
            movement_date=self.day,
            type="adjust_in",
            sku=self.sku,
            quantity=Decimal("2"),
            source_type="manual",
        )
        shipment = confirm_shipment(order, {
            "shipment_date": self.day,
            "items": [{"order_item": item.pk, "quantity": Decimal("2")}],
        })
        return order, shipment

    def create_manual_movement(self, suffix):
        return InventoryMovement.objects.create(
            movement_no=f"IM-ISS006-MANUAL-{suffix}",
            movement_date=self.day,
            type="adjust_in",
            sku=self.sku,
            quantity=Decimal("2"),
            source_type="manual",
        )

    def shipment_state(self, order, shipment):
        shipment.refresh_from_db()
        order.refresh_from_db()
        return {
            "movement_ids": tuple(
                InventoryMovement.objects.order_by("pk").values_list("pk", flat=True)
            ),
            "shipment_status": shipment.status,
            "shipment_reversed_at": shipment.reversed_at,
            "shipment_reversal_reason": shipment.reversal_reason,
            "item_reversal_ids": tuple(
                ShipmentItem.objects.filter(shipment=shipment)
                .order_by("pk")
                .values_list("reversal_inventory_movement_id", flat=True)
            ),
            "order_status": order.status,
            "actual": sku_metrics(self.sku)["actual_quantity"],
            "reserved": sku_metrics(self.sku)["reserved_quantity"],
            "audit_ids": tuple(OperationLog.objects.order_by("pk").values_list("pk", flat=True)),
        }

    def manual_state(self, original):
        original.refresh_from_db()
        return {
            "movement_ids": tuple(
                InventoryMovement.objects.order_by("pk").values_list("pk", flat=True)
            ),
            "original_exists": InventoryMovement.objects.filter(pk=original.pk).exists(),
            "actual": sku_metrics(self.sku)["actual_quantity"],
            "reserved": sku_metrics(self.sku)["reserved_quantity"],
            "audit_ids": tuple(OperationLog.objects.order_by("pk").values_list("pk", flat=True)),
        }

    def test_sales_shipment_reversal_succeeds_and_duplicate_keeps_existing_rule(self):
        order, shipment = self.create_shipment("SUCCESS")
        url = f"/api/shipments/{shipment.pk}/reverse/"

        response = self.client.post(url, {"reason": "隔离验收发货冲销"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        shipment.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(shipment.status, "cancelled")
        self.assertEqual(order.status, "confirmed")
        self.assertEqual(sku_metrics(self.sku)["actual_quantity"], Decimal("2.00"))
        self.assertEqual(sku_metrics(self.sku)["reserved_quantity"], Decimal("2.00"))
        self.assertEqual(OperationLog.objects.filter(action_label="冲销销售发货").count(), 1)

        movement_count = InventoryMovement.objects.count()
        duplicate = self.client.post(url, {"reason": "重复冲销"}, format="json")

        self.assertEqual(duplicate.status_code, status.HTTP_400_BAD_REQUEST, duplicate.data)
        self.assertIn("已经冲销", duplicate.data["detail"])
        self.assertEqual(InventoryMovement.objects.count(), movement_count)
        self.assertEqual(OperationLog.objects.filter(action_label="冲销销售发货").count(), 1)

    def test_sales_shipment_reversal_audit_failure_rolls_back_business_and_stock(self):
        order, shipment = self.create_shipment("AUDIT-FAIL")
        before = self.shipment_state(order, shipment)

        with patch("crm.views.record_operation", side_effect=DatabaseError("injected audit failure")):
            with self.assertRaises(DatabaseError):
                self.client.post(
                    f"/api/shipments/{shipment.pk}/reverse/",
                    {"reason": "审计失败注入"},
                    format="json",
                )

        self.assertEqual(self.shipment_state(order, shipment), before)

    def test_manual_inventory_reversal_writes_both_audits_and_duplicate_is_rejected(self):
        original = self.create_manual_movement("SUCCESS")
        url = f"/api/inventory-movements/{original.pk}/reverse/"

        response = self.client.post(url, {"reason": "隔离验收盘盈冲销"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        reversal = InventoryMovement.objects.get(pk=response.data["id"])
        self.assertEqual(reversal.type, "adjust_out")
        self.assertEqual(reversal.source_type, "reversal")
        self.assertEqual(sku_metrics(self.sku)["actual_quantity"], Decimal("0.00"))
        self.assertEqual(OperationLog.objects.filter(action_label="冲销库存流水").count(), 1)
        self.assertEqual(OperationLog.objects.filter(action_label="生成库存冲销流水").count(), 1)

        movement_count = InventoryMovement.objects.count()
        audit_count = OperationLog.objects.count()
        duplicate = self.client.post(url, {"reason": "重复冲销"}, format="json")

        self.assertEqual(duplicate.status_code, status.HTTP_400_BAD_REQUEST, duplicate.data)
        self.assertIn("已经冲销", duplicate.data["detail"])
        self.assertEqual(InventoryMovement.objects.count(), movement_count)
        self.assertEqual(OperationLog.objects.count(), audit_count)

    def test_manual_inventory_reversal_rolls_back_when_first_audit_fails(self):
        original = self.create_manual_movement("FIRST-AUDIT-FAIL")
        before = self.manual_state(original)

        with patch("crm.views.record_operation", side_effect=DatabaseError("first audit failure")):
            with self.assertRaises(DatabaseError):
                self.client.post(
                    f"/api/inventory-movements/{original.pk}/reverse/",
                    {"reason": "第一条审计失败注入"},
                    format="json",
                )

        self.assertEqual(self.manual_state(original), before)

    def test_manual_inventory_reversal_rolls_back_both_audits_when_second_fails(self):
        original = self.create_manual_movement("SECOND-AUDIT-FAIL")
        before = self.manual_state(original)
        calls = 0

        def record_first_then_fail_second(**kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise DatabaseError("second audit failure")
            return record_operation(**kwargs)

        with patch("crm.views.record_operation", side_effect=record_first_then_fail_second):
            with self.assertRaises(DatabaseError):
                self.client.post(
                    f"/api/inventory-movements/{original.pk}/reverse/",
                    {"reason": "第二条审计失败注入"},
                    format="json",
                )

        self.assertEqual(calls, 2)
        self.assertEqual(self.manual_state(original), before)
