from datetime import date
from decimal import Decimal
import hashlib
import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.files.base import ContentFile
from django.test import TestCase, TransactionTestCase, override_settings
from django.db import close_old_connections, connection, connections
from django.contrib.auth.models import AnonymousUser
from rest_framework.test import APIClient

from crm.models import AdvanceAllocation, ContractChangeRequest, Customer, FinancePlanWriteoff, FinanceReceiptAdjustment, FinanceVoucher, OperationLog, Order, PaymentPlan, Product, RmbCashEvent, SKU, Transaction
from crm.services.finance import approve_contract_change, record_contract_refund, record_customer_receipt


@override_settings(
    APP_STAGE="development", DEBUG=True, DEVELOPMENT_SUPERADMIN=True,
    RBAC_ENFORCEMENT=False, AUDIT_LOG_ENABLED=True,
)
class CustomerReceiptOptimizationTests(TestCase):
    def setUp(self):
        self.media = tempfile.TemporaryDirectory(prefix="receipt-optimization-")
        self.settings = override_settings(MEDIA_ROOT=self.media.name)
        self.settings.enable()
        self.addCleanup(self.settings.disable)
        self.addCleanup(self.media.cleanup)
        self.user = get_user_model().objects.create_user(
            username="receipt-finance-test", password="unused", is_superuser=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.customer = Customer.objects.create(code="RCPT-C", name="合成收款客户")
        product = Product.objects.create(code="RCPT-P", name="合成产品")
        self.sku = SKU.objects.create(product=product, sku="RCPT-SKU")

    def order_and_plan(self, suffix, net_amount="1000", *, discount="0", currency="USD", rate="7.2"):
        order = Order.objects.create(
            order_no=f"RCPT-{suffix}", customer=self.customer, currency=currency,
            exchange_rate=rate, status="confirmed", order_date=date(2026, 11, 1),
            discount=discount,
        )
        order.items.create(sku=self.sku, quantity=1, unit_price=Decimal(net_amount) + Decimal(discount))
        plan = PaymentPlan.objects.create(
            order=order, direction="receivable", currency=currency, planned_amount=net_amount,
        )
        return order, plan

    def voucher(self, name="synthetic-receipt-proof.pdf"):
        content = b"%PDF-1.4\nSynthetic receipt evidence\n%%EOF"
        proof = FinanceVoucher(
            original_name=name, sha256=hashlib.sha256(content).hexdigest(), size=len(content),
            scope="transaction", bank_sources=[], actor={"kind": "synthetic_fixture"},
        )
        proof.file.save(f"{uuid.uuid4().hex}.pdf", ContentFile(content), save=False)
        proof.save()
        return proof

    def receipt_payload(self, number, *, amount="985", customer=None, order=None, currency="USD",
                        remittance="990", adjustments=None, plan_allocations=None, exchange_rate="7.2"):
        payload = {
            "transaction_no": number, "transaction_date": "2026-11-06", "direction": "income",
            "kind": "customer_receipt", "category": "客户收款", "amount": amount,
            "currency": currency, "customer": (customer or self.customer).pk,
            "remittance_amount": remittance, "payment_method": "银行转账", "reference": f"SYN-{number}",
            "receipt_adjustments": adjustments or [],
        }
        if order:
            payload["order"] = order.pk
        if exchange_rate is not None:
            payload["exchange_rate"] = exchange_rate
        if plan_allocations is not None:
            payload["plan_allocations"] = plan_allocations
        return payload

    def post_receipt(self, payload, expected=201):
        response = self.client.post("/api/transactions/", payload, format="json")
        self.assertEqual(response.status_code, expected, getattr(response, "data", response.content))
        return response

    def test_company_fee_and_authorized_discount_settle_without_creating_cash_twice(self):
        order, plan = self.order_and_plan("COMPANY")
        proof = self.voucher()
        payload = self.receipt_payload("RCPT-COMPANY", order=order, adjustments=[
            {"nature": "discount", "amount": "10", "handling": "applied", "reason": "已批准优惠减免", "evidence": proof.pk, "plan": plan.pk},
            {"nature": "bank_fee", "amount": "5", "handling": "company", "reason": "中转行扣费由我方承担", "evidence": proof.pk},
        ])

        response = self.post_receipt(payload)
        row = Transaction.objects.get(pk=response.data["id"])
        plan.refresh_from_db()
        order.refresh_from_db()

        self.assertEqual(row.amount, Decimal("985"))
        self.assertEqual(row.remittance_amount, Decimal("990"))
        self.assertEqual(row.bank_fee_amount, Decimal("5"))
        self.assertEqual(row.allocated_amount, Decimal("990"))
        self.assertEqual(plan.settled_amount, Decimal("990"))
        self.assertEqual(plan.remaining_amount, Decimal("0"))
        allocation = AdvanceAllocation.objects.get(advance=row, plan=plan)
        self.assertEqual(allocation.cash_amount, Decimal("985"))
        self.assertEqual(allocation.fee_credit_amount, Decimal("5"))
        self.assertEqual(order.paid_amount, Decimal("985"))
        self.assertEqual(order.outstanding_amount, Decimal("0"))
        from crm.services.profit import order_profit_summary
        profit = order_profit_summary(order)
        self.assertEqual(profit["receipt_bank_fee_rmb"], Decimal("36"))
        self.assertEqual(profit["receivable_reduction_rmb"], Decimal("72"))
        self.assertEqual(profit["estimated_profit_rmb"], Decimal("7092"))
        metrics = self.client.get("/api/finance-dashboard/", {"date_from": "2026-11-01", "date_to": "2026-11-30"}).data["metrics"]
        self.assertEqual(metrics["estimated_profit_rmb"], Decimal("7092"))
        self.assertEqual(metrics["order_expense_rmb"], Decimal("36"))
        self.assertEqual(metrics["receivable_reduction_rmb"], Decimal("72"))
        reduction_details = self.client.get("/api/finance-dashboard/details/", {"metric": "receivable_reduction_rmb", "date_from": "2026-11-01", "date_to": "2026-11-30"})
        self.assertEqual(reduction_details.status_code, 200)
        self.assertEqual(reduction_details.data["total_amount"], Decimal("72"))
        self.assertEqual(FinancePlanWriteoff.objects.get(source_transaction=row).amount, Decimal("10"))
        self.assertEqual(RmbCashEvent.objects.count(), 0)
        actual_cash = self.client.get("/api/actual-rmb-cash/", {"date_from": "2026-11-01", "date_to": "2026-11-30"})
        self.assertEqual(actual_cash.status_code, 200)
        self.assertEqual(Decimal(actual_cash.data["totals"]["inflow"]), Decimal("0"))
        self.assertEqual(response.data["fx_available_amount"], Decimal("985"))
        self.assertEqual(response.data["receipt_adjustment_rows"][0]["evidence_name"], proof.original_name)
        self.assertEqual(OperationLog.objects.filter(entity="crm.financereceiptadjustment").count(), 2)
        self.assertEqual(OperationLog.objects.filter(entity="crm.financeplanwriteoff").count(), 1)

    def test_customer_borne_fee_and_unverified_difference_leave_receivable_open(self):
        order, plan = self.order_and_plan("CUSTOMER-FEE")
        proof = self.voucher()
        response = self.post_receipt(self.receipt_payload("RCPT-CUSTOMER-FEE", order=order, adjustments=[
            {"nature": "discount", "amount": "10", "handling": "applied", "reason": "已批准优惠减免", "evidence": proof.pk, "plan": plan.pk},
            {"nature": "bank_fee", "amount": "5", "handling": "customer", "reason": "合同約定客户承担扣费", "evidence": proof.pk},
        ]))
        row = Transaction.objects.get(pk=response.data["id"])
        plan.refresh_from_db()
        self.assertEqual(row.allocated_amount, Decimal("985"))
        self.assertEqual(plan.remaining_amount, Decimal("5"))
        self.assertEqual(FinancePlanWriteoff.objects.filter(source_transaction=row).count(), 1)
        self.assertEqual(AdvanceAllocation.objects.get(advance=row).fee_credit_amount, Decimal("0"))

        order2, plan2 = self.order_and_plan("PENDING")
        proof2 = self.voucher("pending-difference.pdf")
        response2 = self.post_receipt(self.receipt_payload("RCPT-PENDING", order=order2, remittance="990", adjustments=[
            {"nature": "pending_difference", "amount": "5", "handling": "pending", "reason": "差额来源待银行核实", "evidence": proof2.pk},
        ]))
        pending = Transaction.objects.get(pk=response2.data["id"])
        plan2.refresh_from_db()
        self.assertEqual(pending.amount, Decimal("985"))
        self.assertEqual(plan2.remaining_amount, Decimal("15"))
        self.assertFalse(FinancePlanWriteoff.objects.filter(source_transaction=pending).exists())

    def test_existing_order_discount_is_informational_and_cannot_be_applied_twice(self):
        order, plan = self.order_and_plan("ORDER-DISCOUNT", discount="10")
        proof = self.voucher()
        payload = self.receipt_payload("RCPT-ORDER-DISCOUNT", amount="1000", remittance="1000", order=order, adjustments=[
            {"nature": "discount", "amount": "10", "handling": "already_in_order", "reason": "訂單金額已含批准優惠", "evidence": proof.pk, "plan": plan.pk},
        ])
        row = Transaction.objects.get(pk=self.post_receipt(payload).data["id"])
        plan.refresh_from_db()
        self.assertEqual(plan.remaining_amount, Decimal("0"))
        self.assertFalse(FinancePlanWriteoff.objects.filter(source_transaction=row).exists())

        duplicate = self.receipt_payload("RCPT-DUP-DISCOUNT", amount="990", remittance="990", order=order, adjustments=[
            {"nature": "discount", "amount": "10", "handling": "applied", "reason": "试图重复抵减订单优惠", "evidence": proof.pk, "plan": plan.pk},
        ])
        response = self.client.post("/api/transactions/", duplicate, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Transaction.objects.filter(transaction_no="RCPT-DUP-DISCOUNT").exists())

    def test_approved_order_reduction_is_linked_once_without_an_extra_writeoff(self):
        order, plan = self.order_and_plan("FORMAL-CHANGE")
        change = ContractChangeRequest.objects.create(order=order, amount_delta="-10", notes="批准合同降价")
        approve_contract_change(change)
        plan.refresh_from_db()
        self.assertEqual(plan.planned_amount, Decimal("990"))
        payload = self.receipt_payload("RCPT-FORMAL-CHANGE", amount="990", remittance="990", order=order, adjustments=[
            {"nature": "discount", "amount": "10", "handling": "already_in_order", "reason": "已按批准合同修订降价", "plan": plan.pk, "contract_change": change.pk},
        ])
        row = Transaction.objects.get(pk=self.post_receipt(payload).data["id"])
        self.assertEqual(row.receipt_adjustments.get().contract_change_id, change.pk)
        self.assertFalse(FinancePlanWriteoff.objects.filter(source_transaction=row).exists())
        duplicate = self.receipt_payload("RCPT-FORMAL-CHANGE-DUP", amount="1", remittance="1", order=order, adjustments=[
            {"nature": "discount", "amount": "1", "handling": "already_in_order", "reason": "再次使用同一合同修订", "plan": plan.pk, "contract_change": change.pk},
        ])
        self.assertEqual(self.client.post("/api/transactions/", duplicate, format="json").status_code, 400)

    def test_receipt_retry_is_idempotent_and_overallocation_rolls_back_every_write(self):
        settled_order, settled_plan = self.order_and_plan("SETTLED-RETRY")
        settled_proof = self.voucher("settled-retry-discount.pdf")
        settled_payload = self.receipt_payload("RCPT-SETTLED-RETRY", amount="990", remittance="990", order=settled_order, adjustments=[
            {"nature": "discount", "amount": "10", "handling": "applied", "reason": "已批准优惠抵减应收", "evidence": settled_proof.pk, "plan": settled_plan.pk},
        ])
        first_settled = self.post_receipt(settled_payload)
        settled_plan.refresh_from_db()
        self.assertEqual(settled_plan.status, "settled")
        retried_settled = self.post_receipt(settled_payload, expected=200)
        self.assertEqual(first_settled.data["id"], retried_settled.data["id"])
        self.assertEqual(FinancePlanWriteoff.objects.filter(source_transaction_id=first_settled.data["id"]).count(), 1)

        order, plan = self.order_and_plan("RETRY")
        proof = self.voucher()
        payload = self.receipt_payload("RCPT-RETRY", order=order, adjustments=[
            {"nature": "bank_fee", "amount": "5", "handling": "company", "reason": "银行已出具扣费凭证", "evidence": proof.pk},
        ])
        first = self.post_receipt(payload)
        second = self.post_receipt(payload, expected=200)
        self.assertEqual(first.data["id"], second.data["id"])
        self.assertEqual(Transaction.objects.filter(transaction_no="RCPT-RETRY").count(), 1)
        self.assertEqual(FinanceReceiptAdjustment.objects.filter(transaction_id=first.data["id"]).count(), 1)
        self.assertEqual(OperationLog.objects.filter(entity="crm.transaction", object_id=str(first.data["id"])).count(), 1)

        rollback_order, rollback_plan = self.order_and_plan("ROLLBACK")
        rollback_proof = self.voucher("rollback-fee.pdf")
        over = self.receipt_payload("RCPT-OVER-ALLOC", order=rollback_order, adjustments=[
            {"nature": "discount", "amount": "10", "handling": "applied", "reason": "已批准优惠抵减应收", "evidence": rollback_proof.pk, "plan": rollback_plan.pk},
            {"nature": "bank_fee", "amount": "5", "handling": "company", "reason": "银行已出具扣费凭证", "evidence": rollback_proof.pk},
        ], plan_allocations=[{"plan": rollback_plan.pk, "amount": "991"}])
        rejected = self.client.post("/api/transactions/", over, format="json")
        self.assertEqual(rejected.status_code, 400)
        self.assertFalse(Transaction.objects.filter(transaction_no="RCPT-OVER-ALLOC").exists())
        self.assertFalse(FinanceReceiptAdjustment.objects.filter(transaction__transaction_no="RCPT-OVER-ALLOC").exists())
        self.assertFalse(FinancePlanWriteoff.objects.filter(source_transaction__transaction_no="RCPT-OVER-ALLOC").exists())
        rollback_plan.refresh_from_db()
        self.assertEqual(rollback_plan.settled_amount, Decimal("0"))
        self.assertEqual(rollback_plan.remaining_amount, Decimal("1000"))

        malformed = self.receipt_payload("RCPT-BAD-AMOUNT", amount="", remittance="", order=rollback_order)
        bad = self.client.post("/api/transactions/", malformed, format="json")
        self.assertEqual(bad.status_code, 400)
        self.assertFalse(Transaction.objects.filter(transaction_no="RCPT-BAD-AMOUNT").exists())

    def test_audit_failure_rolls_back_receipt_deductions_and_plan_allocation(self):
        order, plan = self.order_and_plan("AUDIT-ROLLBACK")
        proof = self.voucher()
        payload = self.receipt_payload("RCPT-AUDIT-ROLLBACK", order=order, adjustments=[
            {"nature": "discount", "amount": "10", "handling": "applied", "reason": "已批准优惠抵减应收", "evidence": proof.pk, "plan": plan.pk},
            {"nature": "bank_fee", "amount": "5", "handling": "company", "reason": "我方承担银行扣费", "evidence": proof.pk},
        ])
        with patch("crm.views.record_operation", side_effect=RuntimeError("synthetic audit failure")):
            with self.assertRaises(RuntimeError):
                self.client.post("/api/transactions/", payload, format="json")
        self.assertFalse(Transaction.objects.filter(transaction_no=payload["transaction_no"]).exists())
        self.assertFalse(FinanceReceiptAdjustment.objects.exists())
        self.assertFalse(FinancePlanWriteoff.objects.exists())
        self.assertFalse(AdvanceAllocation.objects.exists())
        plan.refresh_from_db()
        self.assertEqual(plan.settled_amount, Decimal("0"))
        self.assertEqual(plan.remaining_amount, Decimal("1000"))

    def test_multi_order_allocation_currency_defaults_and_refund_cap_use_real_cash(self):
        order_a, plan_a = self.order_and_plan("MULTI-A", net_amount="100")
        order_b, plan_b = self.order_and_plan("MULTI-B", net_amount="200")
        response = self.post_receipt(self.receipt_payload(
            "RCPT-MULTI", amount="150", remittance="150", order=None,
            plan_allocations=[{"plan": plan_a.pk, "amount": "50"}, {"plan": plan_b.pk, "amount": "100"}],
        ))
        receipt = Transaction.objects.get(pk=response.data["id"])
        self.assertEqual(receipt.allocations.count(), 2)
        self.assertEqual(order_a.outstanding_amount, Decimal("50"))
        self.assertEqual(order_b.outstanding_amount, Decimal("100"))

        refund_order, refund_plan = self.order_and_plan("REFUND-CAP", net_amount="1000")
        proof = self.voucher("refund-cap-fee.pdf")
        refund_receipt = Transaction.objects.get(pk=self.post_receipt(self.receipt_payload(
            "RCPT-REFUND-CAP", order=refund_order, amount="985", remittance="990", adjustments=[
                {"nature": "bank_fee", "amount": "5", "handling": "company", "reason": "我方承担的银行扣费", "evidence": proof.pk},
            ],
        )).data["id"])
        self.assertEqual(refund_order.paid_amount, Decimal("985"))
        with self.assertRaises(DjangoValidationError):
            record_contract_refund(refund_order, {"amount": "986", "currency": "USD"})

        order_cny, plan_cny = self.order_and_plan("CNY", net_amount="100", currency="CNY", rate="1")
        cny_response = self.post_receipt(self.receipt_payload(
            "RCPT-CNY", amount="100", remittance="100", order=order_cny, currency="CNY", exchange_rate="1",
        ))
        self.assertFalse(cny_response.data["reference_rate_missing"])
        self.assertEqual(Decimal(cny_response.data["rmb_amount"]), Decimal("100"))
        known_reference = self.post_receipt(self.receipt_payload(
            "RCPT-USD-REFERENCE", amount="5", remittance="5", order=None, exchange_rate="7.2",
        ))
        self.assertEqual(Decimal(known_reference.data["rmb_amount"]), Decimal("36"))
        before_unknown_reference = self.client.get("/api/finance-dashboard/").data["metrics"]
        no_order_usd = self.receipt_payload("RCPT-USD-NO-ORDER", amount="25", remittance="25", order=None, exchange_rate=None)
        no_order_usd.pop("exchange_rate", None)
        no_order_usd.pop("currency")
        usd_response = self.post_receipt(no_order_usd)
        self.assertTrue(usd_response.data["reference_rate_missing"])
        self.assertEqual(usd_response.data["currency"], "USD")
        self.assertEqual(Decimal(usd_response.data["rmb_amount"]), Decimal("0"))
        self.assertIsNone(usd_response.data["exchange_rate"])
        after_unknown_reference = self.client.get("/api/finance-dashboard/").data["metrics"]
        self.assertEqual(after_unknown_reference["income_rmb"], before_unknown_reference["income_rmb"])
        self.assertEqual(after_unknown_reference["advance_receipt_rmb"], before_unknown_reference["advance_receipt_rmb"])
        advance_details = self.client.get("/api/finance-dashboard/details/", {"metric": "advance_receipt_rmb"})
        self.assertEqual(advance_details.status_code, 200)
        self.assertEqual(advance_details.data["total_amount"], after_unknown_reference["advance_receipt_rmb"])
        jpy = self.receipt_payload("RCPT-JPY-NO-ORDER", amount="25", remittance="25", currency="JPY", order=None, exchange_rate=None)
        jpy.pop("exchange_rate", None)
        jpy_response = self.post_receipt(jpy)
        self.assertEqual(jpy_response.data["currency"], "JPY")
        self.assertEqual(Decimal(jpy_response.data["amount"]), Decimal("25"))
        self.assertTrue(jpy_response.data["reference_rate_missing"])


@skipUnless(connection.vendor == "postgresql", "Receipt row-lock tests require PostgreSQL")
@override_settings(APP_STAGE="development", DEBUG=True, DEVELOPMENT_SUPERADMIN=True, RBAC_ENFORCEMENT=False)
class ReceiptConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.customer = Customer.objects.create(code="PG-RCPT-C", name="合成并发收款客户")
        sku = SKU.objects.create(sku="PG-RCPT-SKU", product=Product.objects.create(code="PG-RCPT-P", name="合成产品"))
        self.order = Order.objects.create(order_no="PG-RCPT-O", customer=self.customer, currency="USD", exchange_rate="7.2", status="confirmed", order_date=date(2026, 11, 8))
        self.order.items.create(sku=sku, quantity=1, unit_price="1000")
        self.plan = PaymentPlan.objects.create(order=self.order, direction="receivable", currency="USD", planned_amount="1000")

    def race(self, callback):
        barrier = Barrier(2)
        def run(index):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return callback(index)
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as executor:
            return list(executor.map(run, range(2)))

    def payload(self, number, value):
        return dict(transaction_no=number, transaction_date=date(2026, 11, 8), customer=self.customer, order=self.order, amount=value, remittance_amount=value, currency="USD", exchange_rate="7.2")

    def test_same_request_after_concurrent_full_settlement_creates_one_receipt(self):
        payload = self.payload("PG-RCPT-SAME", "1000")
        results = self.race(lambda _: record_customer_receipt(payload, AnonymousUser()))
        self.assertEqual(results[0][0].pk, results[1][0].pk)
        self.assertCountEqual([result[1] for result in results], [True, False])
        self.assertEqual(Transaction.objects.count(), 1)
        self.assertEqual(AdvanceAllocation.objects.count(), 1)
        self.plan.refresh_from_db()
        self.assertEqual(self.plan.remaining_amount, Decimal("0"))

    def test_competing_explicit_allocations_reject_the_overallocation_atomically(self):
        def write(index):
            payload = self.payload(f"PG-RCPT-RACE-{index}", "600")
            payload["plan_allocations"] = [{"plan": self.plan.pk, "amount": "600"}]
            try:
                record_customer_receipt(payload, AnonymousUser())
                return "created"
            except DjangoValidationError:
                return "rejected"
        self.assertCountEqual(self.race(write), ["created", "rejected"])
        self.assertEqual(Transaction.objects.count(), 1)
        self.assertEqual(AdvanceAllocation.objects.count(), 1)
        self.plan.refresh_from_db()
        self.assertEqual(self.plan.settled_amount, Decimal("600"))
        self.assertEqual(self.plan.remaining_amount, Decimal("400"))

