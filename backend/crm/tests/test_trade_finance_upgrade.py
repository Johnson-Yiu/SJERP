from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APIClient

from crm.models import Customer, InventoryMovement, Order, PaymentPlan, Product, PurchaseOrder, SKU, Supplier, Transaction
from crm.services.finance import allocate_advance, ensure_default_payment_plans, record_contract_payment, record_transaction, void_transaction
from crm.services.fulfillment import allocate_order, confirm_shipment, order_item_metrics, record_receipt, sku_metrics


class TradeFinanceUpgradeTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.day = date(2026, 9, 7)
        self.customer = Customer.objects.create(code="UP-B", name="Upgrade Buyer")
        self.supplier = Supplier.objects.create(code="UP", name="Upgrade Supplier")
        self.sku = SKU.objects.create(sku="UP-SKU", product=Product.objects.create(code="UP-P", name="Light"))
        self.order = Order.objects.create(order_no="UP-SO", customer=self.customer, order_date=self.day, currency="USD", exchange_rate=7)
        self.item = self.order.items.create(sku=self.sku, quantity=10, unit_price=10)
        self.purchase = PurchaseOrder.objects.create(purchase_no="UP-PO", supplier=self.supplier, order=self.order, order_date=self.day, status="ordered", currency="USD", exchange_rate=7)
        self.purchase_item = self.purchase.items.create(sku=self.sku, quantity=10, unit_price=5)

    def stock(self, quantity):
        return InventoryMovement.objects.create(movement_no=f"UP-IN-{InventoryMovement.objects.count()}", movement_date=self.day, type="adjust_in", sku=self.sku, quantity=quantity)

    def receive(self, quantity):
        return record_receipt(self.purchase_item, {"quantity": Decimal(quantity), "receipt_date": self.day, "unit_cost": Decimal(5)})

    def ship(self, quantity):
        return confirm_shipment(self.order, {"shipment_date": self.day, "items": [{"order_item": self.item.pk, "quantity": Decimal(quantity)}]})

    def plan(self):
        return PaymentPlan.objects.create(order=self.order, direction="receivable", currency="USD", planned_amount=100)

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
        other = Order.objects.create(order_no="UP-SO-2", customer=self.customer, order_date=self.day)
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
        ensure_default_payment_plans(self.purchase)
        response = self.client.post(f"/api/purchase-orders/{self.purchase.pk}/pay/", {"transaction_date": self.day.isoformat(), "amount": "50", "currency": "USD", "exchange_rate": "7"}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertFalse(self.purchase.payment_plans.filter(status="open").exists())
        self.assertEqual(self.purchase.paid_amount, 50)
        self.assertFalse(Transaction.objects.filter(kind="unallocated_advance").exists())
        void_transaction(Transaction.objects.get(pk=response.data["id"]))
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
        void_transaction(advance)
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
        void_transaction(row)
        self.assertEqual(self.client.patch(f"/api/transactions/{row.pk}/", {"status": "confirmed"}, format="json").status_code, 400)

    def test_report_excludes_void_and_out_of_period_transactions(self):
        self.plan()
        row = record_contract_payment(self.order, {"amount": 100, "category": "receipt", "transaction_date": self.day})
        void_transaction(row)
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
        response = self.client.post("/api/purchase-orders/", {"purchase_no": "UP-DRAFT", "supplier": self.supplier.pk, "order_date": self.day.isoformat(), "status": "draft", "items": [{"sku": self.sku.pk, "quantity": "2", "unit_price": "3"}]}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertFalse(PaymentPlan.objects.filter(purchase_order_id=response.data["id"]).exists())
        response = self.client.patch(f"/api/purchase-orders/{response.data['id']}/", {"status": "ordered"}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(PaymentPlan.objects.filter(purchase_order_id=response.data["id"]).count(), 2)

    def test_shared_sku_purchase_is_not_counted_twice_for_procurement_gap(self):
        self.purchase_item.quantity = 6
        self.purchase_item.save()
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
        response = self.client.patch(f"/api/orders/{self.order.pk}/", {"status": "production"}, format="json")
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
        void_transaction(row)
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
