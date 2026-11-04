from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import unittest

from django.db import close_old_connections, connection, connections
from django.test import TransactionTestCase
from rest_framework.exceptions import APIException

from crm.models import FinanceFact, FinanceInstruction, OperationLog
from crm.services import finance_closeout as ledger
from crm.tests.test_finance_closeout import CloseoutFixture


@unittest.skipUnless(connection.vendor == "postgresql", "Real PostgreSQL connections and locks required")
class FinanceCloseoutConcurrencyTests(CloseoutFixture, TransactionTestCase):
    def setUp(self):
        self.setup_ledger()

    def parallel(self, call):
        gate = Barrier(2)

        def worker(_):
            close_old_connections()
            try:
                with connections["default"].cursor() as cursor:
                    cursor.execute("SELECT pg_backend_pid()")
                    pid = cursor.fetchone()[0]
                gate.wait(timeout=20)
                try:
                    result = call()
                    return pid, "ok", result.pk if hasattr(result, "pk") else result[0].pk
                except APIException as error:
                    return pid, "rejected", error.status_code
            finally:
                connections["default"].close()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(worker, range(2)))
        self.assertNotEqual(results[0][0], results[1][0])
        return results

    def test_same_request_key_creates_one_instruction_and_audit(self):
        data = self.data()
        before = OperationLog.objects.count()
        results = self.parallel(lambda: ledger.submit(data, self.maker))
        self.assertEqual([r[1] for r in results], ["ok", "ok"])
        self.assertEqual(results[0][2], results[1][2])
        self.assertEqual(FinanceInstruction.objects.count(), 1)
        self.assertEqual(OperationLog.objects.count(), before + 1)

    def test_concurrent_same_instruction_posts_once(self):
        instruction, _ = ledger.submit(self.data(), self.maker)
        before = OperationLog.objects.count()
        results = self.parallel(lambda: ledger.post(instruction.pk, self.maker, voucher_checked=True))
        self.assertEqual([r[1] for r in results], ["ok", "ok"])
        self.assertEqual(results[0][2], results[1][2])
        self.assertEqual(FinanceFact.objects.count(), 1)
        self.assertEqual(OperationLog.objects.count(), before + 1)

    def test_concurrent_partial_returns_cannot_exceed_original(self):
        parent = self.fact()
        instructions = [ledger.submit(self.data(kind="bank_return", parent=parent.pk, direction="expense", amount="60.00"), self.maker)[0] for _ in range(2)]
        gate = Barrier(2)

        def execute(index):
            close_old_connections()
            try:
                gate.wait(timeout=20)
                try:
                    return ledger.post(instructions[index].pk, self.maker, voucher_checked=True).pk
                except APIException:
                    return None
            finally:
                connections["default"].close()

        before = OperationLog.objects.count()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(execute, range(2)))
        self.assertEqual(sum(r is not None for r in results), 1)
        self.assertEqual(FinanceFact.objects.filter(parent=parent).count(), 1)
        self.assertEqual(OperationLog.objects.count(), before + 1)
        self.assertEqual(sorted(FinanceInstruction.objects.filter(pk__in=[i.pk for i in instructions]).values_list("status", flat=True)), ["pending", "posted"])

    def test_two_refund_payments_share_approval_ceiling(self):
        parent = self.fact()
        approval, _ = ledger.submit(self.data(kind="refund_approval", parent=parent.pk, direction="expense", amount="100.00", excess_reason="合成批准依据"), self.maker)
        ledger.approve(approval.pk, self.reviewer)
        pending = [ledger.submit(self.data(kind="refund_payment", approval=approval.pk, amount="60.00", direction="expense"), self.maker)[0] for _ in range(2)]
        for instruction in pending:
            ledger.approve(instruction.pk, self.reviewer)
        gate = Barrier(2)

        def execute(index):
            close_old_connections()
            try:
                gate.wait(timeout=20)
                try:
                    return ledger.post(pending[index].pk, self.maker, voucher_checked=True).pk
                except APIException:
                    return None
            finally:
                connections["default"].close()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(execute, range(2)))
        self.assertEqual(sum(r is not None for r in results), 1)
        self.assertEqual(FinanceFact.objects.filter(kind="refund_payment").count(), 1)

    def test_concurrent_corrections_cannot_create_two_effective_versions(self):
        from queue import Queue
        parent = self.fact()
        work = Queue()
        for value in ("80.00", "90.00"):
            instruction, _ = ledger.submit(self.data(kind="correction", parent=parent.pk, amount=value), self.maker)
            ledger.approve(instruction.pk, self.reviewer)
            work.put(instruction.pk)
        before = OperationLog.objects.count()
        results = self.parallel(lambda: ledger.post(work.get_nowait(), self.maker, voucher_checked=True))
        self.assertCountEqual([row[1] for row in results], ["ok", "rejected"])
        self.assertEqual(FinanceFact.objects.filter(kind="correction").count(), 1)
        parent.refresh_from_db()
        self.assertEqual(str(parent.amount), "100.00")
        self.assertEqual(OperationLog.objects.count(), before + 1)
