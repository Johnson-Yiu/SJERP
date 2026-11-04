"""Real PostgreSQL HTTP-view competition using independent connections."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import unittest

from django.db import close_old_connections, connection, connections
from django.test import TransactionTestCase
from rest_framework.test import APIClient

from crm.models import FinanceFact, FinanceInstruction, FinanceReview, FinanceTransferMatch, OperationLog
from crm.tests.test_finance_adversarial_review import AdversarialFixture, BASE, PERIOD


@unittest.skipUnless(connection.vendor == "postgresql", "Real PostgreSQL 17 lock semantics required")
class FinanceAdversarialConcurrencyTests(AdversarialFixture, TransactionTestCase):
    def setUp(self):
        self.setup_adversarial()

    def compete(self, calls):
        barrier = Barrier(len(calls))

        def worker(call):
            close_old_connections()
            try:
                with connections["default"].cursor() as cursor:
                    cursor.execute("SELECT pg_backend_pid()")
                    pid = cursor.fetchone()[0]
                client = APIClient()
                client.force_authenticate(self.maker)
                barrier.wait(timeout=20)
                action, body = call
                r = client.post(BASE + action + "/", body, format="json")
                return {"pid": pid, "action": action, "input": body, "status": r.status_code, "body": getattr(r, "data", None)}
            finally:
                connections["default"].close()

        with ThreadPoolExecutor(max_workers=len(calls)) as pool:
            results = list(pool.map(worker, calls))
        self.assertEqual(len({r["pid"] for r in results}), len(calls))
        self.records.extend(results)
        return results

    def test_two_partial_bank_returns_cannot_exceed_remaining_or_duplicate_audit(self):
        parent = self.fact(amount="100.00")
        ids = [self.instruction(kind="bank_return", parent=parent["id"], direction="expense", amount="70.00") for _ in range(2)]
        before = OperationLog.objects.count()
        r = self.compete([("post", {"id": i, "voucher_checked": True}) for i in ids])
        self.assertEqual(sorted(x["status"] for x in r), [200, 400])
        self.assertEqual(list(FinanceFact.objects.filter(kind="bank_return").values_list("amount", flat=True)), [70])
        self.assertEqual(OperationLog.objects.count(), before + 1)
        self.assertEqual(FinanceInstruction.objects.filter(pk__in=ids, status="posted").count(), 1)
        self.assert_surfaces("100", "70")

    def test_transfer_competing_counterparts_do_not_reuse_a_principal(self):
        third = self.api("accounts", {"code": "ADV-THIRD", "name": "合成第三银行", "account_type": "bank", "ownership": "own", "ownership_reason": "合成核实"}, 201)["id"]
        out = self.fact(direction="expense", amount="47.00", nature="internal_principal")
        incoming = [self.fact(account=a, amount="47.00", nature="internal_principal", actual_date="2026-04-05") for a in (self.cash, third)]
        before = OperationLog.objects.count()
        r = self.compete([("transfers", {"outgoing": out["id"], "incoming": f["id"], "reason": "合成竞争本金匹配"}) for f in incoming])
        self.assertEqual(sorted(x["status"] for x in r), [201, 409])
        self.assertEqual(FinanceTransferMatch.objects.count(), 1)
        self.assertEqual(OperationLog.objects.count(), before + 1)
        self.assert_surfaces("47", "0")

    def test_approval_cancel_vs_actual_payment_keeps_any_real_debit(self):
        receipt = self.fact()
        approval = self.instruction(approve=True, kind="refund_approval", parent=receipt["id"], amount="91.00", excess_reason="合成批准")
        pay = self.instruction(approve=True, kind="refund_payment", approval=approval, direction="expense", amount="91.00")
        before = OperationLog.objects.count()
        r = self.compete([("cancel", {"id": approval, "reason": "合成停止剩余批准"}), ("post", {"id": pay, "voucher_checked": True})])
        self.assertEqual(r[0]["status"], 200)
        self.assertIn(r[1]["status"], (200, 400))
        paid = r[1]["status"] == 200
        self.assertEqual(FinanceFact.objects.filter(kind="refund_payment").count(), int(paid))
        self.assertEqual(FinanceInstruction.objects.get(pk=approval).status, "cancelled")
        self.assertEqual(FinanceInstruction.objects.get(pk=pay).status, "posted" if paid else "approved")
        self.assertEqual(OperationLog.objects.count(), before + 1 + int(paid))
        self.assert_surfaces("113.27", "91" if paid else "0")

    def test_fail_vs_post_cannot_leave_failed_instruction_with_business_fact(self):
        ident = self.instruction(direction="expense", amount="31.00")
        before = OperationLog.objects.count()
        r = self.compete([("fail", {"id": ident, "reason": "合成核实未扣款", "no_debit_confirmed": True}), ("post", {"id": ident, "voucher_checked": True})])
        self.assertEqual(sorted(x["status"] for x in r), [200, 400])
        current = FinanceInstruction.objects.get(pk=ident)
        self.assertEqual(FinanceFact.objects.filter(instruction_id=ident).count(), int(current.status == "posted"))
        self.assertEqual(OperationLog.objects.count(), before + 1)

    def test_reconciliation_vs_late_fact_never_silently_keeps_stale_completed(self):
        self.fact(kind="opening", amount="100.00", actual_date="2026-04-01")
        pending = self.instruction(amount="1.00")
        before = OperationLog.objects.count()
        r = self.compete([("reviews", {"account": self.bank, "date_from": "2026-04-01", "date_to": "2026-04-30", "voucher": self.proof, "statement_balance": "100.00", "completed": True, "reason": "合成核对竞争"}), ("post", {"id": pending, "voucher_checked": True})])
        self.assertEqual(r[1]["status"], 200)
        self.assertIn(r[0]["status"], (201, 400))
        if r[0]["status"] == 201:
            self.assertEqual(self.state()["reviews"][0]["status"], "needs_review")
        self.assertEqual(self.balance(), 101)
        self.assertEqual(OperationLog.objects.count(), before + 1 + int(r[0]["status"] == 201))

    def test_correction_vs_transfer_preserves_one_consistent_effective_history(self):
        out = self.fact(direction="expense", amount="52.00", nature="internal_principal")
        inc = self.fact(account=self.cash, amount="52.00", nature="internal_principal", actual_date="2026-04-05")
        correction = self.instruction(approve=True, kind="correction", parent=out["id"], direction="expense", amount="51.00")
        before = OperationLog.objects.count()
        r = self.compete([("transfers", {"outgoing": out["id"], "incoming": inc["id"], "reason": "合成本金竞争"}), ("post", {"id": correction, "voucher_checked": True})])
        self.assertEqual(sum(x["status"] in (200, 201) for x in r), 1)
        self.assertEqual(sum(x["status"] == 400 for x in r), 1)
        self.assertEqual(OperationLog.objects.count(), before + 1)
        matched = FinanceTransferMatch.objects.exists()
        self.assertEqual(FinanceFact.objects.filter(kind="correction").exists(), not matched)
        self.assert_surfaces("0" if matched else "52", "0" if matched else "51")

    def test_two_independent_reconciliations_do_not_create_cash_or_overwrite_history(self):
        self.fact(kind="opening", amount="0.00", actual_date="2026-04-01")
        p = {"account": self.bank, "date_from": "2026-04-01", "date_to": "2026-04-30", "voucher": self.proof, "statement_balance": "0.00", "completed": True, "reason": "合成独立核对"}
        before = FinanceFact.objects.count(), OperationLog.objects.count()
        r = self.compete([("reviews", p), ("reviews", p)])
        self.assertEqual([x["status"] for x in r], [201, 201])
        self.assertNotEqual(r[0]["body"]["id"], r[1]["body"]["id"])
        self.assertEqual(FinanceReview.objects.count(), 2)
        self.assertEqual(FinanceFact.objects.count(), before[0])
        self.assertEqual(OperationLog.objects.count(), before[1] + 2)
