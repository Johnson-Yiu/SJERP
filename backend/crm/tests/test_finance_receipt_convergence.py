from datetime import date
from decimal import Decimal
import hashlib
import tempfile
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless

from django.core.files.base import ContentFile
from django.test import TestCase, TransactionTestCase, override_settings
from django.db import close_old_connections, connection, connections
from rest_framework.test import APIClient

from crm.models import AdvanceAllocation, Customer, FinancePlanWriteoff, FinanceReceiptAdjustment, FinanceVoucher, Order, PaymentPlan, Product, SKU, Transaction


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
        allocated = self.client.post(f"/api/transactions/{response.data['id']}/allocate/", {"plan": self.plan.pk, "amount": "150"}, format="json")
        self.assertEqual(allocated.status_code, 200, allocated.data)
        self.plan.refresh_from_db()
        self.assertEqual(self.plan.remaining_amount, 850)
        receipt = Transaction.objects.get(pk=response.data["id"])
        self.assertEqual(receipt.amount, 200)
        self.assertEqual(receipt.allocated_amount, 150)


@override_settings(APP_STAGE="development", DEBUG=True, DEVELOPMENT_SUPERADMIN=True, RBAC_ENFORCEMENT=False, AUDIT_LOG_ENABLED=True)
@skipUnless(connection.vendor == "postgresql", "并发测试需要 PostgreSQL")
class ReceiptReplayConcurrencyTests(TransactionTestCase):
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
