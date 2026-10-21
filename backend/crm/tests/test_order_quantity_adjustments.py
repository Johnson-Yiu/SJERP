from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from crm.models import (
    Customer,
    InventoryReservation,
    InventoryMovement,
    Order,
    OrderQuantityAdjustment,
    OperationLog,
    PaymentPlan,
    Product,
    Shipment,
    ShipmentItem,
    SKU,
    SKUTradeUnit,
    Transaction,
)


class OrderQuantityAdjustmentApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        customer = Customer.objects.create(code="C-QTY-ADJUST", name="数量变更客户")
        product = Product.objects.create(code="P-QTY-ADJUST", name="数量变更产品")
        self.sku = SKU.objects.create(product=product, sku="SKU-QTY-ADJUST", unit="pcs")
        self.order = Order.objects.create(
            order_no="SO-QTY-ADJUST",
            customer=customer,
            order_date=date(2026, 10, 21),
            currency="USD",
            exchange_rate=Decimal("1"),
            status="confirmed",
        )
        self.item = self.order.items.create(sku=self.sku, quantity=Decimal("100"), unit_price=Decimal("10"))
        self.plan = PaymentPlan.objects.create(
            order=self.order,
            direction="receivable",
            currency="USD",
            planned_amount=Decimal("1000"),
            status="open",
        )

    def payload(self, *, version=None, key="qty-adjust-1", reason="客户调整需求", items=None):
        return {
            "version": self.order.quantity_change_version if version is None else version,
            "request_key": key,
            "reason": reason,
            "items": items or [{"order_item": self.item.id, "new_quantity": "150"}],
        }

    def test_increase_updates_line_preserves_identity_and_extends_receivable(self):
        payload = self.payload()
        preview = self.client.post(
            f"/api/orders/{self.order.id}/quantity-adjustments/preview/",
            payload,
            format="json",
        )
        self.assertEqual(preview.status_code, status.HTTP_200_OK, preview.data)
        self.assertTrue(preview.data["can_submit"])
        self.assertEqual(preview.data["lines"][0]["quantity_delta"], "50.00")
        self.assertEqual(preview.data["financial"]["amount_delta"], "500.0000")

        response = self.client.post(
            f"/api/orders/{self.order.id}/quantity-adjustments/",
            payload,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.item.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(self.item.quantity, Decimal("150.00"))
        self.assertEqual(self.item.pk, response.data["adjustment"]["lines"][0]["order_item"])
        self.assertEqual(self.order.quantity_change_version, 1)
        self.assertEqual(sum(PaymentPlan.objects.filter(order=self.order, status__in=["open", "settled"]).values_list("planned_amount", flat=True)), Decimal("1500.0000"))
        self.assertFalse(OrderQuantityAdjustment.objects.filter(order=self.order).first().impact["warnings"])

        retry = self.client.post(
            f"/api/orders/{self.order.id}/quantity-adjustments/",
            payload,
            format="json",
        )
        self.assertEqual(retry.status_code, status.HTTP_200_OK, retry.data)
        self.assertTrue(retry.data["replayed"])
        self.assertEqual(OrderQuantityAdjustment.objects.filter(order=self.order).count(), 1)

    def test_decrease_without_shipment_reduces_only_unsettled_plan_and_rebalances_reservation(self):
        InventoryMovement.objects.create(
            movement_no="IM-QTY-STOCK",
            movement_date=date(2026, 10, 21),
            type="adjust_in",
            sku=self.sku,
            quantity=Decimal("100"),
        )
        InventoryReservation.objects.create(order_item=self.item, sku=self.sku, quantity=Decimal("100"))
        payload = self.payload(key="qty-adjust-60", items=[{"order_item": self.item.id, "new_quantity": "60"}])
        response = self.client.post(f"/api/orders/{self.order.id}/quantity-adjustments/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.item.refresh_from_db()
        self.assertEqual(self.item.quantity, Decimal("60.00"))
        self.assertEqual(PaymentPlan.objects.get(pk=self.plan.pk).planned_amount, Decimal("600.0000"))
        self.assertEqual(
            InventoryReservation.objects.filter(order_item=self.item).values_list("quantity", flat=True).first(),
            Decimal("60.00"),
        )

    def test_partial_shipment_allows_safe_decrease_but_rejects_below_shipped(self):
        shipment = Shipment.objects.create(
            shipment_no="SHP-QTY-50",
            order=self.order,
            shipment_date=date(2026, 10, 21),
            status="confirmed",
        )
        ShipmentItem.objects.create(shipment=shipment, order_item=self.item, sku=self.sku, quantity=Decimal("50"))

        allowed = self.payload(key="qty-adjust-shipped-60", items=[{"order_item": self.item.id, "new_quantity": "60"}])
        response = self.client.post(f"/api/orders/{self.order.id}/quantity-adjustments/", allowed, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.item.refresh_from_db()
        self.assertEqual(self.item.quantity, Decimal("60.00"))

        blocked = self.payload(
            version=1,
            key="qty-adjust-shipped-40",
            items=[{"order_item": self.item.id, "new_quantity": "40"}],
        )
        response = self.client.post(f"/api/orders/{self.order.id}/quantity-adjustments/", blocked, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.item.refresh_from_db()
        self.assertEqual(self.item.quantity, Decimal("60.00"))
        self.assertEqual(OrderQuantityAdjustment.objects.filter(order=self.order).count(), 1)

    def test_cannot_decrease_below_seventy_already_shipped(self):
        shipment = Shipment.objects.create(
            shipment_no="SHP-QTY-70",
            order=self.order,
            shipment_date=date(2026, 10, 21),
            status="confirmed",
        )
        ShipmentItem.objects.create(shipment=shipment, order_item=self.item, sku=self.sku, quantity=Decimal("70"))
        response = self.client.post(
            f"/api/orders/{self.order.id}/quantity-adjustments/",
            self.payload(key="qty-adjust-shipped-70", items=[{"order_item": self.item.id, "new_quantity": "60"}]),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.item.refresh_from_db()
        self.assertEqual(self.item.quantity, Decimal("100.00"))
        self.assertFalse(OrderQuantityAdjustment.objects.filter(order=self.order).exists())

    def test_multiple_lines_are_atomic_when_one_line_is_invalid(self):
        second = self.order.items.create(sku=self.sku, quantity=Decimal("20"), unit_price=Decimal("5"))
        self.plan.planned_amount = Decimal("1100")
        self.plan.save(update_fields=["planned_amount"])
        response = self.client.post(
            f"/api/orders/{self.order.id}/quantity-adjustments/",
            self.payload(
                key="qty-adjust-multi-invalid",
                items=[
                    {"order_item": self.item.id, "new_quantity": "150"},
                    {"order_item": second.id, "new_quantity": "-1"},
                ],
            ),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.item.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(self.item.quantity, Decimal("100.00"))
        self.assertEqual(second.quantity, Decimal("20.00"))
        self.assertEqual(self.order.quantity_change_version, 0)
        self.assertFalse(OrderQuantityAdjustment.objects.filter(order=self.order).exists())

    def test_existing_purchase_allocation_is_preserved_and_excess_is_only_a_warning(self):
        from crm.models import PurchaseCostAllocation, PurchaseOrder, Supplier

        supplier = Supplier.objects.create(code="SUP-QTY-ADJUST", name="采购供应商")
        purchase = PurchaseOrder.objects.create(
            purchase_no="PO-QTY-ADJUST",
            supplier=supplier,
            order=self.order,
            order_date=date(2026, 10, 21),
            status="ordered",
        )
        purchase_item = purchase.items.create(sku=self.sku, quantity=Decimal("120"), unit_price=Decimal("7"))
        allocation = PurchaseCostAllocation.objects.create(
            purchase_item=purchase_item,
            target_type="order",
            order=self.order,
            quantity=Decimal("120"),
        )
        preview = self.client.post(
            f"/api/orders/{self.order.id}/quantity-adjustments/preview/",
            self.payload(key="qty-adjust-excess", items=[{"order_item": self.item.id, "new_quantity": "60"}]),
            format="json",
        )
        self.assertEqual(preview.status_code, status.HTTP_200_OK, preview.data)
        self.assertTrue(any("采购过剩" in warning for warning in preview.data["warnings"]))
        response = self.client.post(
            f"/api/orders/{self.order.id}/quantity-adjustments/",
            self.payload(key="qty-adjust-excess", items=[{"order_item": self.item.id, "new_quantity": "60"}]),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        purchase_item.refresh_from_db()
        allocation.refresh_from_db()
        purchase.refresh_from_db()
        self.assertEqual(purchase_item.quantity, Decimal("120.00"))
        self.assertEqual(allocation.quantity, Decimal("120.00"))
        self.assertEqual(purchase.status, "ordered")
        self.assertTrue(response.data["adjustment"]["impact"]["warnings"])

    @override_settings(AUDIT_LOG_ENABLED=True)
    def test_success_is_audited_once_and_history_is_readable(self):
        user = get_user_model().objects.create_user(username="qty-adjust-auditor", password="secret")
        self.client.force_authenticate(user=user)
        payload = self.payload(key="qty-adjust-audited")
        response = self.client.post(f"/api/orders/{self.order.id}/quantity-adjustments/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        log = OperationLog.objects.get(entity="crm.order", object_id=str(self.order.id), action_label="调整销售订单数量")
        self.assertEqual(log.operator_id, user.id)
        self.assertEqual(log.before_data["items"][str(self.item.id)], "100.00")
        self.assertEqual(log.after_data["items"][str(self.item.id)], "150.00")
        self.assertEqual(log.metadata["quantity_adjustment_id"], response.data["adjustment"]["id"])
        history = self.client.get(f"/api/orders/{self.order.id}/quantity-adjustments/")
        self.assertEqual(history.status_code, status.HTTP_200_OK, history.data)
        self.assertEqual(len(history.data), 1)
        before_logs = OperationLog.objects.count()
        failed = self.client.post(
            f"/api/orders/{self.order.id}/quantity-adjustments/",
            self.payload(version=1, key="qty-adjust-audited-failed", items=[{"order_item": self.item.id, "new_quantity": "0"}]),
            format="json",
        )
        self.assertEqual(failed.status_code, status.HTTP_400_BAD_REQUEST, failed.data)
        self.assertEqual(OperationLog.objects.count(), before_logs)

    def test_history_serializer_redacts_financial_and_procurement_impact_without_finance_view(self):
        response = self.client.post(
            f"/api/orders/{self.order.id}/quantity-adjustments/",
            self.payload(key="qty-adjust-redaction"),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        adjustment = OrderQuantityAdjustment.objects.get(order=self.order)
        from crm.services.order_quantity_adjustments import serialize_adjustment

        redacted = serialize_adjustment(adjustment, include_financial=False)
        self.assertFalse(redacted["financial_visible"])
        self.assertIsNone(redacted["amount_delta"])
        self.assertNotIn("old_amount", redacted["lines"][0])
        self.assertNotIn("after_metrics", redacted["impact"])

    def test_paid_amount_over_new_contract_amount_is_rejected_without_side_effects(self):
        from crm.services.finance import record_transaction

        record_transaction({"plan": self.plan, "amount": Decimal("900"), "currency": "USD", "exchange_rate": Decimal("1"), "category": "客户收款"})
        before_plans = list(PaymentPlan.objects.filter(order=self.order).values("planned_amount", "settled_amount", "status"))
        response = self.client.post(
            f"/api/orders/{self.order.id}/quantity-adjustments/",
            self.payload(key="qty-adjust-paid-too-high", items=[{"order_item": self.item.id, "new_quantity": "60"}]),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.item.refresh_from_db()
        self.assertEqual(self.item.quantity, Decimal("100.00"))
        self.assertEqual(list(PaymentPlan.objects.filter(order=self.order).values("planned_amount", "settled_amount", "status")), before_plans)
        self.assertFalse(OrderQuantityAdjustment.objects.filter(order=self.order).exists())
        self.assertEqual(Transaction.objects.filter(order=self.order).count(), 1)

    def test_stale_version_and_normal_patch_cannot_bypass_dedicated_flow(self):
        response = self.client.post(
            f"/api/orders/{self.order.id}/quantity-adjustments/",
            self.payload(key="qty-adjust-first"),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        stale = self.client.post(
            f"/api/orders/{self.order.id}/quantity-adjustments/",
            self.payload(version=0, key="qty-adjust-stale", items=[{"order_item": self.item.id, "new_quantity": "140"}]),
            format="json",
        )
        self.assertEqual(stale.status_code, status.HTTP_409_CONFLICT, stale.data)
        ordinary = self.client.patch(
            f"/api/orders/{self.order.id}/",
            {"items": [{"sku": self.sku.id, "quantity": "140", "unit_price": "10"}]},
            format="json",
        )
        self.assertEqual(ordinary.status_code, status.HTTP_400_BAD_REQUEST, ordinary.data)

    def test_trade_unit_uses_saved_factor_and_preserves_snapshot(self):
        self.item.delete()
        unit = SKUTradeUnit.objects.create(
            sku=self.sku,
            name="箱",
            unit="箱",
            factor=Decimal("10"),
            allow_fraction=False,
            is_default=True,
        )
        item = self.order.items.create(
            sku=self.sku,
            quantity=Decimal("100"),
            unit_price=Decimal("10"),
            trade_unit=unit,
            trade_quantity=Decimal("10"),
            trade_unit_price=Decimal("100"),
            trade_snapshot={"name": "箱", "unit": "箱", "base_unit": "pcs", "factor": "10", "allow_fraction": False},
        )
        PaymentPlan.objects.filter(order=self.order).update(planned_amount=Decimal("1000"))
        response = self.client.post(
            f"/api/orders/{self.order.id}/quantity-adjustments/",
            self.payload(key="qty-adjust-boxes", items=[{"order_item": item.id, "new_trade_quantity": "15"}]),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        item.refresh_from_db()
        self.assertEqual(item.quantity, Decimal("150.00"))
        self.assertEqual(item.trade_quantity, Decimal("15.00"))
        self.assertEqual(item.trade_snapshot["factor"], "10")
