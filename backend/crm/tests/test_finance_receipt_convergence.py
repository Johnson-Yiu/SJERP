from datetime import date
from decimal import Decimal
import hashlib
import tempfile
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.test import TestCase, TransactionTestCase, override_settings
from django.db import close_old_connections, connection, connections
from rest_framework.test import APIClient

from crm.models import AdvanceAllocation, Customer, FinancePlanWriteoff, FinanceReceiptAdjustment, FinanceVoucher, Order, PaymentPlan, Product, PurchaseOrder, SKU, Supplier, Transaction


@override_settings(APP_STAGE="development", DEBUG=True, DEVELOPMENT_SUPERADMIN=True, RBAC_ENFORCEMENT=False, AUDIT_LOG_ENABLED=True)
class ReceiptConvergenceTests(TestCase):
    def setUp(self):
        media = tempfile.TemporaryDirectory(prefix="receipt-convergence-")
        self.addCleanup(media.cleanup)
        override = override_settings(MEDIA_ROOT=media.name)
        override.enable()
        self.addCleanup(override.disable)
        self.client = APIClient()
        self.customer = Customer.objects.create(code="CONVERGE-C", name="合成客户")
        product = Product.objects.create(code="CONVERGE-P", name="合成产品")
        sku = SKU.objects.create(product=product, sku="CONVERGE-SKU")
        self.order = Order.objects.create(order_no="CONVERGE-O", customer=self.customer, order_date=date(2026, 11, 1), currency="USD", exchange_rate=Decimal("7.2"), status="confirmed")
        self.order.items.create(sku=sku, quantity=1, unit_price=1000)
        self.plan = PaymentPlan.objects.create(order=self.order, direction="receivable", currency="USD", planned_amount=1000)
        content = b"%PDF-1.4\nSynthetic receipt evidence\n%%EOF"
        self.proof = FinanceVoucher(original_name="synthetic.pdf", sha256=hashlib.sha256(content).hexdigest(), size=len(content), scope="transaction", bank_sources=[], actor={})
        self.proof.file.save("synthetic.pdf", ContentFile(content), save=False)
        self.proof.save()

    def test_void_audit_rollback_and_replay(self):
        from crm.models import OperationLog
        from crm.services.finance import record_transaction
        self.plan.planned_amount = 100
        self.plan.save()
        row = record_transaction({"plan": self.plan, "amount": 50, "currency": "USD", "exchange_rate": 7})
        url = f"/api/transactions/{row.pk}/void/"
        body = {"reason": "Synthetic duplicate receipt"}
        self.client.force_authenticate(get_user_model().objects.create_superuser("void-reviewer"))
        with patch("crm.views.record_operation", side_effect=RuntimeError("synthetic audit failure")):
            self.client.raise_request_exception = False
            self.assertEqual(self.client.post(url, body, format="json", HTTP_IDEMPOTENCY_KEY="VOID-50").status_code, 500)
        row.refresh_from_db()
        self.plan.refresh_from_db()
        self.assertEqual((row.status, self.plan.remaining_amount), ("confirmed", Decimal("50")))
        first = self.client.post(url, body, format="json", HTTP_IDEMPOTENCY_KEY="VOID-50")
        replay = self.client.post(url, body, format="json", HTTP_IDEMPOTENCY_KEY="VOID-50")
        self.assertEqual(first.status_code, 200, first.data)
        self.assertEqual(replay.data, first.data)
        self.assertEqual(replay.headers.get("Idempotent-Replay"), "true")
        conflict = self.client.post(url, {"reason": "Different reason"}, format="json", HTTP_IDEMPOTENCY_KEY="VOID-50")
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(OperationLog.objects.filter(action_label="作废财务流水", object_id=str(row.pk)).count(), 1)

    def test_refund_uses_actual_date_and_replays_across_days(self):
        from crm.services.finance import record_transaction
        row = record_transaction({"plan": self.plan, "amount": 50, "currency": "USD", "exchange_rate": 7})
        url = f"/api/transactions/{row.pk}/refund-cash/"
        payload = {"order": self.order.pk, "amount": "5", "reason": "Synthetic refund receipt evidence", "voucher": self.proof.pk}
        bad = self.client.post(url, {**payload, "actual_date": "2026-02-30"}, format="json", HTTP_IDEMPOTENCY_KEY="REFUND-DATE")
        self.assertEqual(bad.status_code, 400)
        self.assertIn("actual_date", bad.data)
        payload["actual_date"] = "2026-10-30"
        first = self.client.post(url, payload, format="json", HTTP_IDEMPOTENCY_KEY="REFUND-DATE")
        self.assertEqual(first.status_code, 201, first.data)
        with patch("crm.views.timezone.localdate", return_value=date(2026, 11, 10)):
            retry = self.client.post(url, payload, format="json", HTTP_IDEMPOTENCY_KEY="REFUND-DATE")
        self.assertEqual(retry.data, first.data)
        self.assertEqual(retry.headers.get("Idempotent-Replay"), "true")
        refund = Transaction.objects.get(pk=first.data["refunds"][0]["id"])
        self.assertEqual(refund.transaction_date, date(2026, 10, 30))
        for start, end, expected in (("2026-10-01", "2026-10-31", True), ("2026-11-01", "2026-11-30", False)):
            result = self.client.get("/api/transactions/", {"date_from": start, "date_to": end})
            rows = result.data["results"] if isinstance(result.data, dict) else result.data
            self.assertEqual(any(item["id"] == refund.pk for item in rows), expected)
            period = {"date_from": start, "date_to": end}
            summary = self.client.get("/api/finance-dashboard/", period)
            self.assertEqual(Decimal(summary.data["metrics"]["expense_rmb"]), 35 if expected else 0)
            exported = self.client.get("/api/finance-dashboard/", {**period, "export": "csv"})
            self.assertEqual(exported.status_code, 200)
            self.assertEqual("客户退款" in exported.content.decode("utf-8-sig"), expected)

        conflict = self.client.post(url, {**payload, "actual_date": "2026-10-31"}, format="json", HTTP_IDEMPOTENCY_KEY="REFUND-DATE")
        self.assertEqual(conflict.status_code, 409)

    def payload(self, number="CONVERGE-1", responsibility="company"):
        return {"transaction_no": number, "transaction_date": "2026-11-06", "direction": "income", "kind": "customer_receipt",
            "category": "客户收款", "amount": "985", "currency": "USD", "customer": self.customer.pk, "order": self.order.pk,
            "remittance_amount": "990", "receipt_adjustments": [
                {"nature": "discount", "amount": "10", "handling": "applied", "reason": "已批准优惠减免", "evidence": self.proof.pk, "plan": self.plan.pk},
                {"nature": "bank_fee", "amount": "5", "handling": responsibility, "reason": "合同及回单确认手续费承担", "evidence": self.proof.pk},
            ]}

    def test_structured_receipt_preserves_cash_and_idempotent_replay(self):
        payload = self.payload()
        response = self.client.post("/api/transactions/", payload, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        receipt = Transaction.objects.get(pk=response.data["id"])
        self.plan.refresh_from_db()
        allocation = AdvanceAllocation.objects.get(advance=receipt, plan=self.plan)
        self.assertEqual((receipt.amount, allocation.cash_amount, allocation.fee_credit_amount), (Decimal("985"), Decimal("985"), Decimal("5")))
        self.assertEqual(self.plan.remaining_amount, 0)
        self.assertIsNone(receipt.exchange_rate)
        self.assertTrue(receipt.reference_rate_missing)
        self.assertEqual(FinancePlanWriteoff.objects.get(source_transaction=receipt).amount, 10)
        self.assertEqual(FinanceReceiptAdjustment.objects.filter(transaction=receipt).count(), 2)
        retry = self.client.post("/api/transactions/", payload, format="json")
        self.assertEqual(retry.status_code, 200, retry.data)
        self.assertEqual(Transaction.objects.count(), 1)
        payload["amount"] = "984"
        conflict = self.client.post("/api/transactions/", payload, format="json")
        self.assertEqual(conflict.status_code, 409, conflict.data)

    def test_structured_receipt_replay_requires_the_original_operator(self):
        first = get_user_model().objects.create_superuser("receipt-first")
        other = get_user_model().objects.create_superuser("receipt-other")
        self.client.force_authenticate(first)
        body = self.payload()
        created = self.client.post("/api/transactions/", body, format="json")
        self.assertEqual(created.status_code, 201, created.data)
        self.client.force_authenticate(other)
        self.assertEqual(self.client.post("/api/transactions/", body, format="json").status_code, 409)
        self.client.force_authenticate(first)
        self.assertEqual(self.client.post("/api/transactions/", body, format="json").status_code, 200)

    def test_customer_fee_leaves_difference(self):
        response = self.client.post("/api/transactions/", self.payload(responsibility="customer"), format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.plan.refresh_from_db()
        self.assertEqual(self.plan.remaining_amount, 5)

    def test_930_cash_20_company_fee_and_50_discount(self):
        payload = self.payload(number="CONVERGE-930")
        payload.update(amount="930", remittance_amount="950", exchange_rate="7.2")
        payload["receipt_adjustments"][0]["amount"] = "50"
        payload["receipt_adjustments"][1]["amount"] = "20"
        response = self.client.post("/api/transactions/", payload, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        receipt = Transaction.objects.get(pk=response.data["id"])
        allocation = AdvanceAllocation.objects.get(advance=receipt)
        self.plan.refresh_from_db()
        self.assertEqual((receipt.amount, allocation.cash_amount, allocation.fee_credit_amount), (930, 930, 20))
        self.assertEqual(self.plan.remaining_amount, 0)
        from crm.services.profit import order_profit_summary
        summary = order_profit_summary(self.order)
        self.assertEqual(summary["receipt_bank_fee_rmb"], Decimal("144"))
        self.assertEqual(summary["receivable_reduction_rmb"], Decimal("360"))
        period = {"date_from": "2026-11-01", "date_to": "2026-11-30"}
        dashboard = self.client.get("/api/finance-dashboard/", period)
        details = self.client.get("/api/finance-dashboard/details/", {**period, "metric": "receivable_reduction_rmb"})
        csv = self.client.get("/api/finance-dashboard/", {**period, "export": "csv"})
        self.assertEqual((dashboard.status_code, details.status_code, csv.status_code), (200, 200, 200))
        self.assertEqual(Decimal(dashboard.data["metrics"]["receivable_reduction_rmb"]), Decimal("360"))
        self.assertEqual(Decimal(details.data["total_amount"]), Decimal("360"))
        import csv as csv_format
        export_rows = dict((row[0], row[1]) for row in csv_format.reader(csv.content.decode("utf-8-sig").splitlines()) if len(row) == 2)
        self.assertEqual(Decimal(export_rows["核准非现金抵减"]), Decimal("360"))

    def test_unallocated_balance_counts_cash_not_fee_credit(self):
        payload = self.payload(number="CONVERGE-CASH-BALANCE")
        payload["receipt_adjustments"] = [payload["receipt_adjustments"][1]]
        payload["plan_allocations"] = [{"plan": self.plan.pk, "amount": "500"}]
        response = self.client.post("/api/transactions/", payload, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["unallocated_amount"], Decimal("485"))
        self.assertEqual(Decimal(response.data["allocation_capacity"]), Decimal("990"))

    def test_voucher_cannot_be_reused_for_another_receipt(self):
        first = self.client.post("/api/transactions/", self.payload(), format="json")
        self.assertEqual(first.status_code, 201, first.data)
        second = self.payload(number="CONVERGE-OTHER")
        second["receipt_adjustments"] = [second["receipt_adjustments"][1]]
        response = self.client.post("/api/transactions/", second, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(Transaction.objects.count(), 1)

    def test_one_receipt_can_be_distributed_across_orders(self):
        second = Order.objects.create(order_no="CONVERGE-O2", customer=self.customer, order_date=date(2026, 11, 2), currency="USD", exchange_rate=Decimal("7.2"), status="confirmed")
        second.items.create(sku=self.order.items.first().sku, quantity=1, unit_price=400)
        second_plan = PaymentPlan.objects.create(order=second, direction="receivable", currency="USD", planned_amount=400)
        payload = {"transaction_no": "CONVERGE-MULTI", "transaction_date": "2026-11-06", "direction": "income", "kind": "customer_receipt", "category": "客户收款", "amount": "500", "currency": "USD", "customer": self.customer.pk, "receipt_adjustments": [], "plan_allocations": [{"plan": self.plan.pk, "amount": "300"}, {"plan": second_plan.pk, "amount": "200"}]}
        response = self.client.post("/api/transactions/", payload, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.plan.refresh_from_db(); second_plan.refresh_from_db()
        self.assertEqual((self.plan.remaining_amount, second_plan.remaining_amount), (700, 200))
        self.assertEqual(len(response.data["allocations"]), 2)

    def test_audit_failure_rolls_back_entire_receipt(self):
        with patch("crm.views.record_operation", side_effect=RuntimeError("synthetic audit failure")):
            with self.assertRaises(RuntimeError):
                self.client.post("/api/transactions/", self.payload(), format="json")
        self.plan.refresh_from_db()
        self.assertEqual(self.plan.settled_amount, 0)
        self.assertFalse(Transaction.objects.exists())
        self.assertFalse(FinancePlanWriteoff.objects.exists())
        self.assertFalse(FinanceReceiptAdjustment.objects.exists())

    def test_no_order_receipt_can_be_allocated_later(self):
        payload = {"transaction_no": "CONVERGE-LATER", "transaction_date": "2026-11-06", "direction": "income", "kind": "customer_receipt", "category": "客户收款", "amount": "200", "currency": "USD", "customer": self.customer.pk, "receipt_adjustments": []}
        response = self.client.post("/api/transactions/", payload, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["unallocated_amount"], Decimal("200"))
        allocated = self.client.post(f"/api/transactions/{response.data['id']}/allocate/", {"plan": self.plan.pk, "amount": "150"}, format="json", HTTP_IDEMPOTENCY_KEY="allocate-later")
        self.assertEqual(allocated.status_code, 200, allocated.data)
        self.plan.refresh_from_db()
        self.assertEqual(self.plan.remaining_amount, 850)
        receipt = Transaction.objects.get(pk=response.data["id"])
        self.assertEqual(receipt.amount, 200)
        self.assertEqual(receipt.allocated_amount, 150)
        retry = self.client.post(f"/api/transactions/{receipt.pk}/allocate/", {"plan": self.plan.pk, "amount": "150"}, format="json", HTTP_IDEMPOTENCY_KEY="allocate-later")
        self.assertEqual(retry.status_code, 200, retry.data)
        self.assertEqual(retry.headers.get("Idempotent-Replay"), "true")
        conflict = self.client.post(f"/api/transactions/{receipt.pk}/allocate/", {"plan": self.plan.pk, "amount": "100"}, format="json", HTTP_IDEMPOTENCY_KEY="allocate-later")
        self.assertEqual(conflict.status_code, 409, conflict.data)
        missing = self.client.post(f"/api/transactions/{receipt.pk}/allocate/", {"plan": self.plan.pk, "amount": "50"}, format="json")
        self.assertEqual(missing.status_code, 400, missing.data)
        independent = self.client.post(f"/api/transactions/{receipt.pk}/allocate/", {"plan": self.plan.pk, "amount": "50"}, format="json", HTTP_IDEMPOTENCY_KEY="allocate-later-new-action")
        self.assertEqual(independent.status_code, 200, independent.data)
        self.plan.refresh_from_db()
        self.assertEqual(self.plan.settled_amount, 200)

    def test_selected_plan_audit_failure_allows_same_key_retry(self):
        payload = {"amount": "50", "transaction_date": "2026-11-06", "currency": "USD", "exchange_rate": "7.2"}
        url = f"/api/payment-plans/{self.plan.pk}/settle/"
        with patch("crm.views.record_operation", side_effect=RuntimeError("synthetic plan audit failure")):
            with self.assertRaises(RuntimeError):
                self.client.post(url, payload, format="json", HTTP_IDEMPOTENCY_KEY="PLAN-AUDIT")
        self.plan.refresh_from_db()
        self.assertEqual(self.plan.settled_amount, 0)
        self.assertFalse(Transaction.objects.exists())
        response = self.client.post(url, payload, format="json", HTTP_IDEMPOTENCY_KEY="PLAN-AUDIT")
        self.assertEqual(response.status_code, 201, response.data)
        self.plan.refresh_from_db()
        self.assertEqual(self.plan.settled_amount, 50)

    def test_selected_plan_replay_accepts_same_explicit_business_number(self):
        payload = {"transaction_no": "PLAN-BUSINESS-NO", "amount": "50", "transaction_date": "2026-11-06", "currency": "USD", "exchange_rate": "7.2"}
        url = f"/api/payment-plans/{self.plan.pk}/settle/"
        first = self.client.post(url, payload, format="json", HTTP_IDEMPOTENCY_KEY="PLAN-BUSINESS-KEY")
        self.assertEqual(first.status_code, 201, first.data)
        replay = self.client.post(url, payload, format="json", HTTP_IDEMPOTENCY_KEY="PLAN-BUSINESS-KEY")
        self.assertEqual(replay.status_code, 201, replay.data)
        self.assertEqual(replay.data["id"], first.data["id"])
        self.assertEqual(replay.headers.get("Idempotent-Replay"), "true")
        duplicate = self.client.post(url, payload, format="json", HTTP_IDEMPOTENCY_KEY="PLAN-OTHER-KEY")
        self.assertEqual(duplicate.status_code, 409, duplicate.data)

    def test_legacy_direct_receipt_replays_by_business_identity(self):
        payload = {"transaction_no": "LEGACY-RECEIPT-IDENTITY", "transaction_date": "2026-11-06", "direction": "income", "kind": "customer_receipt", "category": "客户收款", "amount": "50", "currency": "USD", "exchange_rate": "7.2", "plan": self.plan.pk}
        first = self.client.post("/api/transactions/", payload, format="json")
        self.assertEqual(first.status_code, 201, first.data)
        replay = self.client.post("/api/transactions/", payload, format="json")
        self.assertEqual(replay.status_code, 201, replay.data)
        self.assertEqual(replay.data["id"], first.data["id"])
        self.assertEqual(replay.headers.get("Idempotent-Replay"), "true")
        conflict = self.client.post("/api/transactions/", {**payload, "amount": "40"}, format="json")
        self.assertEqual(conflict.status_code, 409, conflict.data)
        self.plan.refresh_from_db()
        self.assertEqual(self.plan.settled_amount, 50)

    def test_plan_replay_uses_submitted_intent_after_contract_rate_changes(self):
        payload = {"amount": "50", "transaction_date": "2026-11-06"}
        url = f"/api/payment-plans/{self.plan.pk}/settle/"
        first = self.client.post(url, payload, format="json", HTTP_IDEMPOTENCY_KEY="PLAN-RATE-CHANGE")
        self.assertEqual(first.status_code, 201, first.data)
        self.order.exchange_rate = Decimal("7.9")
        self.order.save(update_fields=["exchange_rate"])
        replay = self.client.post(url, payload, format="json", HTTP_IDEMPOTENCY_KEY="PLAN-RATE-CHANGE")
        self.assertEqual(replay.status_code, 201, replay.data)
        self.assertEqual(replay.data["id"], first.data["id"])
        self.assertEqual(replay.headers.get("Idempotent-Replay"), "true")


@override_settings(APP_STAGE="development", DEBUG=True, DEVELOPMENT_SUPERADMIN=True, RBAC_ENFORCEMENT=False, AUDIT_LOG_ENABLED=True)
@skipUnless(connection.vendor == "postgresql", "并发测试需要 PostgreSQL")
class ReceiptReplayConcurrencyTests(TransactionTestCase):
    def test_concurrent_void_has_one_reversal_and_one_audit(self):
        from crm.models import OperationLog
        from crm.services.finance import record_transaction

        customer = Customer.objects.create(code="VOID-RACE", name="Synthetic void buyer")
        order = Order.objects.create(order_no="VOID-RACE", customer=customer, order_date=date(2026, 11, 1), currency="USD", status="confirmed")
        plan = PaymentPlan.objects.create(order=order, direction="receivable", currency="USD", planned_amount=100)
        receipt = record_transaction({"plan": plan, "amount": 50, "currency": "USD", "exchange_rate": 7})
        user = get_user_model().objects.create_superuser("void-race")
        barrier = Barrier(2)

        def submit():
            close_old_connections()
            try:
                client = APIClient()
                client.force_authenticate(user)
                barrier.wait(timeout=15)
                response = client.post(f"/api/transactions/{receipt.pk}/void/", {"reason": "Synthetic concurrent void"}, format="json", HTTP_IDEMPOTENCY_KEY="VOID-RACE")
                return response.status_code, response.headers.get("Idempotent-Replay")
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: submit(), range(2)))
        self.assertCountEqual(results, [(200, None), (200, "true")])
        plan.refresh_from_db()
        self.assertEqual(plan.remaining_amount, 100)
        self.assertEqual(OperationLog.objects.filter(action_label="作废财务流水", object_id=str(receipt.pk)).count(), 1)

    def test_concurrent_legacy_direct_receipt_replays_once(self):
        customer = Customer.objects.create(code="DIRECT-RACE-C", name="合成客户")
        order = Order.objects.create(order_no="DIRECT-RACE-O", customer=customer, order_date=date(2026, 11, 1), currency="USD", exchange_rate=7, status="confirmed")
        plan = PaymentPlan.objects.create(order=order, direction="receivable", currency="USD", planned_amount=100)
        payload = {"transaction_no": "DIRECT-RACE", "transaction_date": "2026-11-06", "direction": "income", "kind": "customer_receipt", "category": "客户收款", "amount": "50", "currency": "USD", "exchange_rate": "7", "plan": plan.pk}
        barrier = Barrier(2)

        def submit():
            close_old_connections()
            try:
                barrier.wait(timeout=15)
                response = APIClient().post("/api/transactions/", payload, format="json")
                return response.status_code, response.data.get("id"), response.headers.get("Idempotent-Replay")
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: submit(), range(2)))
        self.assertEqual([item[0] for item in results], [201, 201])
        self.assertEqual(len({item[1] for item in results}), 1)
        self.assertEqual(sum(item[2] == "true" for item in results), 1)
        plan.refresh_from_db()
        self.assertEqual(plan.settled_amount, 50)

    def test_concurrent_identical_receipts_create_one_fact(self):
        customer = Customer.objects.create(code="CONVERGE-RACE", name="合成并发客户")
        payload = {"transaction_no": "CONVERGE-RACE", "transaction_date": "2026-11-06", "direction": "income", "kind": "customer_receipt", "category": "客户收款", "amount": "50", "currency": "USD", "customer": customer.pk, "receipt_adjustments": []}
        barrier = Barrier(2)

        def submit():
            close_old_connections()
            try:
                client = APIClient()
                barrier.wait(timeout=15)
                response = client.post("/api/transactions/", payload, format="json")
                return response.status_code, response.data.get("id")
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: submit(), range(2)))
        self.assertEqual(sorted(status for status, _ in results), [200, 201])
        self.assertEqual(len({identifier for _, identifier in results}), 1)
        self.assertEqual(Transaction.objects.filter(transaction_no="CONVERGE-RACE").count(), 1)

    def test_concurrent_allocation_replays_once(self):
        customer = Customer.objects.create(code="ALLOC-RACE-C", name="合成核销客户")
        order = Order.objects.create(order_no="ALLOC-RACE-O", customer=customer, order_date=date(2026, 11, 1), currency="USD", exchange_rate=7, status="confirmed")
        plan = PaymentPlan.objects.create(order=order, direction="receivable", currency="USD", planned_amount=100)
        source = Transaction.objects.create(transaction_no="ALLOC-RACE", transaction_date=date(2026, 11, 1), direction="income", kind="unallocated_advance", category="预收", amount=50, currency="USD", exchange_rate=7, customer=customer, status="confirmed")
        barrier = Barrier(2)

        def submit():
            close_old_connections()
            try:
                client = APIClient()
                barrier.wait(timeout=15)
                response = client.post(f"/api/transactions/{source.pk}/allocate/", {"plan": plan.pk, "amount": "50"}, format="json", HTTP_IDEMPOTENCY_KEY="ALLOC-RACE-KEY")
                return response.status_code, response.headers.get("Idempotent-Replay")
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: submit(), range(2)))
        self.assertEqual(sorted(status for status, _ in results), [200, 200])
        self.assertEqual(sum(replay == "true" for _, replay in results), 1)
        plan.refresh_from_db(); source.refresh_from_db()
        self.assertEqual(plan.settled_amount, 50)
        self.assertEqual(source.allocated_amount, 50)
        self.assertEqual(AdvanceAllocation.objects.filter(advance=source).count(), 1)

    def test_concurrent_supplier_payment_replays_once(self):
        supplier = Supplier.objects.create(code="PR", name="合成供应商")
        product = Product.objects.create(code="PAY-RACE-P", name="合成产品")
        sku = SKU.objects.create(product=product, sku="PAY-RACE-SKU")
        purchase = PurchaseOrder.objects.create(purchase_no="PAY-RACE-PO", supplier=supplier, order_date=date(2026, 11, 1), currency="CNY", exchange_rate=1, status="ordered")
        purchase.items.create(sku=sku, quantity=1, unit_price=100)
        plan = PaymentPlan.objects.create(purchase_order=purchase, direction="payable", currency="CNY", planned_amount=100)
        barrier = Barrier(2)
        payload = {"transaction_date": "2026-11-06", "amount": "50", "currency": "CNY", "exchange_rate": "1"}

        def submit():
            close_old_connections()
            try:
                client = APIClient()
                barrier.wait(timeout=15)
                response = client.post(f"/api/purchase-orders/{purchase.pk}/pay/", payload, format="json", HTTP_IDEMPOTENCY_KEY="PAY-RACE-KEY")
                return response.status_code, response.data.get("id"), response.headers.get("Idempotent-Replay")
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: submit(), range(2)))
        self.assertEqual([status for status, _, _ in results], [201, 201])
        self.assertEqual(len({identifier for _, identifier, _ in results}), 1)
        self.assertEqual(sum(replay == "true" for _, _, replay in results), 1)
        plan.refresh_from_db()
        self.assertEqual(plan.settled_amount, 50)
        self.assertEqual(Transaction.objects.filter(purchase_order=purchase, kind="supplier_payment").count(), 1)
        client = APIClient()
        conflict = client.post(f"/api/purchase-orders/{purchase.pk}/pay/", {**payload, "amount": "49"}, format="json", HTTP_IDEMPOTENCY_KEY="PAY-RACE-KEY")
        self.assertEqual(conflict.status_code, 409, conflict.data)
        missing = client.post(f"/api/purchase-orders/{purchase.pk}/pay/", payload, format="json")
        self.assertEqual(missing.status_code, 400, missing.data)
        plan.refresh_from_db()
        self.assertEqual(plan.settled_amount, 50)

    def test_concurrent_selected_plan_receipt_replays_once(self):
        customer = Customer.objects.create(code="PLAN-RACE-C", name="合成计划客户")
        order = Order.objects.create(order_no="PLAN-RACE-O", customer=customer, order_date=date(2026, 11, 1), currency="USD", exchange_rate=7, status="confirmed")
        first = PaymentPlan.objects.create(order=order, direction="receivable", currency="USD", planned_amount=50, due_date=date(2026, 11, 1))
        selected = PaymentPlan.objects.create(order=order, direction="receivable", currency="USD", planned_amount=50, due_date=date(2026, 12, 1))
        barrier = Barrier(2)
        payload = {"amount": "20", "transaction_date": "2026-11-06", "currency": "USD", "exchange_rate": "7"}

        def submit():
            close_old_connections()
            try:
                client = APIClient()
                barrier.wait(timeout=15)
                response = client.post(f"/api/payment-plans/{selected.pk}/settle/", payload, format="json", HTTP_IDEMPOTENCY_KEY="PLAN-RACE-KEY")
                return response.status_code, response.data.get("id"), response.headers.get("Idempotent-Replay")
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: submit(), range(2)))
        self.assertEqual([status for status, _, _ in results], [201, 201])
        self.assertEqual(len({identifier for _, identifier, _ in results}), 1)
        self.assertEqual(sum(replay == "true" for _, _, replay in results), 1)
        first.refresh_from_db(); selected.refresh_from_db()
        self.assertEqual((first.settled_amount, selected.settled_amount), (0, 20))
        self.assertEqual(Transaction.objects.filter(plan=selected).count(), 1)
        client = APIClient()
        conflict = client.post(f"/api/payment-plans/{selected.pk}/settle/", {**payload, "amount": "19"}, format="json", HTTP_IDEMPOTENCY_KEY="PLAN-RACE-KEY")
        self.assertEqual(conflict.status_code, 409, conflict.data)
        missing = client.post(f"/api/payment-plans/{selected.pk}/settle/", payload, format="json")
        self.assertEqual(missing.status_code, 400, missing.data)
        selected.refresh_from_db()
        self.assertEqual(selected.settled_amount, 20)
