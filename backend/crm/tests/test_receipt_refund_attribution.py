from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection, connections
from django.test import TestCase, TransactionTestCase, override_settings
from rest_framework.test import APIClient
from crm.models import FinanceReceiptRefund, PaymentPlan, Transaction
from crm.services import cash_events as cash
from crm.tests.test_cash_events import CashFixture, payload


@override_settings(RMB_CASH_ACCOUNT_IDS=("SYNTH_FX", "SYNTH_CNY"))
class ReceiptRefundAttributionTests(CashFixture, TestCase):
    def setUp(self):
        self.setup_cash()
        from crm.services.finance_closeout import upload
        self.proof = upload(SimpleUploadedFile("refund.pdf", b"%PDF-1.4\nsynthetic refund proof\n%%EOF"), self.user, scope="transaction")

    def refund(self, key, amount, order=None):
        return self.client.post(f"/api/transactions/{self.receipt.pk}/refund-cash/", {
            "amount": amount, "order": order or self.order.pk, "reason": "合成退款凭证已经核实", "voucher": self.proof.pk,
        }, format="json", HTTP_IDEMPOTENCY_KEY=key)

    def test_direct_plan_receipt_has_no_unallocated_refund_capacity(self):
        self.assertEqual(self.receipt.unallocated_cash_amount, Decimal("0"))
        before = Transaction.objects.count()
        response = self.client.post(f"/api/transactions/{self.receipt.pk}/refund-cash/", {
            "amount": "20", "order": "", "reason": "直接计划收款禁止未分配退款", "voucher": self.proof.pk,
        }, format="json", HTTP_IDEMPOTENCY_KEY="direct-plan-unallocated")
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(Transaction.objects.count(), before)
        self.assertEqual(FinanceReceiptRefund.objects.count(), 0)
        self.plan.refresh_from_db()
        self.assertEqual(self.plan.settled_amount, Decimal("100"))

    def test_cancelled_receipt_void_does_not_reopen_receivable(self):
        from crm.services.finance import void_transaction
        response = self.client.post(f"/api/orders/{self.order.pk}/cancel/", {
            "reason": "测试取消后作废原收款", "settle_refund": True,
        }, format="json", HTTP_IDEMPOTENCY_KEY="cancel-before-void")
        self.assertEqual(response.status_code, 200, response.data)
        void_transaction(self.receipt, "测试原收款作废")
        self.plan.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(self.plan.settled_amount, 0)
        self.assertEqual(self.plan.planned_amount, 0)
        self.assertEqual(self.plan.status, "cancelled")
        self.assertEqual(self.order.outstanding_amount, 0)
        self.assertEqual(self.order.paid_amount, 0)

    def test_cancelled_non_cash_correction_preserves_zero_receivable(self):
        from crm.services.finance import record_transaction, void_transaction, writeoff_receivable, correct_receivable_writeoff
        void_transaction(self.receipt, "测试原收款作废")
        source = record_transaction(dict(plan=self.plan, amount="99", currency="USD"))
        reduction, _ = writeoff_receivable(source, self.plan, Decimal("1"), "测试非现金抵减", "cancel-reduction", self.user)
        response = self.client.post(f"/api/orders/{self.order.pk}/cancel/", {
            "reason": "测试取消后更正非现金抵减", "settle_refund": True,
        }, format="json", HTTP_IDEMPOTENCY_KEY="cancel-before-correction")
        self.assertEqual(response.status_code, 200, response.data)
        correction, created = correct_receivable_writeoff(source, reduction, Decimal("1"), "更正错误非现金抵减", "cancel-correction", self.user)
        self.assertTrue(created)
        self.assertEqual(correction.writeoff_id, reduction.pk)
        self.plan.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(self.plan.planned_amount, 99)
        self.assertEqual(self.plan.settled_amount, 99)
        self.assertEqual(self.plan.status, "settled")
        self.assertEqual(self.order.outstanding_amount, 0)
        self.assertEqual(self.order.paid_amount, 99)
        self.assertEqual(reduction.corrections.count(), 1)

    def test_cancelled_company_fee_refunds_only_cash_and_does_not_reopen_receivable(self):
        from crm.services.finance import record_transaction, void_transaction
        from crm.services.finance_closeout import upload
        void_transaction(self.receipt, "替换公司手续费夹具")
        source = record_transaction(dict(kind="customer_receipt", direction="income", plan=self.plan,
            amount="98", remittance_amount="100", bank_fee_amount="2", fee_responsibility="company",
            fee_reason="合成我方承担手续费", fee_evidence=self.proof, currency="USD"))
        response = self.client.post(f"/api/orders/{self.order.pk}/cancel/", {
            "reason": "取消保留我方手续费的现金事实", "settle_refund": True,
        }, format="json", HTTP_IDEMPOTENCY_KEY="cancel-company-fee")
        self.assertEqual(response.status_code, 200, response.data)
        proof = upload(SimpleUploadedFile("fee-refund.pdf", b"%PDF-1.4\nfee refund\n%%EOF"), self.user, scope="transaction")
        response = self.client.post(f"/api/transactions/{source.pk}/refund-cash/", {
            "order": self.order.pk, "amount": "98", "reason": "只退实际收到的原币现金", "voucher": proof.pk,
        }, format="json", HTTP_IDEMPOTENCY_KEY="refund-company-fee")
        self.assertEqual(response.status_code, 201, response.data)
        self.plan.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(self.order.paid_amount, 0)
        self.assertEqual(self.order.outstanding_amount, 0)
        self.assertEqual(self.plan.remaining_amount, 0)
        self.assertEqual(self.plan.planned_amount, 2)
        self.assertEqual(self.plan.settled_amount, 2)
        self.assertEqual(self.plan.status, "settled")
        self.assertEqual(source.refunded_cash_amount(), 98)

    def test_cancellation_after_attributed_refund_preserves_net_cash(self):
        self.assertEqual(self.refund("before-cancel-refund", "10").status_code, 201)
        response = self.client.post(f"/api/orders/{self.order.pk}/cancel/", {
            "reason": "已经原路退回部分款项后取消", "settle_refund": True,
        }, format="json", HTTP_IDEMPOTENCY_KEY="cancel-after-refund")
        self.assertEqual(response.status_code, 200, response.data)
        self.order.refresh_from_db()
        self.plan.refresh_from_db()
        self.assertEqual(self.order.total_amount, 0)
        self.assertEqual(self.order.paid_amount, 90)
        self.assertEqual(self.order.outstanding_amount, 0)
        self.assertEqual(self.plan.settled_amount, 90)
        self.assertEqual(self.plan.planned_amount, 90)
        self.assertEqual(FinanceReceiptRefund.objects.count(), 1)

    def shared_source(self):
        from crm.models import Order
        from crm.services.finance import record_transaction, void_transaction, allocate_advance
        void_transaction(self.receipt, "替换为共享来源夹具")
        other = Order.objects.create(order_no="SHARED-OTHER", customer=self.customer, currency="USD", status="confirmed", order_date=self.order.order_date)
        other.items.create(sku=self.sku, quantity=1, unit_price=100)
        other_plan = PaymentPlan.objects.create(order=other, direction="receivable", currency="USD", planned_amount=100)
        source = record_transaction(dict(kind="unallocated_advance", direction="income", customer=self.customer, amount="300", currency="USD"))
        allocate_advance(source, self.plan, Decimal("100"))
        allocate_advance(source, other_plan, Decimal("100"))
        response = self.client.post(f"/api/orders/{self.order.pk}/cancel/", {
            "reason": "仅取消共享来源中的本订单", "settle_refund": True,
        }, format="json", HTTP_IDEMPOTENCY_KEY="shared-cancel")
        self.assertEqual(response.status_code, 200, response.data)
        return source, other, other_plan

    def test_shared_cash_three_buckets_never_borrow_and_cancelled_plan_stays_closed(self):
        source, other, other_plan = self.shared_source()
        for order in ("", self.order.pk, other.pk):
            response = self.client.post(f"/api/transactions/{source.pk}/refund-cash/", {
                "order": order, "amount": "101", "reason": "测试不得串用其他退款额度", "voucher": self.proof.pk,
            }, format="json", HTTP_IDEMPOTENCY_KEY=f"shared-over-{order}")
            self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(FinanceReceiptRefund.objects.count(), 0)
        for index, order in enumerate((self.order.pk, "", other.pk, self.order.pk)):
            from crm.services.finance_closeout import upload
            proof = upload(SimpleUploadedFile(f"shared-{index}.pdf", f"%PDF-1.4\nshared refund {index}\n%%EOF".encode()), self.user, scope="transaction")
            response = self.client.post(f"/api/transactions/{source.pk}/refund-cash/", {
                "order": order, "amount": "50", "reason": "按原来源及订单分次实际退款", "voucher": proof.pk,
                "actual_date": "2026-10-20",
            }, format="json", HTTP_IDEMPOTENCY_KEY=f"shared-refund-{index}")
            self.assertEqual(response.status_code, 201, response.data)
        self.plan.refresh_from_db()
        other_plan.refresh_from_db()
        self.assertEqual(self.plan.remaining_amount, 0)
        self.assertEqual(self.plan.settled_amount, 0)
        self.assertEqual(self.plan.status, "cancelled")
        self.assertEqual(other_plan.settled_amount, 50)
        self.assertEqual(other_plan.remaining_amount, 50)
        self.assertEqual(other.paid_amount, 50)
        self.assertEqual(source.unallocated_cash_amount, 50)
        self.assertEqual(FinanceReceiptRefund.objects.count(), 4)
        self.assertEqual(set(Transaction.objects.filter(kind="refund").values_list("transaction_date", flat=True)), {__import__("datetime").date(2026, 10, 20)})

    def test_void_shared_receipt_keeps_cancelled_plan_closed_and_reopens_active_plan(self):
        from crm.services.finance import void_transaction
        source, other, other_plan = self.shared_source()
        void_transaction(source, "共享收款作废，分别核对两单")
        self.plan.refresh_from_db()
        other_plan.refresh_from_db()
        self.assertEqual(self.plan.status, "cancelled")
        self.assertEqual(self.plan.planned_amount, 0)
        self.assertEqual(self.plan.remaining_amount, 0)
        self.assertEqual(other_plan.status, "open")
        self.assertEqual(other_plan.planned_amount, 100)
        self.assertEqual(other_plan.remaining_amount, 100)
        self.assertEqual(source.allocations.filter(is_active=True).count(), 0)

    def test_refund_is_bound_to_source_and_replayed(self):
        first = self.refund("refund-one", "20")
        self.assertEqual(first.status_code, 201, first.data)
        replay = self.refund("refund-one", "20")
        self.assertEqual(replay.status_code, 201, replay.data)
        self.assertEqual(replay.headers.get("Idempotent-Replay"), "true")
        self.assertEqual(self.refund("refund-one", "21").status_code, 409)
        self.assertEqual(FinanceReceiptRefund.objects.count(), 1)
        from importlib import import_module
        from types import SimpleNamespace
        from django.apps import apps
        with self.assertRaisesRegex(RuntimeError, "禁止回退丢失退款历史"):
            import_module("crm.migrations.0125_finance_receipt_refund").preserve_refund_links(apps, SimpleNamespace(connection=connection))
        self.plan.refresh_from_db()
        self.assertEqual(self.plan.settled_amount, Decimal("80"))
        self.assertEqual(cash.available(self.receipt), Decimal("80"))
        self.assertEqual(self.refund("refund-over", "81").status_code, 400)

    def test_partly_exchanged_source_only_refunds_remaining_cash(self):
        event, _ = cash.register_event(payload([self.receipt], amounts=["50"], key="BANK-PARTIAL", bank_net_amount="350", fee_amount="5"), self.user)
        cash.confirm_event(event.pk, self.user, voucher_checked=True)
        self.assertEqual(self.refund("refund-over", "51").status_code, 400)
        self.assertEqual(self.refund("refund-exact", "50").status_code, 201)
        self.assertEqual(cash.available(self.receipt), Decimal("0"))
        self.assertEqual(self.receipt.cash_source_allocations.get().amount, Decimal("50"))

    def test_audit_failure_rolls_back_and_same_identity_can_retry(self):
        with patch("crm.views.record_operation", side_effect=RuntimeError("synthetic audit failure")):
            with self.assertRaises(RuntimeError):
                self.refund("refund-retry", "20")
        self.assertEqual(FinanceReceiptRefund.objects.count(), 0)
        self.plan.refresh_from_db()
        self.assertEqual(self.plan.settled_amount, Decimal("100"))
        self.assertEqual(self.refund("refund-retry", "20").status_code, 201)
        self.assertEqual(Transaction.objects.filter(kind="refund").count(), 1)

    def test_unallocated_refund_reduces_later_allocation_and_fx_capacity(self):
        from crm.services.finance import record_transaction, allocate_advance
        source = record_transaction({"transaction_no": "REFUND-ADVANCE", "kind": "unallocated_advance", "direction": "income",
            "customer": self.customer, "amount": "50", "currency": "USD", "exchange_rate": "7", "category": "客户预收"})
        response = self.client.post(f"/api/transactions/{source.pk}/refund-cash/", {
            "amount": "20", "order": "", "reason": "预收款实际退回客户", "voucher": self.proof.pk,
        }, format="json", HTTP_IDEMPOTENCY_KEY="refund-advance")
        self.assertEqual(response.status_code, 201, response.data)
        source.refresh_from_db()
        self.assertEqual(source.unallocated_cash_amount, Decimal("30"))
        self.assertEqual(source.allocation_capacity, Decimal("30"))
        self.assertEqual(cash.available(source), Decimal("30"))
        second = PaymentPlan.objects.create(order=self.order, direction="receivable", currency="USD", planned_amount=50)
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            allocate_advance(source, second, Decimal("31"))
        allocate_advance(source, second, Decimal("30"))

    def test_cny_bank_confirmation_is_not_an_fx_conversion(self):
        from datetime import date
        from crm.models import Order
        from crm.services.finance import record_transaction
        order = Order.objects.create(order_no="REFUND-CNY-ORDER", customer=self.customer, currency="CNY", exchange_rate=1, status="confirmed", order_date=date(2026, 10, 18))
        plan = PaymentPlan.objects.create(order=order, direction="receivable", currency="CNY", planned_amount=100)
        source = record_transaction({"transaction_no": "REFUND-CNY-RECEIPT", "plan": plan, "amount": "100", "currency": "CNY", "exchange_rate": "1"})
        event, _ = cash.register_event(payload([source], currency="CNY", key="REFUND-CNY-BANK", kind="cny_direct", source_account="SYNTH_CNY", rmb_account="SYNTH_CNY", bank_net_amount="100", fee_mode="none", fee_amount="0", quoted_rate=None), self.user)
        cash.confirm_event(event.pk, self.user, voucher_checked=True)
        self.assertEqual(cash.refundable_cash(source), Decimal("100"))
        response = self.client.post(f"/api/transactions/{source.pk}/refund-cash/", {"order": order.pk, "amount": "20", "reason": "已核实人民币退款凭证", "voucher": self.proof.pk}, format="json", HTTP_IDEMPOTENCY_KEY="refund-cny")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(cash.refundable_cash(source), Decimal("80"))
        self.assertEqual(cash.available(source), Decimal("0"))
        refund = Transaction.objects.get(pk=response.data["refunds"][0]["id"])
        debit, _ = cash.register_event(payload([refund], currency="CNY", key="REFUND-CNY-DEBIT", kind="cny_direct", direction="expense", source_account="SYNTH_CNY", rmb_account="SYNTH_CNY", bank_net_amount="20", fee_mode="none", fee_amount="0", quoted_rate=None), self.user)
        cash.confirm_event(debit.pk, self.user, voucher_checked=True)
        self.assertEqual(debit.bank_net_amount, Decimal("20"))

    def test_other_order_historical_refund_does_not_block_known_source(self):
        from datetime import date
        from crm.models import Order
        from crm.services.finance import record_transaction, record_contract_refund
        other = Order.objects.create(order_no="REFUND-OTHER-ORDER", customer=self.customer, currency="USD", exchange_rate=7, status="confirmed", order_date=date(2026, 10, 18))
        other_plan = PaymentPlan.objects.create(order=other, direction="receivable", currency="USD", planned_amount=100)
        record_transaction({"transaction_no": "REFUND-OTHER-RECEIPT", "plan": other_plan, "amount": "100", "currency": "USD", "exchange_rate": "7"})
        record_contract_refund(other, {"amount": "10", "currency": "USD"})
        self.assertEqual(self.refund("refund-own-order", "20").status_code, 201)

    def test_reference_fx_difference_cannot_be_created_as_cash(self):
        response = self.client.post("/api/transactions/", {"transaction_no": "FX-NOT-CASH", "transaction_date": "2026-10-18", "kind": "exchange_difference", "direction": "expense", "category": "汇兑损失", "amount": "10", "currency": "CNY", "exchange_rate": "1"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("不是实际收付款", str(response.data))
        self.assertFalse(Transaction.objects.filter(transaction_no="FX-NOT-CASH").exists())

    def test_direct_customer_refund_requires_original_receipt_and_evidence(self):
        response = self.client.post("/api/transactions/", {"transaction_no": "REFUND-NO-SOURCE", "transaction_date": "2026-10-18", "kind": "refund", "direction": "expense", "category": "客户退款", "amount": "10", "currency": "USD", "exchange_rate": "7", "order": self.order.pk}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("从原收款详情", str(response.data))
        self.assertFalse(Transaction.objects.filter(transaction_no="REFUND-NO-SOURCE").exists())

    def test_actual_rate_rounding_does_not_override_confirmed_gross(self):
        values = payload([self.receipt], amounts=["100000"], key="ROUNDING-GROSS", gross_rmb_amount="999999.99", bank_net_amount="999999.99", fee_mode="none", fee_amount="0")
        normalized = cash.normalize(values)
        self.assertEqual(normalized["actual_rate"], "10.000000")
        self.assertEqual(normalized["gross_rmb_amount"], "999999.99")
        from rest_framework.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            cash.normalize({**values, "actual_rate": "10.000000"})

    def test_orderless_customer_receipt_can_be_partially_exchanged_from_detail(self):
        from crm.services.finance import record_customer_receipt
        source, _ = record_customer_receipt({"transaction_no": "NO-ORDER-RECEIPT", "customer": self.customer,
            "amount": "100", "currency": "USD", "exchange_rate": None}, self.user)
        response = self.client.get('/api/rmb-cash-events/sources/', {'family_root': source.pk, 'currency': 'USD'})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual([row['id'] for row in response.data['results']], [source.pk])
        event, _ = cash.register_event(payload([source], amounts=["40"], key="NO-ORDER-FX", source_receipt_id=source.pk,
            gross_rmb_amount="284.00", bank_net_amount="284.00", fee_mode="none", fee_amount="0"), self.user)
        cash.confirm_event(event.pk, self.user, voucher_checked=True)
        self.assertEqual(cash.available(source), Decimal("60"))
        self.assertEqual(source.allocations.count(), 0)
        detail = self.client.get(f'/api/rmb-cash-events/{event.pk}/')
        self.assertEqual(detail.status_code, 200, detail.data)
        self.assertIsNone(detail.data['reference_amount'])
        self.assertIsNone(detail.data['pre_fee_reference_delta'])
        self.assertEqual(Decimal(detail.data['quoted_reference_delta']), Decimal('0'))

    def test_one_settlement_from_receipt_can_combine_another_receipt(self):
        from crm.services.finance import record_customer_receipt
        sources = [record_customer_receipt({"transaction_no": f"MERGE-NO-ORDER-{i}", "customer": self.customer,
            "amount": "100", "currency": "USD", "exchange_rate": None}, self.user)[0] for i in (1, 2)]
        event, _ = cash.register_event(payload(sources, amounts=["40", "60"], key="MERGE-FROM-RECEIPT", source_receipt_id=sources[0].pk,
            gross_rmb_amount="710.00", bank_net_amount="710.00", fee_mode="none", fee_amount="0"), self.user)
        cash.confirm_event(event.pk, self.user, voucher_checked=True)
        self.assertEqual([cash.available(row) for row in sources], [Decimal("60"), Decimal("40")])
        self.assertEqual(event.sources.count(), 2)
        self.assertFalse(any(row.allocations.exists() for row in sources))


@override_settings(RMB_CASH_ACCOUNT_IDS=("SYNTH_FX", "SYNTH_CNY"))
class ReceiptRefundConcurrencyTests(CashFixture, TransactionTestCase):
    def test_concurrent_refunds_cannot_exceed_original_cash(self):
        if connection.vendor != "postgresql":
            self.skipTest("Requires PostgreSQL row locks")
        self.setup_cash()
        from crm.services.finance_closeout import upload
        proofs = [upload(SimpleUploadedFile(f"refund-{i}.pdf", f"%PDF-1.4\nsynthetic refund {i}\n%%EOF".encode()), self.user, scope="transaction") for i in range(2)]
        barrier = Barrier(2)
        def run(i):
            try:
                client = APIClient()
                barrier.wait(timeout=10)
                response = client.post(f"/api/transactions/{self.receipt.pk}/refund-cash/", {
                    "amount": "70", "order": self.order.pk, "reason": "合成退款凭证已经核实", "voucher": proofs[i].pk,
                }, format="json", HTTP_IDEMPOTENCY_KEY=f"concurrent-refund-{i}")
                return response.status_code
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertCountEqual(list(pool.map(run, range(2))), [201, 400])
        self.assertEqual(FinanceReceiptRefund.objects.count(), 1)
        self.assertEqual(cash.available(self.receipt), Decimal("30"))
