from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, TransactionTestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework.views import APIView

from crm.authentication import SessionAuthenticationWithChallenge
from crm.models import (
    AccessRole,
    Customer,
    EmployeeProfile,
    InventoryReservation,
    InventoryMovement,
    Order,
    OrderQuantityAdjustment,
    OperationLog,
    OrganizationUnit,
    PaymentPlan,
    Position,
    Product,
    Shipment,
    ShipmentItem,
    SKU,
    SKUTradeUnit,
    Transaction,
    RolePermission,
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

    def test_same_sku_multiple_lines_aggregate_demand_once_for_procurement_warning(self):
        from crm.models import PurchaseCostAllocation, PurchaseOrder, Supplier

        second = self.order.items.create(sku=self.sku, quantity=Decimal("20"), unit_price=Decimal("5"))
        self.plan.planned_amount = Decimal("1100")
        self.plan.save(update_fields=["planned_amount"])
        supplier = Supplier.objects.create(code="SUP-QTY-GROUP", name="共享采购供应商")
        purchase = PurchaseOrder.objects.create(
            purchase_no="PO-QTY-GROUP",
            supplier=supplier,
            order=self.order,
            order_date=date(2026, 10, 21),
            status="ordered",
        )
        purchase_item = purchase.items.create(sku=self.sku, quantity=Decimal("120"), unit_price=Decimal("7"))
        PurchaseCostAllocation.objects.filter(purchase_item=purchase_item).update(
            target_type="order",
            order=self.order,
            quantity=Decimal("120"),
        )
        payload = self.payload(key="qty-adjust-group", items=[{"order_item": self.item.id, "new_quantity": "60"}])
        preview = self.client.post(f"/api/orders/{self.order.id}/quantity-adjustments/preview/", payload, format="json")
        self.assertEqual(preview.status_code, status.HTTP_200_OK, preview.data)
        warnings = [warning for warning in preview.data["warnings"] if "采购过剩" in warning]
        self.assertEqual(len(warnings), 1)
        self.assertIn("40.00", warnings[0])
        response = self.client.post(f"/api/orders/{self.order.id}/quantity-adjustments/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(len(response.data["adjustment"]["lines"]), 1)
        second.refresh_from_db()
        self.assertEqual(second.quantity, Decimal("20.00"))
        self.assertEqual(len(response.data["adjustment"]["impact"]["after_metrics"]), 1)

    def test_noop_is_rejected_without_version_history_plan_or_audit_changes(self):
        before_version = self.order.quantity_change_version
        before_plans = list(PaymentPlan.objects.filter(order=self.order).values("planned_amount", "settled_amount", "status"))
        before_reservations = list(InventoryReservation.objects.filter(order_item=self.item).values("quantity"))
        before_adjustments = OrderQuantityAdjustment.objects.count()
        before_logs = OperationLog.objects.count()
        response = self.client.post(
            f"/api/orders/{self.order.id}/quantity-adjustments/",
            self.payload(key="qty-adjust-noop", items=[{"order_item": self.item.id, "new_quantity": "100.00"}]),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertIn("数量没有变化", response.data["detail"])
        self.order.refresh_from_db()
        self.assertEqual(self.order.quantity_change_version, before_version)
        self.assertEqual(list(PaymentPlan.objects.filter(order=self.order).values("planned_amount", "settled_amount", "status")), before_plans)
        self.assertEqual(list(InventoryReservation.objects.filter(order_item=self.item).values("quantity")), before_reservations)
        self.assertEqual(OrderQuantityAdjustment.objects.count(), before_adjustments)
        self.assertEqual(OperationLog.objects.count(), before_logs)

    def test_multi_line_adjustment_only_records_changed_lines(self):
        second = self.order.items.create(sku=self.sku, quantity=Decimal("20"), unit_price=Decimal("5"))
        self.plan.planned_amount = Decimal("1100")
        self.plan.save(update_fields=["planned_amount"])
        response = self.client.post(
            f"/api/orders/{self.order.id}/quantity-adjustments/",
            self.payload(
                key="qty-adjust-only-changed",
                items=[
                    {"order_item": self.item.id, "new_quantity": "150"},
                    {"order_item": second.id, "new_quantity": "20.00"},
                ],
            ),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual([line["order_item"] for line in response.data["adjustment"]["lines"]], [self.item.id])
        second.refresh_from_db()
        self.assertEqual(second.quantity, Decimal("20.00"))

    def test_invalid_precision_and_oversized_quantity_are_rejected_without_500(self):
        for key, value in (("qty-adjust-scientific", "1e100"), ("qty-adjust-oversized", "9999999999999.99"), ("qty-adjust-precision", "1.001")):
            response = self.client.post(
                f"/api/orders/{self.order.id}/quantity-adjustments/",
                self.payload(key=key, items=[{"order_item": self.item.id, "new_quantity": value}]),
                format="json",
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.item.refresh_from_db()
        self.assertEqual(self.item.quantity, Decimal("100.00"))
        self.assertFalse(OrderQuantityAdjustment.objects.filter(order=self.order).exists())

    def test_partial_payment_allows_both_safe_increase_and_decrease(self):
        from crm.services.finance import record_transaction

        record_transaction({"plan": self.plan, "amount": Decimal("200"), "currency": "USD", "exchange_rate": Decimal("1"), "category": "客户收款"})
        increase = self.client.post(
            f"/api/orders/{self.order.id}/quantity-adjustments/",
            self.payload(key="qty-adjust-paid-increase", items=[{"order_item": self.item.id, "new_quantity": "120"}]),
            format="json",
        )
        self.assertEqual(increase.status_code, status.HTTP_201_CREATED, increase.data)
        decrease = self.client.post(
            f"/api/orders/{self.order.id}/quantity-adjustments/",
            self.payload(version=1, key="qty-adjust-paid-decrease", items=[{"order_item": self.item.id, "new_quantity": "110"}]),
            format="json",
        )
        self.assertEqual(decrease.status_code, status.HTTP_201_CREATED, decrease.data)
        self.plan.refresh_from_db()
        self.assertEqual(sum(PaymentPlan.objects.filter(order=self.order).values_list("planned_amount", flat=True)), Decimal("1100.0000"))
        self.assertEqual(self.plan.settled_amount, Decimal("200.0000"))

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


    def test_real_receipt_shipment_payment_and_party_snapshots_are_unchanged(self):
        from crm.models import GoodsReceipt, PurchaseCostAllocation, PurchaseOrder, Supplier
        from crm.services.fulfillment import record_receipt, confirm_shipment, signed_inventory_quantity
        from crm.services.finance import record_transaction
        supplier = Supplier.objects.create(code="QTY-INTEGRATION-S", name="Original supplier")
        purchase = PurchaseOrder.objects.create(
            purchase_no="PO-QTY-INTEGRATION", supplier=supplier, order=self.order,
            order_date=date(2026, 10, 21), status="ordered", currency="USD",
        )
        line = purchase.items.create(sku=self.sku, quantity=100, unit_price=7)
        PurchaseCostAllocation.objects.update_or_create(purchase_item=line, target_type="order", order=self.order, defaults={"quantity": 100})
        record_receipt(line, {"quantity": "100", "unit_cost": "7", "receipt_date": date(2026, 10, 21)})
        confirm_shipment(self.order, {"shipment_date": date(2026, 10, 21), "items": [{"order_item": self.item.pk, "quantity": "50"}]})
        record_transaction({"plan": self.plan, "amount": Decimal("200"), "currency": "USD", "exchange_rate": Decimal("1"), "category": "客户收款"})
        self.order.customer_name_snapshot = "Customer at confirmation"
        self.order.customer_address_snapshot = "Original address"
        self.order.save(update_fields=["customer_name_snapshot", "customer_address_snapshot"])
        self.order.customer.name = "Customer renamed later"
        self.order.customer.save()
        protected = [PurchaseOrder, type(line), PurchaseCostAllocation, GoodsReceipt, Shipment, ShipmentItem, Transaction, InventoryMovement]
        before = {model._meta.label: list(model.objects.order_by("pk").values()) for model in protected}
        for version, quantity in enumerate(("150", "60")):
            result = self.client.post(
                f"/api/orders/{self.order.pk}/quantity-adjustments/",
                self.payload(version=version, key=f"facts-{version}", items=[{"order_item": self.item.pk, "new_quantity": quantity}]),
                format="json",
            )
            self.assertEqual(result.status_code, 201, result.data)
        self.assertEqual(before, {model._meta.label: list(model.objects.order_by("pk").values()) for model in protected})
        self.order.refresh_from_db()
        self.item.refresh_from_db()
        self.plan.refresh_from_db()
        self.assertEqual(self.order.order_no, "SO-QTY-ADJUST")
        self.assertEqual(self.order.customer_name_snapshot, "Customer at confirmation")
        self.assertEqual(self.order.customer_address_snapshot, "Original address")
        self.assertEqual(self.item.quantity, 60)
        self.assertEqual(self.order.total_amount, 600)
        self.assertEqual(self.plan.settled_amount, 200)
        self.assertEqual(signed_inventory_quantity(self.sku), 50)
        self.assertEqual(sum(self.item.reservations.values_list("quantity", flat=True)), 10)
        self.assertEqual(sum(self.order.payment_plans.exclude(status="cancelled").values_list("planned_amount", flat=True)), 600)

    def test_failure_after_financial_write_rolls_back_everything(self):
        from unittest.mock import patch
        before = list(self.order.payment_plans.values())
        with patch("crm.services.order_quantity_adjustments.rebalance_sku_reservations", side_effect=RuntimeError("reservation failure")):
            with self.assertRaises(RuntimeError):
                self.client.post(f"/api/orders/{self.order.pk}/quantity-adjustments/", self.payload(), format="json")
        self.item.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(self.item.quantity, 100)
        self.assertEqual(self.order.quantity_change_version, 0)
        self.assertFalse(self.order.quantity_adjustments.exists())
        self.assertEqual(before, list(self.order.payment_plans.values()))

    def test_historical_flag_cannot_bypass_dedicated_quantity_flow(self):
        Order.objects.filter(pk=self.order.pk).update(historical_only=True)
        for suffix in ("preview/", ""):
            response = self.client.post(f"/api/orders/{self.order.pk}/quantity-adjustments/{suffix}", self.payload(), format="json")
            self.assertEqual(response.status_code, 400, response.data)
        self.item.refresh_from_db()
        self.assertEqual(self.item.quantity, 100)

    def test_development_operator_is_explicitly_not_a_real_authenticated_actor(self):
        response = self.client.post(f"/api/orders/{self.order.pk}/quantity-adjustments/", self.payload(), format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertIsNone(response.data["adjustment"]["operator"])
        self.assertEqual(response.data["adjustment"]["operator_name"], "开发身份（未实名）")


class QuantityPreviewTransactionTests(TransactionTestCase):
    def test_preview_works_without_an_outer_test_transaction(self):
        customer = Customer.objects.create(code="PREVIEW-TX", name="Preview transaction")
        product = Product.objects.create(code="PREVIEW-TX", name="Preview product")
        sku = SKU.objects.create(product=product, sku="PREVIEW-TX")
        order = Order.objects.create(customer=customer, order_no="PREVIEW-TX", order_date=date(2026, 10, 25), status="confirmed")
        item = order.items.create(sku=sku, quantity=100, unit_price=10)
        PaymentPlan.objects.create(order=order, direction="receivable", currency="USD", planned_amount=1000)
        response = APIClient().post(f"/api/orders/{order.pk}/quantity-adjustments/preview/", {
            "version": 0, "reason": "Preview outside atomic request",
            "items": [{"order_item": item.pk, "new_quantity": "150"}],
        }, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data["can_submit"])
        self.assertFalse(order.quantity_adjustments.exists())


RBAC_SETTINGS = {
    "APP_STAGE": "production",
    "DEBUG": False,
    "DEVELOPMENT_SUPERADMIN": False,
    "RBAC_ENFORCEMENT": True,
}


@override_settings(**RBAC_SETTINGS)
class QuantityAdjustmentRBACApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.unit = OrganizationUnit.objects.create(name="数量变更测试部", code="QTY-RBAC-UNIT")
        self.position = Position.objects.create(unit=self.unit, name="测试员工", code="QTY-RBAC-STAFF")
        self.product = Product.objects.create(code="P-QTY-RBAC", name="数量权限产品")
        self.sku = SKU.objects.create(product=self.product, sku="SKU-QTY-RBAC", unit="pcs")

        self.role_a = AccessRole.objects.create(name="数量调整采购外权限", code="qty-rbac-a", default_data_scope="all")
        self.role_b = AccessRole.objects.create(name="数量调整完整权限", code="qty-rbac-b", default_data_scope="all")
        self.role_c = AccessRole.objects.create(name="数量调整本人订单", code="qty-rbac-c", default_data_scope="self")
        self.role_d = AccessRole.objects.create(name="数量调整外部员工", code="qty-rbac-d", default_data_scope="self")

        self.user_a = self.make_user("qty-rbac-a", self.role_a)
        self.user_b = self.make_user("qty-rbac-b", self.role_b)
        self.user_c = self.make_user("qty-rbac-c", self.role_c)
        self.user_d = self.make_user("qty-rbac-d", self.role_d)

        self.customer = Customer.objects.create(code="C-QTY-RBAC", name="权限数量客户", owner_profile=self.user_a.employee_profile)
        self.order = Order.objects.create(
            order_no="SO-QTY-RBAC",
            customer=self.customer,
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

        self.c_customer = Customer.objects.create(code="C-QTY-RBAC-C", name="本人范围客户", owner_profile=self.user_c.employee_profile)
        self.c_order = Order.objects.create(
            order_no="SO-QTY-RBAC-C",
            customer=self.c_customer,
            order_date=date(2026, 10, 21),
            currency="USD",
            exchange_rate=Decimal("1"),
            status="confirmed",
        )
        self.c_item = self.c_order.items.create(sku=self.sku, quantity=Decimal("30"), unit_price=Decimal("10"))
        PaymentPlan.objects.create(order=self.c_order, direction="receivable", currency="USD", planned_amount=Decimal("300"), status="open")

        self.grant(self.role_a, "orders", can_view=True, can_update=True)
        self.grant(self.role_b, "orders", can_view=True, can_update=True)
        self.grant(self.role_b, "finance", can_view=True)
        self.grant(self.role_b, "transactions", can_view=True)
        self.grant(self.role_b, "purchases", can_view=True)
        self.grant(self.role_c, "orders", can_view=True)
        self.grant(self.role_d, "orders", can_view=True, can_update=True)

    def make_user(self, username, role):
        user = get_user_model().objects.create_user(username=username, password="test-password")
        profile = EmployeeProfile.objects.create(
            user=user,
            display_name=username,
            unit=self.unit,
            position=self.position,
        )
        profile.roles.add(role)
        return user

    def grant(self, role, module, **values):
        defaults = {
            "can_view": False,
            "can_create": False,
            "can_update": False,
            "can_delete": False,
            "can_export": False,
            "can_import": False,
        }
        defaults.update(values)
        return RolePermission.objects.create(role=role, module=module, **defaults)

    def auth(self, user):
        self.client.force_authenticate(user=user)

    def test_orders_update_user_can_adjust_but_receives_no_finance_or_procurement_details(self):
        self.auth(self.user_a)
        payload = {
            "version": 0,
            "request_key": "qty-rbac-a-adjust",
            "reason": "权限边界测试",
            "items": [{"order_item": self.item.id, "new_quantity": "150"}],
        }
        preview = self.client.post(f"/api/orders/{self.order.id}/quantity-adjustments/preview/", payload, format="json")
        self.assertEqual(preview.status_code, status.HTTP_200_OK, preview.data)
        self.assertIsNone(preview.data["financial"]["amount_delta"])
        self.assertNotIn("old_amount", preview.data["lines"][0])
        self.assertNotIn("after", preview.data["lines"][0])
        self.assertNotIn("1000", repr(preview.data))
        response = self.client.post(f"/api/orders/{self.order.id}/quantity-adjustments/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertIsNone(response.data["adjustment"]["amount_delta"])
        self.assertNotIn("after_metrics", response.data["preview"])
        self.assertNotIn("after_metrics", response.data["adjustment"]["impact"])
        history = self.client.get(f"/api/orders/{self.order.id}/quantity-adjustments/")
        self.assertEqual(history.status_code, status.HTTP_200_OK, history.data)
        self.assertIsNone(history.data[0]["amount_delta"])
        workbench = self.client.get(f"/api/orders/{self.order.id}/workbench/")
        self.assertEqual(workbench.status_code, status.HTTP_200_OK, workbench.data)
        self.assertIsNone(workbench.data["order"]["total_amount"])
        self.assertIsNone(workbench.data["items"][0]["unit_price"])
        self.assertIsNone(workbench.data["items"][0]["amount"])

    def test_financial_rejection_for_orders_update_user_does_not_echo_amounts(self):
        self.plan.settled_amount = Decimal("900")
        self.plan.save(update_fields=["settled_amount"])
        self.auth(self.user_a)
        response = self.client.post(
            f"/api/orders/{self.order.id}/quantity-adjustments/",
            {
                "version": 0,
                "request_key": "qty-rbac-a-financial-block",
                "reason": "受限财务错误提示测试",
                "items": [{"order_item": self.item.id, "new_quantity": "60"}],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertIn("受权限保护的财务校验", response.data["detail"])
        self.assertNotIn("900", response.data["detail"])
        self.assertFalse(OrderQuantityAdjustment.objects.filter(order=self.order).exists())

    def test_procurement_warning_is_generic_without_purchases_view(self):
        from crm.models import PurchaseOrder, PurchaseCostAllocation, Supplier

        supplier = Supplier.objects.create(code="SUP-QTY-RBAC", name="受限采购供应商")
        purchase = PurchaseOrder.objects.create(
            purchase_no="PO-QTY-RBAC",
            supplier=supplier,
            order=self.order,
            order_date=date(2026, 10, 21),
            status="ordered",
        )
        purchase_item = purchase.items.create(sku=self.sku, quantity=Decimal("120"), unit_price=Decimal("7"))
        PurchaseCostAllocation.objects.filter(purchase_item=purchase_item).update(quantity=Decimal("120"))
        self.auth(self.user_a)
        response = self.client.post(
            f"/api/orders/{self.order.id}/quantity-adjustments/preview/",
            {
                "version": 0,
                "request_key": "qty-rbac-a-procurement-mask",
                "reason": "采购影响脱敏测试",
                "items": [{"order_item": self.item.id, "new_quantity": "60"}],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["warnings"], ["采购影响信息受权限保护。"])
        self.assertNotIn("before", response.data["lines"][0])
        self.assertNotIn("120", repr(response.data))

    def test_full_finance_and_procurement_user_can_read_complete_adjustment_impact(self):
        self.auth(self.user_a)
        payload = {
            "version": 0,
            "request_key": "qty-rbac-b-source",
            "reason": "准备完整权限读取测试",
            "items": [{"order_item": self.item.id, "new_quantity": "60"}],
        }
        created = self.client.post(f"/api/orders/{self.order.id}/quantity-adjustments/", payload, format="json")
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.data)
        self.client.force_authenticate(user=self.user_b)
        history = self.client.get(f"/api/orders/{self.order.id}/quantity-adjustments/")
        self.assertEqual(history.status_code, status.HTTP_200_OK, history.data)
        self.assertEqual(Decimal(str(history.data[0]["amount_delta"])), Decimal("-400.0000"))
        self.assertIn("before", history.data[0]["lines"][0])
        self.assertIn("after_metrics", history.data[0]["impact"])

    @patch.object(APIView, "authentication_classes", [SessionAuthenticationWithChallenge])
    def test_view_only_and_out_of_scope_users_cannot_submit_or_read_foreign_order(self):
        self.auth(self.user_c)
        own = self.client.get(f"/api/orders/{self.c_order.id}/quantity-adjustments/")
        self.assertEqual(own.status_code, status.HTTP_200_OK, own.data)
        blocked = self.client.post(
            f"/api/orders/{self.c_order.id}/quantity-adjustments/preview/",
            {"version": 0, "request_key": "qty-rbac-c-preview", "reason": "不应提交", "items": [{"order_item": self.c_item.id, "new_quantity": "31"}]},
            format="json",
        )
        self.assertEqual(blocked.status_code, status.HTTP_403_FORBIDDEN, blocked.data)
        self.auth(self.user_d)
        self.assertEqual(self.client.get(f"/api/orders/{self.order.id}/workbench/").status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.post(f"/api/orders/{self.order.id}/quantity-adjustments/preview/", {}).status_code, status.HTTP_404_NOT_FOUND)
        self.client.logout()
        self.assertEqual(self.client.get(f"/api/orders/{self.order.id}/quantity-adjustments/").status_code, status.HTTP_401_UNAUTHORIZED)

    @override_settings(AUDIT_LOG_ENABLED=True)
    def test_redacted_quantity_adjustment_audit_does_not_leak_financial_snapshot(self):
        self.auth(self.user_a)
        payload = {
            "version": 0,
            "request_key": "qty-rbac-a-audit",
            "reason": "审计脱敏测试",
            "items": [{"order_item": self.item.id, "new_quantity": "150"}],
        }
        created = self.client.post(f"/api/orders/{self.order.id}/quantity-adjustments/", payload, format="json")
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.data)
        logs = self.client.get("/api/operation-logs/?entity=crm.order&object_id=%s" % self.order.id)
        self.assertEqual(logs.status_code, status.HTTP_200_OK, logs.data)
        adjustment_log = next(row for row in logs.data["results"] if row["action_display"] == "调整销售订单数量")
        self.assertEqual(adjustment_log["metadata"]["summary"], "数量变更金额影响受权限保护。")
        self.assertNotIn("1000", repr(adjustment_log))
        self.assertNotIn("amount_delta", adjustment_log["changed_fields"])
