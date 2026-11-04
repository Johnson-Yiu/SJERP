"""Independent HTTP-contract counterexamples; no production service modifications."""
import csv
import hashlib
import io
import json
import os
import tempfile
import uuid
from decimal import Decimal as D
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from crm.models import FinanceFact, FinanceInstruction, OperationLog, Order

BASE = "/api/finance-ledger/"
PERIOD = {"date_from": "2026-04-01", "date_to": "2026-06-30"}


class AdversarialFixture:
    def setup_adversarial(self):
        self.temp = tempfile.TemporaryDirectory(prefix="finance-adversarial-media-")
        self.addCleanup(self.temp.cleanup)
        context = override_settings(MEDIA_ROOT=self.temp.name)
        context.enable()
        self.addCleanup(context.disable)
        self.records = []
        self.addCleanup(self.save_evidence)
        self.maker = get_user_model().objects.create_superuser("adversarial-maker", "", None)
        self.reviewer = get_user_model().objects.create_superuser("adversarial-reviewer", "", None)
        self.client = APIClient()
        self.client.force_authenticate(self.maker)
        self.bank = self.api("accounts", {"code": "ADV-BANK", "name": "合成反例银行", "account_type": "bank", "ownership": "own", "ownership_reason": "合成核实"}, 201)["id"]
        self.cash = self.api("accounts", {"code": "ADV-CASH", "name": "合成反例现金", "account_type": "cash", "ownership": "own", "ownership_reason": "合成核实"}, 201)["id"]
        self.proof_bytes = b"%PDF-1.4\n% Synthetic counterexample evidence only\n%%EOF\n"
        r = self.client.post(BASE + "vouchers/", {"file": SimpleUploadedFile("synthetic-adversarial.pdf", self.proof_bytes)}, format="multipart")
        self.assertEqual(r.status_code, 201, r.data)
        self.proof = r.data["id"]

    def save_evidence(self):
        destination = os.environ.get("FINANCE_ADVERSARIAL_EVIDENCE")
        if destination:
            root = Path(destination)
            root.mkdir(parents=True, exist_ok=True)
            (root.resolve() / (hashlib.sha256(self.id().encode()).hexdigest()[:16] + ".json")).write_text(json.dumps({"test": self.id(), "requests": self.records}, ensure_ascii=False, indent=2, default=str), encoding="utf-8", newline="\n")

    def api(self, action, payload=None, status=200, user=None, method="post"):
        client = APIClient()
        client.force_authenticate(user or self.maker)
        r = getattr(client, method)(BASE + action + "/", payload or {}, format="json")
        data = getattr(r, "data", None)
        self.records.append({"method": method, "path": BASE + action + "/", "input": payload, "status": r.status_code, "body": data})
        self.assertEqual(r.status_code, status, data)
        return data

    def data(self, **changes):
        key = "ADV-" + uuid.uuid4().hex
        p = {"request_key": key, "source_system": "SYNTH-ADVERSARIAL", "source_key": key,
             "kind": "cash", "account": self.bank, "voucher": self.proof,
             "actual_date": "2026-04-03", "direction": "income", "amount": "113.27",
             "nature": "unclassified", "truth": "verified", "reason": "合成反例凭证已核实"}
        p.update(changes)
        return p

    def instruction(self, approve=False, **changes):
        i = self.api("instructions", self.data(**changes), 201)
        if approve:
            self.api("approve", {"id": i["id"]}, user=self.reviewer)
        return i["id"]

    def fact(self, **changes):
        approved = changes.get("kind") in {"opening", "correction", "refund_approval", "refund_payment"}
        i = self.instruction(approve=approved, **changes)
        return self.api("post", {"id": i, "voucher_checked": True})

    def facts(self, **period):
        return self.api("facts", period or PERIOD, method="get")

    def state(self, end="2026-06-30"):
        r = self.client.get(BASE, {"date_to": end})
        self.assertEqual(r.status_code, 200, r.data)
        self.records.append({"method": "get", "path": BASE, "input": end, "status": r.status_code, "body": r.data})
        return r.data

    def balance(self, account=None, end="2026-06-30"):
        return D(next(a["balance"] for a in self.state(end)["accounts"] if a["id"] == (account or self.bank)))

    def review(self, amount, **changes):
        return self.api("reviews", {"account": self.bank, "date_from": "2026-04-01", "date_to": "2026-04-30", "voucher": self.proof, "statement_balance": amount, "completed": True, "reason": "合成对账单核对", **changes}, 201)["id"]

    def actual(self, period=PERIOD):
        r = self.client.get("/api/actual-rmb-cash/", period)
        self.assertEqual(r.status_code, 200, r.data)
        self.records.append({"path": "/api/actual-rmb-cash/", "input": period, "status": r.status_code, "body": r.data})
        return r.data

    def assert_surfaces(self, inflow, outflow, period=PERIOD):
        actual = self.actual(period)
        totals = self.facts(**period)["totals"]
        for name, expected in (("inflow", inflow), ("outflow", outflow)):
            self.assertEqual(D(actual["totals"][name]), D(expected))
            self.assertEqual(D(totals[name]), D(expected))
        r = self.client.get(BASE + "facts/", {**period, "export": "csv"})
        self.assertEqual(r.status_code, 200)
        rows = list(csv.DictReader(io.StringIO(r.content.decode("utf-8-sig"))))
        self.records.append({"path": BASE + "facts/?export=csv", "csv": r.content.decode("utf-8-sig")})
        for direction, expected in (("income", inflow), ("expense", outflow)):
            self.assertEqual(sum((D(row["amount"]) for row in rows if row["company_flow_included"] == "True" and row["direction"] == direction), D(0)), D(expected))
        report = self.client.get("/api/reports/data/", {**period, "source": "actual_cash", "group_by": "direction"})
        self.assertEqual(report.status_code, 200, report.data)
        # Existing report contract uses signed net, not gross sum (reporting.py
        # actual_cash rows negate expenses). Gross API/CSV checks stay above.
        self.assertEqual(D(str(report.data["totals"]["amount"])), D(inflow) - D(outflow))
        self.records.append({"path": "/api/reports/data/", "body": report.data})
        for row in self.facts(**period)["facts"]:
            detail = self.api("fact_detail", {"id": row["id"]}, method="get")
            self.assertEqual(detail["company_flow_included"], row["company_flow_included"])
            self.assertEqual(detail["amount"], row["amount"])


class FinanceAdversarialReviewTests(AdversarialFixture, TestCase):
    def setUp(self):
        self.setup_adversarial()

    def test_multi_period_amount_direction_date_zero_and_multilevel_corrections(self):
        self.fact(kind="opening", actual_date="2026-04-01", amount="1000.00")
        first = self.fact()
        original = FinanceFact.objects.filter(pk=first["id"]).values().get()
        second = self.fact(kind="correction", parent=first["id"], amount="81.09", direction="expense", actual_date="2026-05-02")
        self.assert_surfaces("0", "0", {"date_from": "2026-04-01", "date_to": "2026-04-30"})
        self.assert_surfaces("0", "81.09", {"date_from": "2026-05-01", "date_to": "2026-05-31"})
        self.assertEqual(self.balance(end="2026-04-30"), D(1000))
        self.assertEqual(self.balance(end="2026-05-31"), D("918.91"))
        third = self.fact(kind="correction", parent=second["id"], amount="0.00", actual_date="2026-06-03")
        self.assert_surfaces("0", "0")
        self.assertEqual(self.balance(), D(1000))
        fourth = self.fact(kind="correction", parent=third["id"], amount="72.08", actual_date="2026-06-04")
        self.assert_surfaces("72.08", "0")
        self.assertEqual(self.balance(), D("1072.08"))
        self.assertEqual(FinanceFact.objects.filter(pk=first["id"]).values().get(), original)
        self.assertEqual(FinanceFact.objects.count(), 5)
        self.assertEqual(fourth["parent"], third["id"])

    def test_cross_day_transfer_fees_repeat_and_correction_after_match(self):
        self.fact(kind="opening", amount="600.00", actual_date="2026-04-01")
        self.fact(kind="opening", account=self.cash, amount="100.00", actual_date="2026-04-01")
        out = self.fact(direction="expense", amount="79.00", nature="internal_principal")
        inc = self.fact(account=self.cash, amount="79.00", nature="internal_principal", actual_date="2026-04-05")
        self.fact(direction="expense", amount="1.23", nature="bank_fee", actual_date="2026-04-04")
        p = {"outgoing": out["id"], "incoming": inc["id"], "reason": "合成跨日人工核实"}
        match = self.api("transfers", p, 201)
        count = OperationLog.objects.count()
        self.assertEqual(self.api("transfers", p, 201), match)
        self.assertEqual(OperationLog.objects.count(), count)
        correction = self.instruction(approve=True, kind="correction", parent=out["id"], direction="expense", amount="78.00")
        self.api("post", {"id": correction, "voucher_checked": True}, 400)
        self.assert_surfaces("0", "1.23")
        self.assertEqual(self.balance(), D("519.77"))
        self.assertEqual(self.balance(self.cash), D("179.00"))

    def test_cross_approval_excess_and_partial_refund_returns(self):
        receipt = self.fact(amount="93.00")
        a = self.instruction(approve=True, kind="refund_approval", parent=receipt["id"], amount="80.00", excess_reason="合成批准依据")
        b = self.instruction(approve=True, kind="refund_approval", parent=receipt["id"], amount="60.00", excess_reason="合成补充批准")
        first = self.fact(kind="refund_payment", approval=a, direction="expense", amount="80.00")
        second = self.fact(kind="refund_payment", approval=b, direction="expense", amount="60.00")
        self.assertEqual(D(first["refund_excess_amount"]), D(0))
        self.assertEqual(D(second["refund_excess_amount"]), D(47))
        self.fact(kind="refund_return", parent=second["id"], amount="21.00", actual_date="2026-04-09")
        self.fact(kind="refund_return", parent=second["id"], amount="39.00", actual_date="2026-04-10")
        bad = self.instruction(kind="refund_return", parent=second["id"], amount="0.01")
        self.api("post", {"id": bad, "voucher_checked": True}, 400)
        self.assert_surfaces("153.00", "140.00")

    def test_per_order_cumulative_approval_is_not_reset_per_payment(self):
        from crm.models import Customer
        customer = Customer.objects.create(name="合成反例客户")
        order = Order.objects.create(order_no="ADV-SO", customer=customer, order_date="2026-04-01")
        receipt = self.fact(amount="93.00")
        approval = self.instruction(approve=True, kind="refund_approval", parent=receipt["id"], amount="80.00", allocations=[{"order": order.pk, "amount": "50.00"}], excess_reason="合成批准")
        self.fact(kind="refund_payment", approval=approval, direction="expense", amount="40.00", allocations=[{"order": order.pk, "amount": "40.00"}])
        candidate = self.instruction(approve=True, kind="refund_payment", approval=approval, direction="expense", amount="20.00", allocations=[{"order": order.pk, "amount": "11.00"}])
        before = FinanceFact.objects.count(), OperationLog.objects.count()
        self.api("post", {"id": candidate, "voucher_checked": True}, 400)
        self.assertEqual((FinanceFact.objects.count(), OperationLog.objects.count()), before)
        self.fact(kind="refund_payment", approval=approval, direction="expense", amount="20.00", allocations=[{"order": order.pk, "amount": "10.00"}])

    def test_unknown_debit_stable_retry_failure_revision_and_approval_cancel(self):
        receipt = self.fact()
        approval = self.instruction(approve=True, kind="refund_approval", parent=receipt["id"], amount="50.00", excess_reason="合成批准")
        data = self.data(kind="refund_payment", approval=approval, direction="expense", amount="41.00")
        pending = self.api("instructions", data, 201)["id"]
        self.api("approve", {"id": pending}, user=self.reviewer)
        self.api("fail", {"id": pending, "reason": "扣款未知", "no_debit_confirmed": False}, 400)
        first = self.api("post", {"id": pending, "voucher_checked": True})
        self.assertEqual(self.api("instructions", data)["id"], pending)
        before = FinanceFact.objects.count(), OperationLog.objects.count()
        self.assertEqual(self.api("post", {"id": pending, "voucher_checked": True})["id"], first["id"])
        self.assertEqual((FinanceFact.objects.count(), OperationLog.objects.count()), before)
        self.api("cancel", {"id": approval, "reason": "停止剩余批准额度"})
        self.assert_surfaces("113.27", "41.00")
        failed = self.instruction(kind="cash", direction="expense", amount="7.00")
        self.api("fail", {"id": failed, "reason": "已核实未扣款", "no_debit_confirmed": True})
        revised = self.instruction(replaces=failed, kind="correction", parent=receipt["id"], amount="112.00")
        self.api("post", {"id": revised, "voucher_checked": True}, 400)

    def test_orphan_verified_real_refund_can_be_recorded_without_inventing_original(self):
        approval = self.instruction(approve=True, kind="refund_approval", amount="29.91", excess_reason="原收款待查，有合成退款依据")
        payment = self.instruction(approve=True, kind="refund_payment", approval=approval, direction="expense", amount="29.91")
        self.api("post", {"id": payment, "voucher_checked": True}, 400)
        # The supported independent actual-fact entry records the bank debit;
        # no guessed source/approval link and no second order refund is created.
        fact = self.fact(direction="expense", amount="29.91", nature="commercial_refund")
        self.assertIsNone(fact["parent"])
        self.assert_surfaces("0", "29.91")

    def test_positive_negative_zero_opening_and_same_day_boundary(self):
        for index, (direction, amount, expected) in enumerate((("income", "20.00", "23.71"), ("expense", "20.00", "-16.29"), ("income", "0.00", "3.71"))):
            own = self.api("accounts", {"code": f"ADV-{index}", "name": "合成基准", "account_type": "bank", "ownership": "own", "ownership_reason": "合成核实"}, 201)["id"]
            self.fact(kind="opening", account=own, direction=direction, amount=amount, actual_date="2026-04-03")
            self.fact(account=own, amount="3.71")
            self.assertEqual(self.balance(own), D(expected))
            old = self.instruction(account=own, amount="1.00", actual_date="2026-04-02")
            self.api("post", {"id": old, "voucher_checked": True}, 400)
        self.assert_surfaces("11.13", "0")

    def test_reconciliation_late_correction_cross_period_and_classification(self):
        self.fact(kind="opening", amount="100.00", actual_date="2026-04-01")
        original = self.fact(amount="17.00")
        review = self.review("117.00")
        self.fact(kind="correction", parent=original["id"], amount="11.00", actual_date="2026-05-02")
        row = next(r for r in self.state()["reviews"] if r["id"] == review)
        self.assertEqual(row["status"], "needs_review")
        self.assertEqual(self.balance(end="2026-04-30"), D(100))
        again = self.review("100.00")
        later = self.fact(amount="0.09", actual_date="2026-04-09")
        self.assertEqual(next(r for r in self.state()["reviews"] if r["id"] == again)["status"], "needs_review")
        third = self.review("100.09")
        self.api("classifications", {"fact": later["id"], "nature": "interest", "reason": "合成利息核实"}, 201)
        self.assertEqual(next(r for r in self.state()["reviews"] if r["id"] == third)["status"], "needs_review")

    def test_all_kinds_reject_unverified_and_simulated_before_post(self):
        for truth in ("simulated", "needs_verification"):
            for kind in ("cash", "opening", "correction", "refund_approval", "refund_payment", "bank_return", "refund_return"):
                with self.subTest(truth=truth, kind=kind):
                    data = self.data(kind=kind, truth=truth, excess_reason="合成依据")
                    self.api("preview", data)
                    ident = self.api("instructions", data, 201)["id"]
                    self.api("approve", {"id": ident}, 400, user=self.reviewer)
                    self.api("post", {"id": ident, "voucher_checked": True}, 400)
        self.assertFalse(FinanceFact.objects.exists())
        self.assert_surfaces("0", "0")

    def test_approved_payload_has_no_supported_edit_or_delete_path(self):
        ident = self.instruction(approve=True, kind="opening", amount="10.00", actual_date="2026-04-01")
        self.api("approve", {"id": self.instruction(kind="opening", amount="11.00")}, 400)
        original = FinanceInstruction.objects.get(pk=ident)
        for method in ("patch", "put", "delete"):
            r = getattr(self.client, method)(BASE + f"{ident}/", {"payload": {"amount": "999"}}, format="json")
            self.assertIn(r.status_code, (404, 405))
        original.refresh_from_db()
        self.assertEqual(original.payload["amount"], "10.00")
        self.api("post", {"id": ident, "voucher_checked": True})
        self.api("cancel", {"id": ident, "reason": "不能取消事实"}, 400)

    def test_trusted_storage_corruption_of_approved_payload_is_detected_on_post(self):
        original = self.fact(amount="19.00")
        ident = self.instruction(approve=True, kind="correction", parent=original["id"], amount="18.00")
        obj = FinanceInstruction.objects.get(pk=ident)
        corrupted = {**obj.payload, "amount": "999.00"}
        # Explicit trusted-ORM fault injection, not an exposed update API.
        FinanceInstruction.objects.filter(pk=ident).update(payload=corrupted)
        before = FinanceFact.objects.count(), OperationLog.objects.count()
        response = self.api("post", {"id": ident, "voucher_checked": True}, 400)
        self.assertIn("指令内容完整性异常", str(response))
        self.assertEqual((FinanceFact.objects.count(), OperationLog.objects.count()), before)

    def test_file_replacement_deletion_and_size_hash_refuse_without_side_effects(self):
        from crm.models import FinanceVoucher
        path = Path(FinanceVoucher.objects.get(pk=self.proof).file.path)
        for body in (b"changed-size", b"x" * len(self.proof_bytes), None):
            with self.subTest(body=body is None):
                ident = self.instruction()
                if body is None:
                    path.unlink()
                else:
                    path.write_bytes(body)
                before = FinanceFact.objects.count(), OperationLog.objects.count()
                self.api("post", {"id": ident, "voucher_checked": True}, 400)
                self.api("voucher-download", {"id": self.proof}, 400, method="get")
                self.assertEqual((FinanceFact.objects.count(), OperationLog.objects.count()), before)
                path.write_bytes(self.proof_bytes)

    def test_audit_failure_rollback_at_post_transfer_and_review(self):
        from crm.services import finance_closeout as ledger
        ident = self.instruction(approve=True, kind="opening", amount="100.00", actual_date="2026-04-01")
        before = FinanceFact.objects.count(), OperationLog.objects.count()
        with patch.object(ledger, "audit", side_effect=RuntimeError("synthetic audit outage")):
            with self.assertRaisesRegex(RuntimeError, "synthetic audit outage"):
                self.client.post(BASE + "post/", {"id": ident, "voucher_checked": True}, format="json")
        self.assertEqual((FinanceFact.objects.count(), OperationLog.objects.count()), before)
        self.assertEqual(FinanceInstruction.objects.get(pk=ident).status, "approved")
        self.api("post", {"id": ident, "voucher_checked": True})
        from crm.models import FinanceReview, FinanceTransferMatch
        out = self.fact(direction="expense", amount="12.00", nature="internal_principal")
        inc = self.fact(account=self.cash, amount="12.00", nature="internal_principal")
        before = OperationLog.objects.count()
        for action, data, model in (("reviews", {"account": self.bank, "date_from": "2026-04-01", "date_to": "2026-04-30", "voucher": self.proof, "statement_balance": "88.00", "completed": True, "reason": "合成核对"}, FinanceReview), ("transfers", {"outgoing": out["id"], "incoming": inc["id"], "reason": "合成匹配"}, FinanceTransferMatch)):
            with patch.object(ledger, "audit", side_effect=RuntimeError("synthetic audit outage")):
                with self.assertRaises(RuntimeError):
                    self.client.post(BASE + action + "/", data, format="json")
            self.assertFalse(model.objects.exists())
            self.assertEqual(OperationLog.objects.count(), before)

    def test_permission_rejection_covers_list_detail_file_csv_and_writes(self):
        from crm.tests.test_finance_data_scope import RBAC_SETTINGS
        user = get_user_model().objects.create_user("adversarial-no-role")
        fact = self.fact()
        # Only this isolated test changes settings; running development does not.
        with override_settings(**RBAC_SETTINGS):
            client = APIClient()
            client.force_authenticate(user)
            for path in (BASE, BASE + f"fact_detail/?id={fact['id']}", BASE + f"voucher-download/?id={self.proof}", BASE + "facts/?export=csv", "/api/actual-rmb-cash/", "/api/reports/data/?source=actual_cash"):
                r = client.get(path)
                self.assertEqual(r.status_code, 403, (path, r.content))
                self.assertNotIn(b"113.27", r.content)
            self.assertEqual(client.post(BASE + "instructions/", self.data(), format="json").status_code, 403)

    def test_orm_update_is_blocked_but_bulk_insert_is_a_trusted_code_boundary(self):
        from django.core.exceptions import ValidationError
        fact = self.fact()
        with self.assertRaises(ValidationError):
            FinanceFact.objects.filter(pk=fact["id"]).update(amount=D(999))
        pending = self.instruction(truth="simulated")
        self.api("post", {"id": pending, "voucher_checked": True}, 400)
        with transaction.atomic():
            row = FinanceFact.objects.get(pk=fact["id"])
            attrs = {f.attname: getattr(row, f.attname) for f in FinanceFact._meta.concrete_fields if f.name not in {"id", "created_at"}}
            attrs.update(instruction_id=pending, truth="simulated", source_key="ADV-TRUSTED-BULK-PROBE")
            FinanceFact.objects.bulk_create([FinanceFact(**attrs)])
            self.assertTrue(FinanceFact.objects.filter(source_key="ADV-TRUSTED-BULK-PROBE").exists())
            self.records.append({"boundary": "trusted_ORM_only_not_HTTP", "bulk_create_accepts_simulated": True, "rolled_back": True})
            transaction.set_rollback(True)
        self.assertFalse(FinanceFact.objects.filter(source_key="ADV-TRUSTED-BULK-PROBE").exists())
        from django.contrib import admin
        self.assertFalse(admin.site.is_registered(FinanceFact))
        self.assertFalse(admin.site.is_registered(FinanceInstruction))
        # No current supported caller bulk-inserts FinanceFact. Do not label a
        # trusted-code/DB-administrator capability as a public API exploit.
        self.assertEqual(self.api("fact_detail", {"id": fact["id"]}, method="get")["amount"], "113.27")

    def test_mixed_legacy_and_new_cross_day_principal_preserves_legacy_business_rows(self):
        from crm.models import RmbCashEvent, Transaction
        from crm.services.finance import record_transaction
        from crm.tests.test_cash_events import ACCOUNTS, payload
        with override_settings(RMB_CASH_ACCOUNT_IDS=ACCOUNTS):
            self.fact(kind="opening", amount="100.00", actual_date="2026-04-01")
            self.fact(kind="opening", account=self.cash, amount="100.00", actual_date="2026-04-01")
            source = record_transaction({"transaction_no": "ADV-LEGACY-OUT", "kind": "other_expense", "direction": "expense", "amount": "47.00", "currency": "CNY", "exchange_rate": "1", "category": "合成旧银行本金"})
            body = payload([source], key="ADV-OLD", kind="cny_direct", currency="CNY", direction="expense", bank_date="2026-04-03", source_account="SYNTH_CNY", rmb_account="SYNTH_CNY", bank_net_amount="47.00", fee_mode="none", fee_amount="0", quoted_rate=None)
            r = self.client.post("/api/rmb-cash-events/", body, format="json")
            self.assertEqual(r.status_code, 201, r.data)
            ident = r.data["id"]
            self.assertEqual(self.client.post(f"/api/rmb-cash-events/{ident}/confirm/", {"voucher_checked": True}, format="json").status_code, 200)
            self.api("mappings", {"account": self.bank, "legacy_code": "SYNTH_CNY", "reason": "合成开户资料明确匹配"}, 201)
            incoming = self.fact(account=self.cash, nature="internal_principal", amount="47.00", actual_date="2026-04-05")
            before = (list(RmbCashEvent.objects.values()), list(Transaction.objects.values()))
            match = self.api("transfers", {"outgoing": f"legacy:{ident}", "incoming": f"fact:{incoming['id']}", "outgoing_voucher": self.proof, "incoming_voucher": self.proof, "reason": "合成新旧事实两端核实"}, 201)
            self.assertTrue(match["id"])
            self.assert_surfaces("0", "0")
            self.assertEqual(self.balance(), D(53))
            self.assertEqual(self.balance(self.cash), D(147))
            self.assertEqual((list(RmbCashEvent.objects.values()), list(Transaction.objects.values())), before)


from crm.tests import test_finance_data_scope as scope_fixture


class HiddenSourceFixture(AdversarialFixture):
    make_employee = scope_fixture.FinanceDataScopeTests.make_employee

    def setup_hidden(self):
        self.setup_adversarial()
        scope_fixture.FinanceDataScopeTests.setUp(self)
        self.client.force_authenticate(self.maker)

    def hidden_candidate(self):
        from crm.models import RolePermission, Transaction
        from crm.tests.test_cash_events import payload
        p = payload(self.receipts[:2], key="ADV-HIDDEN", currency="CNY", kind="cny_direct", bank_date="2026-04-03", bank_net_amount="20.00", fee_mode="none", fee_amount="0", quoted_rate=None)
        r = self.client.post("/api/rmb-cash-events/", p, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(self.client.post(f"/api/rmb-cash-events/{r.data['id']}/confirm/", {"voucher_checked": True}, format="json").status_code, 200)
        self.api("mappings", {"account": self.bank, "legacy_code": "SYNTH_CNY", "reason": "合成显式账户映射"}, 201)
        RolePermission.objects.filter(role=self.roles["all"], module="orders").update(can_view=False)
        return self.all_user.user, self.data(amount="20.00")


@override_settings(**scope_fixture.RBAC_SETTINGS, RMB_CASH_ACCOUNT_IDS=("SYNTH_FX", "SYNTH_CNY"), PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class FinanceAdversarialHiddenSourceTests(HiddenSourceFixture, TestCase):
    def setUp(self):
        self.setup_hidden()

    def test_hidden_duplicate_service_boundary_below_blocked_role_http_gate(self):
        from crm.models import Transaction
        from crm.services import finance_closeout as ledger
        from rest_framework.exceptions import APIException
        user, data = self.hidden_candidate()
        before = list(Transaction.objects.values()), list(Order.objects.values())
        candidates = ledger.duplicate_candidates(ledger.normalize(data, user), user)
        self.assertEqual(candidates, {"ids": [], "token": "", "restricted": True})
        pending, _ = ledger.submit(data, user)
        with self.assertRaises(APIException) as refused:
            ledger.post(pending.pk, user, voucher_checked=True)
        self.assertEqual(refused.exception.status_code, 409)
        self.records.append({"layer": "service_only_HTTP_authorized_role_blocked_ADV03", "candidates": candidates, "post_status": refused.exception.status_code})
        self.assertFalse(FinanceFact.objects.exists())
        self.assertEqual((list(Transaction.objects.values()), list(Order.objects.values())), before)
