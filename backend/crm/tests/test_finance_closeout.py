import tempfile
import uuid
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.exceptions import APIException
from rest_framework.test import APIClient

from crm.models import FinanceAccount, FinanceFact, FinanceInstruction, FinanceReview, OperationLog
from crm.services import finance_closeout as ledger


class CloseoutFixture:
    def setup_ledger(self):
        self.media = tempfile.TemporaryDirectory(prefix="finance-closeout-test-")
        self.addCleanup(self.media.cleanup)
        self.settings_override = override_settings(MEDIA_ROOT=self.media.name)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        User = get_user_model()
        self.maker = User.objects.create_superuser("finance-maker", "", None)
        self.reviewer = User.objects.create_superuser("finance-reviewer", "", None)
        self.account = ledger.create_account({"code": "SYNTH-BANK", "name": "合成银行", "account_type": "bank", "ownership": "own", "ownership_reason": "合成开户核实"}, self.maker)
        self.second = ledger.create_account({"code": "SYNTH-CASH", "name": "合成现金", "account_type": "cash", "ownership": "own", "ownership_reason": "合成现金保管核实"}, self.maker)
        self.proof = ledger.upload(SimpleUploadedFile("synthetic.pdf", b"%PDF-1.4\nSynthetic voucher only\n%%EOF"), self.maker)

    def data(self, **changes):
        key = "SYNTH-" + uuid.uuid4().hex
        value = {"request_key": key, "kind": "cash", "account": self.account.pk,
            "voucher": self.proof.pk, "actual_date": "2026-01-02", "amount": "100.00",
            "direction": "income", "nature": "unclassified", "truth": "verified",
            "source_system": "SYNTH-LEGACY", "source_key": key, "reason": "合成凭证核实"}
        value.update(changes)
        return value

    def fact(self, **changes):
        obj, _ = ledger.submit(self.data(**changes), self.maker)
        if obj.kind in ledger.APPROVAL_KINDS:
            ledger.approve(obj.pk, self.reviewer)
        return ledger.post(obj.pk, self.maker, voucher_checked=True)


class FinanceCloseoutTests(CloseoutFixture, TestCase):
    def setUp(self):
        self.setup_ledger()

    def test_persistent_identity_and_conflicting_payload(self):
        data = self.data()
        obj, created = ledger.submit(data, self.maker)
        again, created_again = ledger.submit(data, self.maker)
        self.assertTrue(created)
        self.assertFalse(created_again)
        self.assertEqual(obj.pk, again.pk)
        with self.assertRaises(APIException):
            ledger.submit({**data, "amount": "101.00"}, self.maker)
        first = ledger.post(obj.pk, self.maker, voucher_checked=True)
        logs = OperationLog.objects.count()
        self.assertEqual(first.pk, ledger.post(obj.pk, self.maker, voucher_checked=True).pk)
        self.assertEqual(logs, OperationLog.objects.count())
        self.assertEqual(FinanceFact.objects.count(), 1)

    def test_distinct_same_amount_requires_review_then_remains_legal(self):
        self.fact()
        data = self.data()
        p = ledger.normalize(data)
        candidates = ledger.duplicate_candidates(p)
        data.update(duplicate_review_token=candidates["token"], duplicate_review_reason="对账单为两笔独立交易")
        second, _ = ledger.submit(data, self.maker)
        ledger.post(second.pk, self.maker, voucher_checked=True)
        self.assertEqual(FinanceFact.objects.count(), 2)

    def test_pending_classification_is_independent_from_verified_voucher(self):
        fact = self.fact(nature="unclassified")
        self.assertEqual(fact.nature, "unclassified")
        ledger.classify({"fact": fact.pk, "nature": "interest", "reason": "合成银行利息说明"}, self.maker)
        fact.refresh_from_db()
        self.assertEqual(fact.nature, "unclassified")
        self.assertEqual(fact.classifications.get().nature, "interest")
        for truth in ("needs_verification", "simulated"):
            pending, _ = ledger.submit(self.data(truth=truth), self.maker)
            with self.assertRaises(APIException):
                ledger.post(pending.pk, self.maker, voucher_checked=True)

    def test_opening_is_separate_and_late_fact_invalidates_review(self):
        self.fact(kind="opening", actual_date="2026-01-01", amount="1000.00")
        self.fact(amount="100.00")
        self.assertEqual(ledger.balance(self.account, "2026-01-31")[0], Decimal("1100.00"))
        review = ledger.reconcile({"account": self.account.pk, "date_from": "2026-01-01", "date_to": "2026-01-31",
            "voucher": self.proof.pk, "statement_balance": "1100.00", "completed": True, "reason": "合成月末核对"}, self.maker)
        self.fact(actual_date="2026-01-03", amount="20.00")
        self.assertNotEqual(review.fingerprint, ledger.balance(self.account, review.date_to)[1])
        events = ledger.reporting_events(self.maker, "2026-01-01", "2026-01-31")
        self.assertEqual(sum(e.bank_net_amount for e in events), Decimal("120.00"))
        with self.assertRaises(APIException):
            ledger.reconcile({"account": self.account.pk, "date_from": "2026-01-01", "date_to": "2026-01-31",
                "voucher": self.proof.pk, "statement_balance": "1.00", "completed": True, "reason": "差异未处理"}, self.maker)

    def test_zero_opening_and_negative_balance_are_preserved(self):
        self.fact(kind="opening", actual_date="2026-01-01", amount="0.00")
        self.fact(direction="expense", amount="10.00")
        self.assertEqual(ledger.balance(self.account, "2026-01-31")[0], Decimal("-10.00"))

    def test_approved_correction_replaces_effective_fact_without_fake_cash_outflow(self):
        self.fact(kind="opening", amount="1000.00", actual_date="2026-01-01")
        original = self.fact(amount="100.00")
        review = ledger.reconcile({"account": self.account.pk, "date_from": "2026-01-01", "date_to": "2026-01-31", "voucher": self.proof.pk, "statement_balance": "1100.00", "completed": True, "reason": "合成月末核对"}, self.maker)
        corrected = self.fact(kind="correction", parent=original.pk, amount="90.00", direction="income", actual_date="2026-02-02")
        original.refresh_from_db()
        self.assertEqual(original.amount, Decimal("100.00"))
        self.assertEqual(ledger.reporting_events(self.maker, "2026-01-01", "2026-01-31"), [])
        active = ledger.reporting_events(self.maker, "2026-02-01", "2026-02-28")
        self.assertEqual([(e.pk, e.direction, e.bank_net_amount) for e in active], [(-corrected.pk, "income", Decimal("90.00"))])
        self.assertEqual(ledger.balance(self.account, "2026-01-31")[0], Decimal("1000.00"))
        self.assertEqual(ledger.balance(self.account, "2026-02-28")[0], Decimal("1090.00"))
        self.assertNotEqual(review.fingerprint, ledger.balance(self.account, review.date_to)[1])
        self.fact(kind="correction", parent=corrected.pk, amount="0.00", actual_date="2026-02-02")
        self.assertEqual(ledger.reporting_events(self.maker, "2026-02-01", "2026-02-28"), [])

    def test_transfer_cross_day_explicit_match_keeps_account_facts(self):
        out = self.fact(direction="expense", nature="internal_principal")
        inc = self.fact(account=self.second.pk, actual_date="2026-01-03", nature="internal_principal")
        self.assertEqual(len(ledger.reporting_events(self.maker, "2026-01-01", "2026-01-31")), 2)
        match = ledger.match_transfer({"outgoing": out.pk, "incoming": inc.pk, "reason": "合成两端凭证核实"}, self.maker)
        self.assertEqual(match.pk, ledger.match_transfer({"outgoing": out.pk, "incoming": inc.pk, "reason": "重复核查"}, self.maker).pk)
        self.assertEqual(ledger.reporting_events(self.maker, "2026-01-01", "2026-01-31"), [])
        self.assertEqual(FinanceFact.objects.count(), 2)
        fee = self.fact(direction="expense", nature="bank_fee", amount="2.00")
        self.assertEqual([e.pk for e in ledger.reporting_events(self.maker, "2026-01-01", "2026-01-31")], [-fee.pk])

    def test_transfer_difference_not_assumed_fee(self):
        out = self.fact(direction="expense", nature="internal_principal")
        inc = self.fact(account=self.second.pk, nature="internal_principal", amount="99.00")
        with self.assertRaises(APIException):
            ledger.match_transfer({"outgoing": out.pk, "incoming": inc.pk, "reason": "有差额"}, self.maker)

    def test_bank_return_partial_cumulative_cap_and_original_unchanged(self):
        original = self.fact()
        self.fact(kind="bank_return", parent=original.pk, direction="expense", amount="40.00")
        self.fact(kind="bank_return", parent=original.pk, direction="expense", amount="60.00", actual_date="2026-01-03")
        with self.assertRaises(APIException):
            self.fact(kind="bank_return", parent=original.pk, direction="expense", amount="0.01")
        original.refresh_from_db()
        self.assertEqual(original.amount, Decimal("100.00"))
        self.assertEqual(FinanceFact.objects.count(), 3)

    def test_refund_approved_not_paid_and_excess_separately_recorded(self):
        receipt = self.fact()
        approval, _ = ledger.submit(self.data(kind="refund_approval", amount="150.00", direction="expense", parent=receipt.pk, excess_reason="批准额外赔偿50元"), self.maker)
        ledger.approve(approval.pk, self.reviewer)
        self.assertEqual(FinanceFact.objects.count(), 1)
        with self.assertRaises(APIException):
            ledger.post(approval.pk, self.maker, voucher_checked=True)
        paid = self.fact(kind="refund_payment", amount="150.00", direction="expense", approval=approval.pk, nature="commercial_refund")
        self.assertEqual(paid.excess_amount, Decimal("50.00"))
        self.fact(kind="refund_return", direction="income", amount="50.00", parent=paid.pk)
        with self.assertRaises(APIException):
            self.fact(kind="refund_payment", amount="0.01", direction="expense", approval=approval.pk)

    def test_separation_of_duties_and_cancelled_revision(self):
        original = self.fact()
        obj, _ = ledger.submit(self.data(kind="correction", parent=original.pk), self.maker)
        with self.assertRaises(APIException):
            ledger.approve(obj.pk, self.maker)
        with self.assertRaises(APIException):
            ledger.approve(obj.pk, AnonymousUser())
        with self.assertRaises(APIException):
            ledger.post(obj.pk, self.maker, voucher_checked=True)
        ledger.approve(obj.pk, self.reviewer)
        ledger.cancel(obj.pk, self.maker, "凭证修订，需要重审")
        revision, _ = ledger.submit(self.data(kind="correction", parent=original.pk, replaces=obj.pk), self.maker)
        self.assertEqual(revision.status, "pending")
        with self.assertRaises(APIException):
            ledger.post(revision.pk, self.maker, voucher_checked=True)

    def test_file_digest_recomputed_not_claimed_and_private_direct_url(self):
        obj, _ = ledger.submit(self.data(), self.maker)
        with self.proof.file.open("wb") as target:
            target.write(b"%PDF-tampered")
        with self.assertRaises(APIException):
            ledger.post(obj.pk, self.maker, voucher_checked=True)
        self.assertEqual(FinanceFact.objects.count(), 0)
        client = APIClient()
        response = client.get("/api/media/" + self.proof.file.name)
        self.assertNotEqual(response.status_code, 200)
        with self.assertRaises(APIException):
            ledger.upload(SimpleUploadedFile("unsafe.html", b"<html>active</html>"), self.maker)

    def test_audit_failure_rolls_back_facts_and_request_status(self):
        obj, _ = ledger.submit(self.data(), self.maker)
        with patch("crm.services.finance_closeout.audit", side_effect=RuntimeError("synthetic audit failure")):
            with self.assertRaises(RuntimeError):
                ledger.post(obj.pk, self.maker, voucher_checked=True)
        obj.refresh_from_db()
        self.assertEqual(obj.status, "pending")
        self.assertFalse(FinanceFact.objects.exists())

    def test_scope_denial_does_not_reveal_or_write(self):
        with patch("crm.services.finance_closeout.effective_data_scope", return_value="own"):
            with self.assertRaises(APIException):
                ledger.submit(self.data(), self.maker)
        self.assertFalse(FinanceInstruction.objects.exists())

    def test_malformed_json_commands_are_rejected_without_partial_writes(self):
        client = APIClient()
        client.force_authenticate(self.maker)
        self.assertEqual(client.post("/api/finance-ledger/instructions/", [], format="json").status_code, 400)
        for field in ("kind", "nature", "direction", "truth"):
            response = client.post("/api/finance-ledger/instructions/", self.data(**{field: {"invalid": True}}), format="json")
            self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(FinanceInstruction.objects.exists())
        self.assertFalse(FinanceFact.objects.exists())

    @override_settings(DEVELOPMENT_SUPERADMIN=False)
    def test_unauthenticated_api_and_voucher_download_are_denied(self):
        client = APIClient()
        self.assertIn(client.get("/api/finance-ledger/").status_code, (401, 403))
        self.assertIn(client.get(f"/api/finance-ledger/voucher-download/?id={self.proof.pk}").status_code, (401, 403))
        self.assertIn(client.post("/api/finance-ledger/instructions/", self.data(), format="json").status_code, (401, 403))
        self.assertFalse(FinanceInstruction.objects.exists())

    def test_account_verification_and_legacy_mapping_do_not_guess(self):
        unknown = ledger.create_account({"code": "SYNTH-UNKNOWN", "name": "合成自有银行", "account_type": "bank"}, self.maker)
        self.assertEqual(unknown.ownership, "unverified")
        with self.assertRaises(APIException):
            ledger.submit(self.data(account=unknown.pk), self.maker)
        ledger.verify_account({"account": unknown.pk, "ownership": "own", "reason": "合成开户资料逐项核实"}, self.reviewer)
        self.fact(account=unknown.pk)
        with self.assertRaises(APIException):
            ledger.verify_account({"account": unknown.pk, "ownership": "external", "reason": "不得覆盖旧归属"}, self.reviewer)
        with self.assertRaises(APIException):
            ledger.map_account({"account": self.second.pk, "legacy_code": "SYNTH-CNY", "reason": "错误银行转现金映射"}, self.maker)

    def test_history_and_migration_reversal_are_protected(self):
        from importlib import import_module
        from django.apps import apps
        from django.core.exceptions import ValidationError
        from django.db import connection
        from types import SimpleNamespace
        fact = self.fact()
        with self.assertRaises(ValidationError):
            FinanceFact.objects.filter(pk=fact.pk).update(amount="1.00")
        with self.assertRaises(ValidationError):
            fact.delete()
        for module, function in (("0098_finance_accounts", "preserve_accounts"), ("0099_finance_closeout_workflows", "preserve_finance_history")):
            with self.assertRaises(RuntimeError):
                getattr(import_module("crm.migrations." + module), function)(apps, SimpleNamespace(connection=connection))

    def test_order_refund_allocations_cannot_exceed_approved_shares(self):
        from crm.models import Customer, Order
        customer = Customer.objects.create(code="SYNTH-REF-C", name="合成退款客户")
        order = Order.objects.create(order_no="SYNTH-REF-SO", customer=customer, order_date=date(2026, 1, 1))
        receipt = self.fact()
        approval, _ = ledger.submit(self.data(kind="refund_approval", parent=receipt.pk, direction="expense", amount="150.00", excess_reason="合成批准", allocations=[{"order": order.pk, "amount": "50.00"}]), self.maker)
        ledger.approve(approval.pk, self.reviewer)
        with self.assertRaises(APIException):
            self.fact(kind="refund_payment", approval=approval.pk, direction="expense", amount="60.00", allocations=[{"order": order.pk, "amount": "60.00"}])
        self.assertEqual(FinanceFact.objects.count(), 1)

    @override_settings(RMB_CASH_ACCOUNT_IDS=("SYNTH_FX", "SYNTH_CNY"))
    def test_legacy_bank_return_preserves_original_and_does_not_release_sources(self):
        from crm.tests.test_cash_events import CashFixture, payload
        from crm.services import cash_events
        from crm.models import RmbCashEvent
        CashFixture.setup_cash(self)
        self.proof = ledger.upload(SimpleUploadedFile("synthetic-legacy-correction.pdf", b"%PDF-1.4\nSynthetic legacy correction proof\n%%EOF"), self.maker)
        original, _ = cash_events.register_event(payload([self.receipt], key="SYNTH-LEGACY-BANK"), self.maker)
        cash_events.confirm_event(original.pk, self.maker, voucher_checked=True)
        before = RmbCashEvent.objects.filter(pk=original.pk).values().get()
        ledger.map_account({"account": self.account.pk, "legacy_code": "SYNTH_CNY", "reason": "合成银行开户映射凭证"}, self.maker)
        returned = self.fact(kind="bank_return", legacy_parent=original.pk, direction="expense", amount="100.00", actual_date="2026-10-19")
        self.assertEqual(returned.legacy_parent_id, original.pk)
        self.assertEqual(before, RmbCashEvent.objects.filter(pk=original.pk).values().get())
        self.assertEqual(cash_events.available(self.receipt), Decimal("0"))
        with self.assertRaises(APIException):
            self.fact(kind="bank_return", legacy_parent=original.pk, direction="expense", amount="605.01", actual_date="2026-10-19")

    def test_separate_refund_approvals_still_identify_cumulative_excess(self):
        receipt = self.fact()
        payments = []
        for i in range(2):
            approval, _ = ledger.submit(self.data(kind="refund_approval", amount="80.00", direction="expense", parent=receipt.pk, excess_reason="合成独立批准依据"), self.maker)
            ledger.approve(approval.pk, self.reviewer)
            payments.append(self.fact(kind="refund_payment", amount="80.00", direction="expense", approval=approval.pk))
        self.assertEqual([p.excess_amount for p in payments], [Decimal("0"), Decimal("60.00")])

    def test_upload_limit_and_audit_failure_do_not_leave_private_files(self):
        client = APIClient()
        client.force_authenticate(self.maker)
        before = sorted(Path(self.media.name).rglob("*"))
        response = client.post("/api/finance-ledger/vouchers/", {"file": SimpleUploadedFile("large.pdf", b"%PDF-" + b"x" * (10 * 1024 * 1024))}, format="multipart")
        self.assertEqual(response.status_code, 413)
        self.assertEqual(before, sorted(Path(self.media.name).rglob("*")))
        for handler in response.wsgi_request.upload_handlers[1:]:
            self.assertFalse(getattr(handler, "file", None))
        with patch("crm.services.finance_closeout.audit", side_effect=RuntimeError("synthetic audit failure")):
            with self.assertRaises(RuntimeError):
                ledger.upload(SimpleUploadedFile("new.pdf", b"%PDF-synthetic"), self.maker)
        self.assertEqual(before, sorted(Path(self.media.name).rglob("*")))

    def test_failure_requires_confirmed_no_debit_and_retry_needs_review(self):
        obj, _ = ledger.submit(self.data(kind="correction", parent=self.fact().pk), self.maker)
        ledger.approve(obj.pk, self.reviewer)
        with self.assertRaises(APIException):
            ledger.fail(obj.pk, self.maker, "结果未知", False)
        ledger.fail(obj.pk, self.maker, "合成银行拒绝，已核实未扣款", True)
        self.assertEqual(FinanceFact.objects.count(), 1)
        with self.assertRaises(APIException):
            ledger.post(obj.pk, self.maker, voucher_checked=True)
        retry, _ = ledger.submit(self.data(kind="correction", parent=FinanceFact.objects.first().pk, replaces=obj.pk), self.maker)
        self.assertEqual(retry.status, "pending")

    @override_settings(RMB_CASH_ACCOUNT_IDS=("SYNTH_CNY", "SYNTH_OTHER"))
    def test_existing_bank_transfer_is_matched_without_copying_bank_facts(self):
        from crm.models import RmbCashEvent
        from crm.services import cash_events
        from crm.services.finance import record_transaction
        from crm.tests.test_cash_events import payload
        other = ledger.create_account({"code": "SYNTH-OTHER-BANK", "name": "合成第二银行", "account_type": "bank", "ownership": "own", "ownership_reason": "合成开户核实"}, self.maker)
        events = []
        for direction, code, day in (("expense", "SYNTH_OTHER", "2026-01-03"), ("income", "SYNTH_CNY", "2026-01-04")):
            source = record_transaction({"transaction_no": "SYNTH-OLD-" + direction, "kind": "other_expense" if direction == "expense" else "other_income", "direction": direction, "amount": "705.00", "currency": "CNY", "exchange_rate": "1", "category": "合成旧银行本金"})
            event, _ = cash_events.register_event(payload([source], key="SYNTH-OLD-BANK-" + direction, kind="cny_direct", currency="CNY", direction=direction, bank_date=day, source_account=code, rmb_account=code, bank_net_amount="705.00", fee_mode="none", fee_amount="0", quoted_rate=None), self.maker)
            cash_events.confirm_event(event.pk, self.maker, voucher_checked=True)
            events.append(event)
        ledger.map_account({"account": other.pk, "legacy_code": "SYNTH_OTHER", "reason": "合成旧银行映射"}, self.maker)
        ledger.map_account({"account": self.account.pk, "legacy_code": "SYNTH_CNY", "reason": "合成旧银行映射"}, self.maker)
        before = list(RmbCashEvent.objects.order_by("pk").values())
        match = ledger.match_historical_transfer({"outgoing": f"legacy:{events[0].pk}", "incoming": f"legacy:{events[1].pk}", "outgoing_voucher": self.proof.pk, "incoming_voucher": self.proof.pk, "reason": "合成跨日两端本金及文件核实"}, self.maker)
        self.assertIsNotNone(match.pk)
        self.assertFalse(FinanceFact.objects.exists())
        self.assertEqual(before, list(RmbCashEvent.objects.order_by("pk").values()))
        client = APIClient()
        client.force_authenticate(self.maker)
        result = client.get("/api/actual-rmb-cash/", {"date_from": "2026-01-01", "date_to": "2026-01-31"})
        self.assertEqual(result.status_code, 200, result.data)
        self.assertEqual(result.data["totals"]["count"], 0)
        self.assertEqual(Decimal(result.data["totals"]["net"]), Decimal("0"))

    def test_actual_api_report_csv_and_drilldown_share_same_amount(self):
        self.fact(amount="123.45")
        client = APIClient()
        client.force_authenticate(self.maker)
        period = {"date_from": "2026-01-01", "date_to": "2026-01-31"}
        actual = client.get("/api/actual-rmb-cash/", period)
        self.assertEqual(actual.status_code, 200, actual.data)
        self.assertEqual(Decimal(actual.data["totals"]["inflow"]), Decimal("123.45"))
        report = client.get("/api/reports/data/", {**period, "source": "actual_cash", "group_by": "direction"})
        self.assertEqual(report.status_code, 200, report.data)
        self.assertEqual(Decimal(str(report.data["totals"]["amount"])), Decimal("123.45"))
        csv = client.get("/api/finance-ledger/facts/", {**period, "export": "csv"})
        self.assertEqual(csv.status_code, 200)
        self.assertIn("123.45", csv.content.decode("utf-8-sig"))
        detail = client.get("/api/finance-ledger/facts/", period)
        self.assertEqual(detail.data["facts"][0]["amount"], "123.45")
