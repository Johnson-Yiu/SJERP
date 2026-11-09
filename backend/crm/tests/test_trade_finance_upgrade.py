from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.test import TestCase
from rest_framework.test import APIClient

from crm.models import AdvanceAllocation, Customer, FinancePlanWriteoff, FinancePlanWriteoffCorrection, GoodsReceipt, InventoryMovement, InventoryReservation, Order, PaymentPlan, Product, PurchaseOrder, Shipment, SKU, Supplier, Transaction
from crm.services.finance import allocate_advance, ensure_default_payment_plans, order_receivable_state, record_contract_payment, record_transaction, void_transaction
from crm.services.profit import order_profit_summary
from crm.services.fulfillment import allocate_order, confirm_shipment, order_item_metrics, record_receipt, reverse_receipt, reverse_shipment, sku_metrics
from crm.services.purchase_costs import rebuild_default_cost_allocations


class TradeFinanceUpgradeTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.day = date(2026, 9, 7)
        self.customer = Customer.objects.create(code="UP-B", name="Upgrade Buyer")
        self.supplier = Supplier.objects.create(code="UP", name="Upgrade Supplier")
        self.sku = SKU.objects.create(sku="UP-SKU", product=Product.objects.create(code="UP-P", name="Light"))
        self.order = Order.objects.create(order_no="UP-SO", customer=self.customer, order_date=self.day, currency="USD", exchange_rate=7, status="confirmed")
        self.item = self.order.items.create(sku=self.sku, quantity=10, unit_price=10)
        self.purchase = PurchaseOrder.objects.create(purchase_no="UP-PO", supplier=self.supplier, order=self.order, order_date=self.day, status="ordered", currency="USD", exchange_rate=7)
        self.purchase_item = self.purchase.items.create(sku=self.sku, quantity=10, unit_price=5)

    def stock(self, quantity):
        return InventoryMovement.objects.create(movement_no=f"UP-IN-{InventoryMovement.objects.count()}", movement_date=self.day, type="adjust_in", sku=self.sku, quantity=quantity)

    def receive(self, quantity):
        return record_receipt(self.purchase_item, {"quantity": Decimal(quantity), "receipt_date": self.day, "unit_cost": Decimal(5)})

    def ship(self, quantity):
        return confirm_shipment(self.order, {"shipment_date": self.day, "items": [{"order_item": self.item.pk, "quantity": Decimal(quantity)}]})

    def _shipment_reversal_snapshot(self, shipment):
        shipment.refresh_from_db()
        self.order.refresh_from_db()
        line = shipment.items.get()
        return {
            "movement_count": InventoryMovement.objects.count(),
            "actual": sku_metrics(self.sku)["actual_quantity"],
            "reserved": sku_metrics(self.sku)["reserved_quantity"],
            "reservation_count": InventoryReservation.objects.filter(sku=self.sku).count(),
            "order_status": self.order.status,
            "shipment_status": shipment.status,
            "shipment_reversed_at": shipment.reversed_at,
            "shipment_reversal_reason": shipment.reversal_reason,
            "line_reversal_id": line.reversal_inventory_movement_id,
        }

    def _assert_malformed_shipment_reversal_is_atomic(self, mutate):
        self.receive("10")
        shipment = self.ship("10")
        line = shipment.items.get()
        mutate(line, line.inventory_movement)
        before = self._shipment_reversal_snapshot(shipment)

        with self.assertRaisesMessage(ValidationError, "原销售出库流水缺失或异常，无法安全冲销，请先检查库存流水。"):
            reverse_shipment(shipment, "原流水异常")

        self.assertEqual(self._shipment_reversal_snapshot(shipment), before)

    def plan(self):
        return PaymentPlan.objects.create(order=self.order, direction="receivable", currency="USD", planned_amount=100)

    def test_customer_receipt_settles_selected_plan_first(self):
        first = PaymentPlan.objects.create(order=self.order, direction="receivable", currency="USD", planned_amount=50, due_date=self.day)
        selected = PaymentPlan.objects.create(order=self.order, direction="receivable", currency="USD", planned_amount=50, due_date=self.day + timedelta(days=1))
        row = record_transaction({"plan": selected, "kind": "customer_receipt", "amount": Decimal("20"), "category": "客户收款"})
        first.refresh_from_db()
        selected.refresh_from_db()
        self.assertEqual(row.plan_id, selected.pk)
        self.assertEqual(selected.settled_amount, Decimal("20"))
        self.assertEqual(first.settled_amount, Decimal("0"))

    def test_historical_receipt_without_reference_rate_is_not_converted(self):
        from crm.serializers import TransactionSerializer
        receipt = Transaction.objects.create(transaction_no="UP-MISSING-RATE", transaction_date=self.day,
            direction="income", kind="unallocated_advance", category="客户收款", amount=80,
            currency="USD", exchange_rate=None, reference_rate_missing=True, customer=self.customer,
            status="confirmed")
        data = TransactionSerializer(receipt).data
        self.assertIsNone(data["exchange_rate"])
        self.assertIsNone(data["rmb_amount"])
        self.assertTrue(data["reference_rate_missing"])
        response = self.client.get("/api/finance-dashboard/", {"date_from": "2026-09-01", "date_to": "2026-09-30"})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["cash_basis"]["missing_reference_count"], 1)
        self.assertIn("未录入参考汇率", response.data["cash_basis"]["note"])
        self.assertEqual(response.data["metrics"]["income_rmb"], 0)
        from crm.services.cash_events import source_snapshot, source_snapshot_matches
        receipt.refresh_from_db()
        old_snapshot = source_snapshot(receipt)
        old_snapshot.update(remittance_amount=None, bank_fee_amount="0.0000", fee_responsibility="", settlement_amount="0.0000", reference_rate_missing=True, exchange_rate=None)
        self.assertTrue(source_snapshot_matches(receipt, old_snapshot))
        old_snapshot["bank_fee_amount"] = "1.0000"
        self.assertFalse(source_snapshot_matches(receipt, old_snapshot))

    def test_effective_writeoff_updates_order_state_and_profit(self):
        plan = self.plan()
        receipt = record_transaction({"plan": plan, "kind": "customer_receipt", "amount": Decimal("90"), "category": "客户收款"})
        writeoff = FinancePlanWriteoff.objects.create(plan=plan, source_transaction=receipt, amount=10, reason="已授权抹零", request_key="read-writeoff", request_hash="a", confirmed_actor={})
        plan.refresh_from_db()
        plan.status = "settled"
        plan.save(update_fields=["status"])
        self.assertEqual(order_receivable_state(self.order, [plan])["state"], "settled")
        self.assertEqual(order_profit_summary(self.order)["sales_rmb"], Decimal("630"))
        FinancePlanWriteoffCorrection.objects.create(writeoff=writeoff, amount=4, reason="更正抹零金额", request_key="read-correction", request_hash="b", actor={})
        plan.status = "open"
        plan.save(update_fields=["status"])
        self.assertEqual(order_receivable_state(self.order, [plan])["state"], "partial")
        self.assertEqual(plan.remaining_amount, Decimal("4"))
        self.assertEqual(order_profit_summary(self.order)["sales_rmb"], Decimal("658"))

    def test_completed_receipts_do_not_reduce_another_open_purchase_in_transit(self):
        self.receive("10")
        second = PurchaseOrder.objects.create(purchase_no="UP-PO-2", supplier=self.supplier, order_date=self.day, status="ordered")
        second.items.create(sku=self.sku, quantity=4, unit_price=5)
        self.assertEqual(sku_metrics(self.sku)["in_transit_quantity"], 4)

    def test_partial_shipping_releases_only_shipped_reservation(self):
        self.receive("10")
        self.ship("4")
        metrics = sku_metrics(self.sku)
        self.assertEqual(metrics["actual_quantity"], 6)
        self.assertEqual(metrics["reserved_quantity"], 6)
        self.assertEqual(metrics["available_quantity"], 0)
        self.assertEqual(order_item_metrics(self.item)["to_procure_quantity"], 0)
        self.ship("6")
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "shipped")
        self.assertEqual(sku_metrics(self.sku)["reserved_quantity"], 0)

    def test_shipping_cannot_consume_other_order_reservations(self):
        self.stock(5)
        other = Order.objects.create(order_no="UP-SO-2", customer=self.customer, order_date=self.day - timedelta(days=1), status="confirmed")
        other.items.create(sku=self.sku, quantity=5, unit_price=1)
        allocate_order(other)
        with self.assertRaises(ValidationError):
            self.ship("1")
        self.assertFalse(self.order.shipments.exists())

    def test_cancelled_order_and_purchase_reject_operations(self):
        self.order.status = "cancelled"
        self.order.save()
        self.purchase.status = "cancelled"
        self.purchase.save()
        with self.assertRaises(ValidationError):
            self.receive("1")
        with self.assertRaises(ValidationError):
            self.ship("1")

    def test_receipt_reversal_restores_inventory_received_quantity_and_purchase_status(self):
        receipt = self.receive("10")
        reverse_receipt(receipt, "数量录错")

        receipt.refresh_from_db()
        self.purchase.refresh_from_db()
        self.purchase_item.refresh_from_db()
        self.assertEqual(receipt.quantity, Decimal("10"))
        self.assertIsNotNone(receipt.reversal_inventory_movement_id)
        self.assertEqual(receipt.reversal_inventory_movement.source_type, "reversal")
        self.assertEqual(sku_metrics(self.sku)["actual_quantity"], Decimal("0"))
        self.assertEqual(self.purchase_item.received_quantity, Decimal("0"))
        self.assertEqual(self.purchase_item.remaining_quantity, Decimal("10"))
        self.assertEqual(self.purchase.status, "ordered")

    def test_partial_receipt_reversal_keeps_remaining_received_quantity_and_status(self):
        self.receive("4")
        second = self.receive("6")
        reverse_receipt(second, "第二批数量录错")

        self.purchase.refresh_from_db()
        self.purchase_item.refresh_from_db()
        self.assertEqual(self.purchase_item.received_quantity, Decimal("4"))
        self.assertEqual(self.purchase_item.remaining_quantity, Decimal("6"))
        self.assertEqual(self.purchase.status, "partial")

    def test_receipt_cannot_be_reversed_twice(self):
        receipt = self.receive("10")
        reverse_receipt(receipt, "首次冲销")
        with self.assertRaises(ValidationError):
            reverse_receipt(receipt, "重复冲销")

    def test_receipt_reversal_rejects_insufficient_actual_inventory_without_changes(self):
        receipt = self.receive("10")
        self.ship("6")
        self.purchase.refresh_from_db()
        before_movement_count = InventoryMovement.objects.count()
        before_status = self.purchase.status
        with self.assertRaises(ValidationError):
            reverse_receipt(receipt, "库存已被消耗")

        receipt.refresh_from_db()
        self.purchase.refresh_from_db()
        self.assertIsNone(receipt.reversal_inventory_movement_id)
        self.assertEqual(InventoryMovement.objects.count(), before_movement_count)
        self.assertEqual(self.purchase.status, before_status)
        self.assertEqual(sku_metrics(self.sku)["actual_quantity"], Decimal("4"))

    def test_receipt_reversal_rebalances_current_sku_reservations(self):
        receipt = self.receive("10")
        self.assertEqual(sku_metrics(self.sku)["reserved_quantity"], Decimal("10"))
        reverse_receipt(receipt, "冲销并释放预留")
        metrics = sku_metrics(self.sku)
        self.assertLessEqual(metrics["reserved_quantity"], metrics["actual_quantity"])
        self.assertEqual(InventoryReservation.objects.filter(sku=self.sku).count(), 0)

    def test_receipt_reversal_api_requires_reason_and_succeeds(self):
        receipt = self.receive("10")
        url = f"/api/purchase-orders/{self.purchase.pk}/receipts/{receipt.pk}/reverse/"
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        receipt.refresh_from_db()
        self.assertIsNone(receipt.reversal_inventory_movement_id)

        response = self.client.post(url, {"reason": "API 冲销原因"}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        receipt.refresh_from_db()
        self.assertEqual(response.data["id"], receipt.id)
        self.assertEqual(response.data["reversal_reason"], "API 冲销原因")
        self.assertIsNotNone(response.data["reversal_inventory_movement"])

    def test_shipment_reversal_restores_inventory_order_progress_and_reservation(self):
        self.receive("10")
        shipment = self.ship("10")
        original_movement = shipment.items.get().inventory_movement
        reverse_shipment(shipment, "发货数量录错")

        shipment.refresh_from_db()
        self.order.refresh_from_db()
        self.item.refresh_from_db()
        self.assertEqual(shipment.status, "cancelled")
        self.assertIsNotNone(shipment.reversed_at)
        self.assertEqual(sku_metrics(self.sku)["actual_quantity"], Decimal("10"))
        self.assertEqual(order_item_metrics(self.item)["shipped_quantity"], Decimal("0"))
        self.assertEqual(order_item_metrics(self.item)["unshipped_quantity"], Decimal("10"))
        self.assertEqual(self.order.status, "confirmed")
        self.assertLessEqual(sku_metrics(self.sku)["reserved_quantity"], sku_metrics(self.sku)["actual_quantity"])
        self.assertEqual(original_movement.type, "sale_out")
        reversal = shipment.items.get().reversal_inventory_movement
        self.assertEqual(reversal.type, "adjust_in")
        self.assertEqual(reversal.source_type, "reversal")

    def test_reversing_second_split_shipment_keeps_first_shipment_active(self):
        self.receive("10")
        self.ship("4")
        second = self.ship("6")
        reverse_shipment(second, "第二批发货录错")

        self.order.refresh_from_db()
        self.item.refresh_from_db()
        self.assertEqual(self.order.status, "confirmed")
        self.assertEqual(order_item_metrics(self.item)["shipped_quantity"], Decimal("4"))
        self.assertEqual(order_item_metrics(self.item)["unshipped_quantity"], Decimal("6"))
        self.assertEqual(sku_metrics(self.sku)["actual_quantity"], Decimal("6"))
        self.assertEqual(sku_metrics(self.sku)["reserved_quantity"], Decimal("6"))

    def test_shipment_cannot_be_reversed_twice(self):
        self.stock("10")
        shipment = self.ship("10")
        reverse_shipment(shipment, "首次冲销")
        with self.assertRaises(ValidationError):
            reverse_shipment(shipment, "重复冲销")

    def test_multi_sku_shipment_reversal_rebalances_each_sku(self):
        second_sku = SKU.objects.create(sku="UP-SKU-2", product=Product.objects.create(code="UP-P-2", name="Downlight"))
        second_item = self.order.items.create(sku=second_sku, quantity=5, unit_price=8)
        self.stock("10")
        InventoryMovement.objects.create(movement_no="UP-IN-SECOND", movement_date=self.day, type="adjust_in", sku=second_sku, quantity=5)
        shipment = confirm_shipment(self.order, {"shipment_date": self.day, "items": [
            {"order_item": self.item.pk, "quantity": Decimal("10")},
            {"order_item": second_item.pk, "quantity": Decimal("5")},
        ]})
        reverse_shipment(shipment, "多 SKU 发货录错")

        self.assertEqual(InventoryMovement.objects.filter(order=self.order, source_type="reversal", type="adjust_in").count(), 2)
        self.assertEqual(sku_metrics(self.sku)["actual_quantity"], Decimal("10"))
        self.assertEqual(sku_metrics(second_sku)["actual_quantity"], Decimal("5"))
        self.assertLessEqual(sku_metrics(self.sku)["reserved_quantity"], sku_metrics(self.sku)["actual_quantity"])
        self.assertLessEqual(sku_metrics(second_sku)["reserved_quantity"], sku_metrics(second_sku)["actual_quantity"])

    def test_customer_addon_shipment_reversal_removes_supplement_and_cancels_plan(self):
        self.stock("20")
        shipment = confirm_shipment(self.order, {"shipment_date": self.day, "items": [{
            "order_item": self.item.pk, "quantity": Decimal("11"), "overage_reason": "customer_addon",
        }]})
        overage = shipment.items.get(is_overage=True)
        plan = overage.generated_payment_plan
        self.assertEqual(overage.source_order_item_id, self.item.id)
        reverse_shipment(shipment, "包含增补")
        shipment.refresh_from_db()
        plan.refresh_from_db()
        overage.refresh_from_db()
        self.assertEqual(shipment.status, "cancelled")
        self.assertEqual(self.order.items.count(), 1)
        self.assertEqual(plan.status, "cancelled")
        self.assertEqual(overage.order_item_id, self.item.id)

    def test_gift_overage_reversal_removes_zero_price_supplement(self):
        self.stock("20")
        shipment = confirm_shipment(self.order, {"shipment_date": self.day, "items": [{
            "order_item": self.item.pk, "quantity": Decimal("11"), "overage_reason": "gift_or_sample",
        }]})
        self.assertFalse(shipment.items.get(is_overage=True).generated_payment_plan_id)
        reverse_shipment(shipment, "赠品录错")
        shipment.refresh_from_db()
        self.assertEqual(self.order.items.count(), 1)
        self.assertEqual(shipment.status, "cancelled")

    def test_paid_customer_addon_cannot_be_reversed(self):
        self.stock("20")
        shipment = confirm_shipment(self.order, {"shipment_date": self.day, "items": [{
            "order_item": self.item.pk, "quantity": Decimal("11"), "overage_reason": "customer_addon",
        }]})
        plan = shipment.items.get(is_overage=True).generated_payment_plan
        record_transaction({"plan": plan, "amount": Decimal("10"), "currency": self.order.currency, "exchange_rate": self.order.exchange_rate, "category": "客户收款"})
        with self.assertRaisesMessage(ValidationError, "已经发生收款或预收款核销"):
            reverse_shipment(shipment, "已收款")
        shipment.refresh_from_db()
        self.assertEqual(shipment.status, "confirmed")

    def test_historical_customer_addon_without_payment_plan_cannot_be_reversed(self):
        self.stock("20")
        shipment = confirm_shipment(self.order, {"shipment_date": self.day, "items": [{
            "order_item": self.item.pk, "quantity": Decimal("11"), "overage_reason": "customer_addon",
        }]})
        overage = shipment.items.get(is_overage=True)
        overage.generated_payment_plan = None
        overage.save(update_fields=["generated_payment_plan"])
        before_movements = InventoryMovement.objects.count()
        before_items = self.order.items.count()
        before_plans = PaymentPlan.objects.count()

        with self.assertRaisesMessage(ValidationError, "该历史客户追加记录缺少应收计划关联，需要人工核对后才能冲销。"):
            reverse_shipment(shipment, "历史追加缺少应收计划")

        shipment.refresh_from_db()
        self.assertEqual(shipment.status, "confirmed")
        self.assertEqual(InventoryMovement.objects.count(), before_movements)
        self.assertEqual(self.order.items.count(), before_items)
        self.assertEqual(PaymentPlan.objects.count(), before_plans)

    def test_reversal_movements_inherit_trade_snapshots(self):
        receipt = self.receive("10")
        receipt.trade_quantity = Decimal("2")
        receipt.trade_unit_price = Decimal("2.5000")
        receipt.trade_snapshot = {"unit": "箱", "base_unit": "个", "factor": "5", "name": "五个装"}
        receipt.save(update_fields=["trade_quantity", "trade_unit_price", "trade_snapshot"])
        reverse_receipt(receipt, "采购规格录错")
        receipt.refresh_from_db()
        receipt_reversal = receipt.reversal_inventory_movement
        self.assertEqual(receipt_reversal.trade_quantity, Decimal("2"))
        self.assertEqual(receipt_reversal.trade_unit_price, Decimal("2.5000"))
        self.assertEqual(receipt_reversal.trade_snapshot, receipt.trade_snapshot)

        self.stock("10")
        shipment = self.ship("10")
        line = shipment.items.get()
        line.trade_quantity = Decimal("2")
        line.trade_unit_price = Decimal("5.0000")
        line.trade_snapshot = {"unit": "箱", "base_unit": "个", "factor": "5", "name": "五个装"}
        line.save(update_fields=["trade_quantity", "trade_unit_price", "trade_snapshot"])
        reverse_shipment(shipment, "销售规格录错")
        shipment_reversal = shipment.items.get().reversal_inventory_movement
        self.assertEqual(shipment_reversal.trade_quantity, Decimal("2"))
        self.assertEqual(shipment_reversal.trade_unit_price, Decimal("5.0000"))
        self.assertEqual(shipment_reversal.trade_snapshot, line.trade_snapshot)

    def test_shipment_reversal_api_requires_reason_and_succeeds(self):
        self.stock("10")
        shipment = self.ship("10")
        url = f"/api/shipments/{shipment.pk}/reverse/"
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        shipment.refresh_from_db()
        self.assertEqual(shipment.status, "confirmed")

        response = self.client.post(url, {"reason": "API 发货冲销"}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        shipment.refresh_from_db()
        self.assertEqual(response.data["status"], "cancelled")
        self.assertEqual(response.data["reversal_reason"], "API 发货冲销")
        self.assertTrue(response.data["reversal_inventory_movement_ids"])

    def test_shipment_reversal_rejects_missing_original_movement_without_changes(self):
        self.receive("10")
        shipment = self.ship("10")
        line = shipment.items.get()
        line.inventory_movement = None
        line.save(update_fields=["inventory_movement"])
        self.order.refresh_from_db()
        before_status = self.order.status
        before_actual = sku_metrics(self.sku)["actual_quantity"]
        before_reserved = sku_metrics(self.sku)["reserved_quantity"]
        before_reversals = InventoryMovement.objects.filter(source_type="reversal").count()

        with self.assertRaisesMessage(ValidationError, "原销售出库流水缺失或异常，无法安全冲销，请先检查库存流水。"):
            reverse_shipment(shipment, "原流水缺失")

        shipment.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(shipment.status, "confirmed")
        self.assertEqual(self.order.status, before_status)
        self.assertEqual(sku_metrics(self.sku)["actual_quantity"], before_actual)
        self.assertEqual(sku_metrics(self.sku)["reserved_quantity"], before_reserved)
        self.assertEqual(InventoryMovement.objects.filter(source_type="reversal").count(), before_reversals)

    def test_shipment_reversal_rejects_sku_mismatch_atomically(self):
        second_sku = SKU.objects.create(sku="UP-SKU-MISMATCH", product=Product.objects.create(code="UP-P-MISMATCH", name="Mismatch Light"))
        self._assert_malformed_shipment_reversal_is_atomic(
            lambda _line, movement: (setattr(movement, "sku", second_sku), movement.save(update_fields=["sku"]))
        )

    def test_shipment_reversal_rejects_order_mismatch_atomically(self):
        other_order = Order.objects.create(order_no="UP-SO-MISMATCH", customer=self.customer, order_date=self.day)
        self._assert_malformed_shipment_reversal_is_atomic(
            lambda _line, movement: (setattr(movement, "order", other_order), movement.save(update_fields=["order"]))
        )

    def test_shipment_reversal_rejects_quantity_mismatch_atomically(self):
        def mutate(_line, movement):
            movement.quantity = Decimal("9")
            movement.save(update_fields=["quantity"])

        self._assert_malformed_shipment_reversal_is_atomic(mutate)

    def test_shipment_reversal_rejects_source_type_mismatch_atomically(self):
        def mutate(_line, movement):
            movement.source_type = "receipt"
            movement.save(update_fields=["source_type"])

        self._assert_malformed_shipment_reversal_is_atomic(mutate)

    def test_cancelled_order_rejects_shipment_reversal_atomically(self):
        self.stock("10")
        shipment = self.ship("10")
        self.order.status = "cancelled"
        self.order.save(update_fields=["status"])
        before = self._shipment_reversal_snapshot(shipment)

        with self.assertRaisesMessage(ValidationError, "已完成或已取消的订单不能冲销发货。"):
            reverse_shipment(shipment, "取消订单不应冲销")

        self.assertEqual(self._shipment_reversal_snapshot(shipment), before)

    def test_receipt_reversal_second_call_has_no_second_side_effect(self):
        receipt = self.receive("10")
        reverse_receipt(receipt, "首次冲销")
        receipt.refresh_from_db()
        self.purchase.refresh_from_db()
        before = {
            "movement_count": InventoryMovement.objects.count(),
            "receipt_reversal_id": receipt.reversal_inventory_movement_id,
            "reversed_at": receipt.reversed_at,
            "reason": receipt.reversal_reason,
            "purchase_status": self.purchase.status,
            "received": self.purchase_item.received_quantity,
            "actual": sku_metrics(self.sku)["actual_quantity"],
            "reserved": sku_metrics(self.sku)["reserved_quantity"],
        }

        with self.assertRaisesMessage(ValidationError, "该入库记录已经冲销，不能重复操作。"):
            reverse_receipt(receipt, "重复冲销")

        receipt.refresh_from_db()
        self.purchase.refresh_from_db()
        after = {
            "movement_count": InventoryMovement.objects.count(),
            "receipt_reversal_id": receipt.reversal_inventory_movement_id,
            "reversed_at": receipt.reversed_at,
            "reason": receipt.reversal_reason,
            "purchase_status": self.purchase.status,
            "received": self.purchase_item.received_quantity,
            "actual": sku_metrics(self.sku)["actual_quantity"],
            "reserved": sku_metrics(self.sku)["reserved_quantity"],
        }
        self.assertEqual(after, before)

    def test_shipment_reversal_second_call_has_no_second_side_effect(self):
        self.stock("10")
        shipment = self.ship("10")
        reverse_shipment(shipment, "首次冲销")
        before = self._shipment_reversal_snapshot(shipment)

        with self.assertRaisesMessage(ValidationError, "该发货单已经冲销，不能重复操作。"):
            reverse_shipment(shipment, "重复冲销")

        self.assertEqual(self._shipment_reversal_snapshot(shipment), before)

    def test_malformed_and_foreign_shipment_lines_return_400(self):
        for line in ({"quantity": "abc"}, {"order_item": 999999, "quantity": "1"}):
            response = self.client.post(f"/api/orders/{self.order.pk}/ship/", {"shipment_date": self.day.isoformat(), "items": [line]}, format="json")
            self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(self.order.shipments.exists())

    def test_manual_batch_cannot_overdraw_same_sku_or_spoof_automatic_movement(self):
        self.stock(5)
        response = self.client.post("/api/inventory-movements/batch/", {"type": "sample_out", "movement_date": self.day.isoformat(), "items": [{"sku": self.sku.pk, "quantity": 3}, {"sku": self.sku.pk, "quantity": 3}]}, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(sku_metrics(self.sku)["actual_quantity"], 5)
        response = self.client.post("/api/inventory-movements/batch/", {"type": "adjust_in", "movement_date": self.day.isoformat(), "items": [{"sku": self.sku.pk, "quantity": 1, "type": "sale_out"}]}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_consumed_manual_inbound_cannot_be_deleted(self):
        movement = self.stock(10)
        allocate_order(self.order)
        response = self.client.delete(f"/api/inventory-movements/{movement.pk}/")
        self.assertEqual(response.status_code, 400)
        self.assertTrue(InventoryMovement.objects.filter(pk=movement.pk).exists())

    def test_contract_payment_settles_all_installments_and_void_restores_them(self):
        self.purchase.payment_terms_snapshot = [
            {"label": "预付款", "ratio": "0.30", "due_basis": "order_date", "offset_days": 0},
            {"label": "尾款", "ratio": "0.70", "due_basis": "no_date", "offset_days": 0},
        ]
        self.purchase.save(update_fields=["payment_terms_snapshot"])
        ensure_default_payment_plans(self.purchase)
        response = self.client.post(f"/api/purchase-orders/{self.purchase.pk}/pay/", {"transaction_date": self.day.isoformat(), "amount": "50", "currency": "USD", "exchange_rate": "7"}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertFalse(self.purchase.payment_plans.filter(status="open").exists())
        self.assertEqual(self.purchase.paid_amount, 50)
        self.assertFalse(Transaction.objects.filter(kind="unallocated_advance").exists())
        void_transaction(Transaction.objects.get(pk=response.data["id"]), "付款录入错误")
        self.assertEqual(self.purchase.paid_amount, 0)
        self.assertEqual(self.purchase.payment_plans.filter(status="open", settled_amount=0).count(), 2)

    def test_advance_allocation_changes_contract_balance_without_duplicating_cash(self):
        plan = self.plan()
        advance = record_transaction({"transaction_date": self.day, "direction": "income", "kind": "unallocated_advance", "category": "预收", "customer": self.customer, "amount": 80, "currency": "USD", "exchange_rate": 7})
        allocate_advance(advance, plan, 60)
        self.assertEqual(self.order.paid_amount, 60)
        workbench = self.client.get(f'/api/orders/{self.order.pk}/workbench/').data
        self.assertEqual(workbench['payment_summary']['paid_amount'], 60)
        self.assertEqual(workbench['advance_allocations'][0]['amount'], 60)
        report = self.client.get("/api/finance-dashboard/", {"date_from": "2026-09-01", "date_to": "2026-09-30"}).data
        self.assertEqual(report["metrics"]["income_rmb"], 560)
        self.assertEqual(report["metrics"]["advance_receipt_rmb"], 140)
        void_transaction(advance, "预收款录入错误")
        plan.refresh_from_db()
        self.assertEqual(plan.settled_amount, 0)
        self.assertEqual(self.order.paid_amount, 0)
        self.assertFalse(advance.allocations.get().is_active)

    def test_advance_rejects_wrong_direction_and_cancelled_plan(self):
        plan = self.plan()
        advance = Transaction.objects.create(transaction_no="UP-ADV", transaction_date=self.day, direction="expense", kind="unallocated_advance", category="advance", customer=self.customer, amount=10, currency="USD")
        with self.assertRaises(ValidationError):
            allocate_advance(advance, plan, 5)
        advance.direction = "income"
        advance.save()
        plan.status = "cancelled"
        plan.save()
        with self.assertRaises(ValidationError):
            allocate_advance(advance, plan, 5)

    def test_advance_allocation_rejects_cross_party_direction_currency_and_closed_plan_atomically(self):
        other_customer = Customer.objects.create(code="UP-C-OTHER", name="Other Upgrade Buyer")
        other_order = Order.objects.create(order_no="UP-SO-OTHER", customer=other_customer, order_date=self.day, currency="USD", status="confirmed")
        other_plan = PaymentPlan.objects.create(order=other_order, direction="receivable", currency="USD", planned_amount=Decimal("50"))
        eur_order = Order.objects.create(order_no="UP-SO-EUR", customer=self.customer, order_date=self.day, currency="EUR", status="confirmed")
        eur_plan = PaymentPlan.objects.create(order=eur_order, direction="receivable", currency="EUR", planned_amount=Decimal("50"))
        other_supplier = Supplier.objects.create(code="UO", name="Other Upgrade Supplier")
        other_purchase = PurchaseOrder.objects.create(purchase_no="UP-PO-OTHER", supplier=other_supplier, order_date=self.day, status="ordered", currency="USD")
        payable_plan = PaymentPlan.objects.create(purchase_order=other_purchase, direction="payable", currency="USD", planned_amount=Decimal("50"))
        cancelled_plan = PaymentPlan.objects.create(order=self.order, direction="receivable", currency="USD", planned_amount=Decimal("50"), status="cancelled")

        advances = [
            Transaction.objects.create(transaction_no="UP-E33-CUSTOMER", transaction_date=self.day, direction="income", kind="unallocated_advance", category="advance", customer=self.customer, amount=10, currency="USD"),
            Transaction.objects.create(transaction_no="UP-E33-SUPPLIER", transaction_date=self.day, direction="expense", kind="unallocated_payment", category="advance", supplier=self.supplier, amount=10, currency="USD"),
            Transaction.objects.create(transaction_no="UP-E33-DIRECTION", transaction_date=self.day, direction="expense", kind="unallocated_payment", category="advance", supplier=self.supplier, amount=10, currency="USD"),
            Transaction.objects.create(transaction_no="UP-E33-CURRENCY", transaction_date=self.day, direction="income", kind="unallocated_advance", category="advance", customer=self.customer, amount=10, currency="USD"),
            Transaction.objects.create(transaction_no="UP-E33-CLOSED", transaction_date=self.day, direction="income", kind="unallocated_advance", category="advance", customer=self.customer, amount=10, currency="USD"),
        ]
        cases = [
            ("customer", advances[0], other_plan),
            ("supplier", advances[1], payable_plan),
            ("direction", advances[2], self.plan()),
            ("currency", advances[3], eur_plan),
            ("closed", advances[4], cancelled_plan),
        ]
        before_allocations = AdvanceAllocation.objects.count()
        before_advance_amounts = {row.pk: row.allocated_amount for row in advances}
        before_plans = {plan.pk: (plan.status, plan.settled_amount) for _, _, plan in cases}
        for label, advance, plan in cases:
            with self.subTest(label=label):
                with self.assertRaises(ValidationError):
                    allocate_advance(advance, plan, Decimal("5"))
        self.assertEqual(AdvanceAllocation.objects.count(), before_allocations)
        self.assertEqual({row.pk: Transaction.objects.get(pk=row.pk).allocated_amount for row in advances}, before_advance_amounts)
        self.assertEqual({plan.pk: (PaymentPlan.objects.get(pk=plan.pk).status, PaymentPlan.objects.get(pk=plan.pk).settled_amount) for _, _, plan in cases}, before_plans)

    def test_settle_validates_payload_and_does_not_accept_mismatched_contract(self):
        plan = self.plan()
        url = f"/api/payment-plans/{plan.pk}/settle/"
        for payload in ({}, {"amount": "NaN"}, {"amount": "1", "exchange_rate": "0"}, {"amount": "1", "transaction_date": "invalid"}, {"amount": "1", "purchase_order": self.purchase.pk}):
            response = self.client.post(url, payload, format="json")
            self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(Transaction.objects.exists())

    def test_transaction_cannot_be_deleted_or_reactivated_by_patch(self):
        row = record_transaction({"plan": self.plan(), "amount": 10, "category": "receipt"})
        self.assertEqual(self.client.delete(f"/api/transactions/{row.pk}/").status_code, 400)
        void_transaction(row, "流水录入错误")
        self.assertEqual(self.client.patch(f"/api/transactions/{row.pk}/", {"status": "confirmed"}, format="json").status_code, 400)

    def test_direct_customer_receipt_without_payment_plan_records_contract_payment(self):
        row = record_transaction({
            "order": self.order,
            "customer": self.order.customer,
            "direction": "income",
            "kind": "customer_receipt",
            "category": "客户收款",
            "amount": Decimal("100"),
            "currency": self.order.currency,
            "transaction_date": self.day,
        })
        self.assertIsInstance(row, Transaction)
        self.assertEqual(row.status, "confirmed")
        self.assertEqual(row.order, self.order)
        self.assertEqual(sum(Transaction.objects.filter(order=self.order, status="confirmed").values_list("amount", flat=True)), Decimal("100"))

    def test_direct_supplier_payment_without_payment_plan_records_contract_payment(self):
        self.purchase_item.unit_price = Decimal("10")
        self.purchase_item.save(update_fields=["unit_price"])
        row = record_transaction({
            "purchase_order": self.purchase,
            "supplier": self.purchase.supplier,
            "direction": "expense",
            "kind": "supplier_payment",
            "category": "供应商付款",
            "amount": Decimal("100"),
            "currency": self.purchase.currency,
            "transaction_date": self.day,
        })
        self.assertIsInstance(row, Transaction)
        self.assertEqual(row.status, "confirmed")
        self.assertEqual(row.purchase_order, self.purchase)
        self.assertEqual(sum(Transaction.objects.filter(purchase_order=self.purchase, status="confirmed").values_list("amount", flat=True)), Decimal("100"))

    def test_report_excludes_void_and_out_of_period_transactions(self):
        self.plan()
        row = record_contract_payment(self.order, {"amount": 100, "category": "receipt", "transaction_date": self.day})
        void_transaction(row, "收款金额录入错误")
        report = self.client.get("/api/finance-dashboard/", {"date_from": "2026-09-01", "date_to": "2026-09-30"})
        self.assertEqual(report.status_code, 200)
        self.assertEqual(report.data["metrics"]["income_rmb"], 0)
        self.assertEqual(self.client.get("/api/finance-dashboard/", {"date_from": "broken"}).status_code, 400)

    def test_purchase_cannot_switch_supplier_after_receipt(self):
        self.receive("1")
        other = Supplier.objects.create(code="UQ", name="Other supplier")
        response = self.client.patch(f"/api/purchase-orders/{self.purchase.pk}/", {"supplier": other.pk}, format="json")
        self.assertEqual(response.status_code, 400, response.data)

    def test_draft_contract_does_not_create_financial_obligations(self):
        response = self.client.post("/api/purchase-orders/", {"exchange_rate": "1", "supplier": self.supplier.pk, "order_date": self.day.isoformat(), "status": "draft", "payment_terms_snapshot": [{"label": "预付款", "ratio": "0.30", "due_basis": "order_date", "offset_days": 0}, {"label": "尾款", "ratio": "0.70", "due_basis": "no_date", "offset_days": 0}], "items": [{"sku": self.sku.pk, "quantity": "2", "unit_price": "3"}]}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertFalse(PaymentPlan.objects.filter(purchase_order_id=response.data["id"]).exists())
        response = self.client.post(f"/api/purchase-orders/{response.data['id']}/place/", {}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(PaymentPlan.objects.filter(purchase_order_id=response.data["id"]).count(), 2)

    def test_shared_sku_purchase_is_not_counted_twice_for_procurement_gap(self):
        self.purchase_item.quantity = 6
        self.purchase_item.save()
        rebuild_default_cost_allocations(self.purchase)
        self.item.quantity = 5
        self.item.save()
        second = self.order.items.create(sku=self.sku, quantity=5, unit_price=10)
        gap = order_item_metrics(self.item)["to_procure_quantity"] + order_item_metrics(second)["to_procure_quantity"]
        self.assertEqual(gap, 4)

    def test_overreceipt_does_not_reduce_other_purchase_in_transit_for_order(self):
        record_receipt(self.purchase_item, {"quantity": Decimal(11), "receipt_date": self.day, "unit_cost": 5, "is_overage": True, "overage_reason": "gift"})
        second = PurchaseOrder.objects.create(purchase_no="UP-EXTRA", supplier=self.supplier, order=self.order, order_date=self.day, status="ordered")
        second.items.create(sku=self.sku, quantity=4, unit_price=5)
        self.assertEqual(order_item_metrics(self.item)['in_transit_quantity'], 4)

    def test_manual_replenishment_reserves_stock_for_existing_demand(self):
        response = self.client.post("/api/inventory-movements/", {"movement_date": self.day.isoformat(), "type": "adjust_in", "sku": self.sku.pk, "quantity": 4}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(sku_metrics(self.sku)["reserved_quantity"], 4)

    def test_status_change_does_not_reset_custom_installments(self):
        plans = ensure_default_payment_plans(self.order)
        plans[0].planned_amount = 20
        plans[0].save()
        plans[1].planned_amount = 80
        plans[1].save()
        response = self.client.post(f"/api/orders/{self.order.pk}/start-production/", {}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(list(self.order.payment_plans.order_by('pk').values_list('planned_amount', flat=True)), [20, 80])

    def test_quote_deposit_and_zero_or_full_deposit_are_respected(self):
        from crm.models import Quote
        quote = Quote.objects.create(quote_no="UP-Q", customer=self.customer, quote_date=self.day, deposit_ratio=Decimal("0.4"))
        self.order.quote = quote
        self.order.save()
        plans = ensure_default_payment_plans(self.order)
        self.assertEqual([row.planned_amount for row in plans], [40, 60])
        self.order.payment_plans.all().delete()
        plans = ensure_default_payment_plans(self.order, Decimal("1"))
        self.assertEqual([row.planned_amount for row in plans], [100])

    def test_excess_split_is_voided_with_original_cash_event(self):
        row = record_transaction({"plan": self.plan(), "amount": 120, "category": "receipt", "exchange_rate": 7})
        self.assertEqual(sum(Transaction.objects.values_list('rmb_amount', flat=True)), 840)
        void_transaction(row, "超额收款录入错误")
        self.assertFalse(Transaction.objects.filter(status='confirmed').exists())

    def test_import_cannot_overwrite_existing_cash(self):
        from crm.views import _import_row
        record_transaction({"transaction_no": "UP-IMPORT", "direction": "income", "category": "other", "amount": 20})
        with self.assertRaises(ValidationError):
            _import_row('transactions', {"transaction_no": "UP-IMPORT", "transaction_date": self.day.isoformat(), "direction": "income", "category": "other", "amount": "500"})
        self.assertEqual(Transaction.objects.get(transaction_no='UP-IMPORT').amount, 20)

    def test_plan_api_exposes_rmb_and_counterparty_and_protects_settled_amount(self):
        plan = self.plan()
        response = self.client.get(f'/api/payment-plans/{plan.pk}/')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['remaining_rmb'], 700)
        self.assertEqual(response.data['customer_id'], self.customer.pk)
        record_transaction({'plan': plan, 'amount': 10, 'category': 'receipt'})
        response = self.client.patch(f'/api/payment-plans/{plan.pk}/', {'planned_amount': 5}, format='json')
        self.assertEqual(response.status_code, 400, response.data)
        response = self.client.patch(f'/api/payment-plans/{plan.pk}/', {'notes': '新日期已确认'}, format='json')
        self.assertEqual(response.status_code, 200, response.data)

    def test_allocate_api_returns_updated_plan_and_trace(self):
        plan = self.plan()
        advance = record_transaction({'direction': 'income', 'kind': 'unallocated_advance', 'category': 'advance', 'amount': 10, 'currency': 'USD', 'customer': self.customer})
        response = self.client.post(f'/api/transactions/{advance.pk}/allocate/', {'plan': plan.pk, 'amount': '10'}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['settled_amount'], '10.0000')
        response = self.client.get(f'/api/transactions/{advance.pk}/')
        self.assertEqual(response.data['allocations'][0]['plan'], plan.pk)

    def test_allocate_audit_failure_rolls_back_business_write(self):
        plan = self.plan()
        advance = record_transaction({'direction': 'income', 'kind': 'unallocated_advance', 'category': 'advance', 'amount': 50, 'currency': 'USD', 'customer': self.customer})
        with patch('crm.views.record_operation', side_effect=RuntimeError('audit unavailable')):
            with self.assertRaises(RuntimeError):
                self.client.post(f'/api/transactions/{advance.pk}/allocate/', {'plan': plan.pk, 'amount': '50'}, format='json')
        plan.refresh_from_db()
        advance.refresh_from_db()
        self.assertEqual(plan.settled_amount, 0)
        self.assertEqual(advance.allocated_amount, 0)
        self.assertFalse(AdvanceAllocation.objects.filter(advance=advance).exists())
        response = self.client.post(f'/api/transactions/{advance.pk}/allocate/', {'plan': plan.pk, 'amount': '50'}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        plan.refresh_from_db()
        self.assertEqual(plan.settled_amount, 50)

    def test_receipt_audit_failure_rolls_back_business_write(self):
        plan = self.plan()
        payload = {'plan': plan.pk, 'transaction_date': self.day.isoformat(), 'direction': 'income', 'kind': 'customer_receipt', 'category': '客户收款', 'amount': '50', 'currency': 'USD', 'exchange_rate': '7'}
        with patch('crm.views.record_operation', side_effect=RuntimeError('audit unavailable')):
            with self.assertRaises(RuntimeError):
                self.client.post('/api/transactions/', payload, format='json')
        plan.refresh_from_db()
        self.assertEqual(plan.settled_amount, 0)
        self.assertFalse(Transaction.objects.exists())
        response = self.client.post('/api/transactions/', payload, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        plan.refresh_from_db()
        self.assertEqual(plan.settled_amount, 50)

    def _advance(self, number, *, purchase=False, amount=Decimal("50")):
        return Transaction.objects.create(
            transaction_no=number,
            transaction_date=self.day,
            direction="expense" if purchase else "income",
            kind="unallocated_payment" if purchase else "unallocated_advance",
            category="advance",
            amount=amount,
            rmb_amount=amount * Decimal("7"),
            currency="USD",
            exchange_rate=Decimal("7"),
            supplier=self.supplier if purchase else None,
            customer=None if purchase else self.customer,
        )

    def test_transaction_allocation_payload_exposes_order_id_and_keeps_unallocated_shape(self):
        unallocated = self._advance("UP-ALLOC-SO-EMPTY")
        response = self.client.get(f"/api/transactions/{unallocated.pk}/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["allocations"], [])

        plan = self.plan()
        advance = self._advance("UP-ALLOC-SO")
        allocate_advance(advance, plan, Decimal("20"))
        response = self.client.get(f"/api/transactions/{advance.pk}/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["allocations"], [{
            "id": AdvanceAllocation.objects.get(advance=advance).pk,
            "plan": plan.pk,
            "contract_no": self.order.order_no,
            "order": self.order.pk,
            "purchase_order": None,
            "amount": Decimal("20.0000"),
            "is_active": True,
        }])

    def test_transaction_allocation_payload_exposes_purchase_order_id(self):
        plan = PaymentPlan.objects.create(
            purchase_order=self.purchase, direction="payable", currency="USD", planned_amount=Decimal("50"),
        )
        advance = self._advance("UP-ALLOC-PO", purchase=True)
        allocate_advance(advance, plan, Decimal("15"))
        response = self.client.get(f"/api/transactions/{advance.pk}/")
        self.assertEqual(response.status_code, 200, response.data)
        item = response.data["allocations"][0]
        self.assertEqual(item["contract_no"], self.purchase.purchase_no)
        self.assertIsNone(item["order"])
        self.assertEqual(item["purchase_order"], self.purchase.pk)
        self.assertEqual(item["amount"], Decimal("15.0000"))

    def test_inactive_allocation_keeps_contract_navigation_ids(self):
        plan = self.plan()
        advance = self._advance("UP-ALLOC-INACTIVE")
        allocate_advance(advance, plan, Decimal("10"))
        allocation = AdvanceAllocation.objects.get(advance=advance)
        allocation.is_active = False
        allocation.save(update_fields=["is_active"])

        response = self.client.get(f"/api/transactions/{advance.pk}/")

        item = response.data["allocations"][0]
        self.assertFalse(item["is_active"])
        self.assertEqual(item["order"], self.order.pk)
        self.assertIsNone(item["purchase_order"])

    def test_multiple_transaction_allocations_keep_each_contract_id_and_number(self):
        other_order = Order.objects.create(
            order_no="CUSTOM-SALES-2", customer=self.customer, order_date=self.day,
            currency="USD", exchange_rate=7, status="confirmed",
        )
        other_order.items.create(sku=self.sku, quantity=10, unit_price=10)
        first_plan = self.plan()
        second_plan = PaymentPlan.objects.create(
            order=other_order, direction="receivable", currency="USD", planned_amount=Decimal("100"),
        )
        advance = self._advance("UP-ALLOC-MULTI", amount=Decimal("50"))
        allocate_advance(advance, first_plan, Decimal("10"))
        allocate_advance(advance, second_plan, Decimal("15"))

        response = self.client.get(f"/api/transactions/{advance.pk}/")

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual([
            (item["order"], item["purchase_order"], item["contract_no"])
            for item in response.data["allocations"]
        ], [
            (self.order.pk, None, self.order.order_no),
            (other_order.pk, None, other_order.order_no),
        ])

    def test_transaction_list_allocation_serialization_does_not_add_per_row_queries(self):
        first_plan = self.plan()
        first_advance = self._advance("UP-ALLOC-QUERY-1")
        allocate_advance(first_advance, first_plan, Decimal("5"))
        with CaptureQueriesContext(connection) as one_row_queries:
            first_response = self.client.get("/api/transactions/")
        self.assertEqual(first_response.status_code, 200, first_response.data)

        for index in range(2, 5):
            advance = self._advance(f"UP-ALLOC-QUERY-{index}")
            allocate_advance(advance, first_plan, Decimal("5"))
        with CaptureQueriesContext(connection) as several_row_queries:
            response = self.client.get("/api/transactions/")

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(len(one_row_queries), len(several_row_queries))
