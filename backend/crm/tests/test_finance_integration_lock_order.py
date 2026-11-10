"""Focused finance match/reconciliation boundaries and real PostgreSQL lock order."""
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
import json
from queue import Empty, Queue
from threading import Event
import time
import unittest
import uuid

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import close_old_connections, connection, connections, transaction
from django.test import TestCase, TransactionTestCase, override_settings
from rest_framework.exceptions import APIException
from rest_framework.test import APIClient

from crm.models import (
    FinanceClassification,
    FinanceFact,
    FinanceHistoricalTransfer,
    FinanceReview,
    FinanceTransferMatch,
    OperationLog,
)
from crm.services import finance_closeout as ledger
from crm.tests.test_cash_events import CashFixture, payload as bank_payload
from crm.tests.test_finance_closeout import CloseoutFixture
from crm.services import cash_events


FINANCE_TEST_CASH_ACCOUNTS = ("SYNTH_FX", "SYNTH_CNY")
REVIEW_END = "2026-10-31"
REVIEW_START = "2026-10-01"


class FinanceLockOrderFixture(CloseoutFixture):
    def setup_lock_order_fixture(self):
        self.setup_ledger()
        self.client = APIClient()
        self.client.force_authenticate(self.maker)

    def create_confirmed_legacy_income(self, bank_date="2026-10-18"):
        # The bank event and its source are isolated synthetic fixture data.
        CashFixture.setup_cash(self)
        # CashFixture installs its own MEDIA_ROOT after CloseoutFixture uploaded
        # the account voucher; create a fresh account-scoped proof in that root.
        self.proof = ledger.upload(
            SimpleUploadedFile(
                "lock-order-account.pdf",
                b"%PDF-1.4\nSynthetic lock-order account proof\n%%EOF",
            ),
            self.maker,
        )
        event, _ = cash_events.register_event(
            bank_payload(
                [self.receipt],
                key="LOCK-ORDER-" + uuid.uuid4().hex,
                bank_date=bank_date,
            ),
            self.maker,
        )
        cash_events.confirm_event(event.pk, self.maker, voucher_checked=True)
        ledger.map_account(
            {
                "account": self.account.pk,
                "legacy_code": "SYNTH_CNY",
                "reason": "合成旧银行账户映射",
            },
            self.maker,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.maker)
        return event

    def create_opening(self, account_obj, amount="1000.00"):
        return self.fact(
            kind="opening",
            account=account_obj.pk,
            actual_date=REVIEW_START,
            amount=amount,
        )

    def api_review_status(self, review, date_to=REVIEW_END):
        response = self.client.get("/api/finance-ledger/", {"date_to": date_to})
        self.assertEqual(response.status_code, 200, response.data)
        return next(row["status"] for row in response.data["reviews"] if row["id"] == review.pk)

    def old_balance_fingerprint(self, account_obj, end=REVIEW_END):
        """Recreate the pre-9068350 summary shape for a synthetic persisted row."""
        facts, legacy = ledger.account_rows(account_obj, end, self.maker)
        opening = next((fact for fact in facts if fact.kind == "opening"), None)
        self.assertIsNotNone(opening, "Legacy review fixture requires an opening baseline")
        included_legacy = [event for event in legacy if event.bank_date >= opening.actual_date]
        corrections = list(
            FinanceFact.objects.filter(account=account_obj, kind="correction")
            .order_by("pk")
            .values_list("pk", flat=True)
        )
        classifications = list(
            FinanceClassification.objects.filter(fact__in=facts)
            .order_by("pk")
            .values_list("pk", flat=True)
        )
        return ledger.digest(
            {
                "facts": [fact.pk for fact in facts],
                "legacy": [event.pk for event in included_legacy],
                "corrections": corrections,
                "classifications": classifications,
            }
        )

    def seed_pre_upgrade_review(self, account_obj, reason):
        """Seed only the old persisted digest; service-created finance rows stay intact."""
        calculated, _ = ledger.balance(account_obj, REVIEW_END, self.maker)
        self.assertIsNotNone(calculated)
        return FinanceReview.objects.create(
            account=account_obj,
            date_from=REVIEW_START,
            date_to=REVIEW_END,
            voucher=self.proof,
            statement_balance=calculated,
            calculated_balance=calculated,
            difference=Decimal("0.00"),
            fingerprint=self.old_balance_fingerprint(account_obj),
            completed=True,
            reason=reason,
            actor={"kind": "synthetic_pre_upgrade_review_fixture"},
        )


@override_settings(RMB_CASH_ACCOUNT_IDS=FINANCE_TEST_CASH_ACCOUNTS)
class FinanceIntegrationLockBoundaryTests(FinanceLockOrderFixture, TestCase):
    def setUp(self):
        self.setup_lock_order_fixture()

    def test_post_period_fact_match_does_not_invalidate_cutoff_review(self):
        self.create_opening(self.account)
        review = ledger.reconcile(
            {
                "account": self.account.pk,
                "date_from": REVIEW_START,
                "date_to": REVIEW_END,
                "voucher": self.proof.pk,
                "statement_balance": "1000.00",
                "completed": True,
                "reason": "合成十月月末核对",
            },
            self.maker,
        )
        before_amount, before_fingerprint = ledger.balance(self.account, REVIEW_END, self.maker)
        outgoing = self.fact(
            account=self.account.pk,
            actual_date="2026-11-02",
            direction="expense",
            amount="75.00",
            nature="internal_principal",
        )
        incoming = self.fact(
            account=self.second.pk,
            actual_date="2026-11-03",
            direction="income",
            amount="75.00",
            nature="internal_principal",
        )

        match = ledger.match_transfer(
            {"outgoing": outgoing.pk, "incoming": incoming.pk, "reason": "合成十一月本金匹配"},
            self.maker,
        )

        after_amount, after_fingerprint = ledger.balance(self.account, REVIEW_END, self.maker)
        self.assertIsNotNone(match.pk)
        self.assertEqual(after_amount, before_amount)
        self.assertEqual(after_fingerprint, before_fingerprint)
        self.assertEqual(self.api_review_status(review), "completed")

    def test_pre_cutoff_legacy_post_cutoff_fact_match_invalidates_review(self):
        legacy = self.create_confirmed_legacy_income(bank_date="2026-10-18")
        self.create_opening(self.account)
        outgoing = self.fact(
            account=self.second.pk,
            actual_date="2026-11-02",
            direction="expense",
            amount=str(legacy.bank_net_amount),
            nature="internal_principal",
        )
        amount_before, _ = ledger.balance(self.account, REVIEW_END, self.maker)
        review = ledger.reconcile(
            {
                "account": self.account.pk,
                "date_from": REVIEW_START,
                "date_to": REVIEW_END,
                "voucher": self.proof.pk,
                "statement_balance": str(amount_before),
                "completed": True,
                "reason": "合成十月旧银行核对",
            },
            self.maker,
        )

        match = ledger.match_historical_transfer(
            {
                "outgoing": f"fact:{outgoing.pk}",
                "incoming": f"legacy:{legacy.pk}",
                "outgoing_voucher": self.proof.pk,
                "incoming_voucher": self.proof.pk,
                "reason": "合成跨期新旧本金匹配",
            },
            self.maker,
        )

        amount_after, fingerprint_after = ledger.balance(self.account, REVIEW_END, self.maker)
        self.assertIsNotNone(match.pk)
        self.assertEqual(amount_after, amount_before)
        self.assertNotEqual(fingerprint_after, review.fingerprint)
        self.assertEqual(self.api_review_status(review), "needs_review")

    def test_existing_new_match_with_pre_upgrade_digest_needs_review(self):
        self.create_opening(self.account)
        outgoing = self.fact(
            account=self.account.pk,
            actual_date="2026-10-19",
            direction="expense",
            amount="50.00",
            nature="internal_principal",
        )
        incoming = self.fact(
            account=self.second.pk,
            actual_date="2026-10-20",
            direction="income",
            amount="50.00",
            nature="internal_principal",
        )
        ledger.match_transfer(
            {"outgoing": outgoing.pk, "incoming": incoming.pk, "reason": "合成既有新事实匹配"},
            self.maker,
        )

        old_review = self.seed_pre_upgrade_review(self.account, "合成升级前旧摘要：新事实匹配已存在")

        self.assertNotEqual(ledger.balance(self.account, REVIEW_END, self.maker)[1], old_review.fingerprint)
        self.assertEqual(self.api_review_status(old_review), "needs_review")

    def test_existing_historical_match_with_pre_upgrade_digest_needs_review(self):
        legacy = self.create_confirmed_legacy_income(bank_date="2026-10-18")
        self.create_opening(self.account)
        outgoing = self.fact(
            account=self.second.pk,
            actual_date="2026-10-19",
            direction="expense",
            amount=str(legacy.bank_net_amount),
            nature="internal_principal",
        )
        ledger.match_historical_transfer(
            {
                "outgoing": f"fact:{outgoing.pk}",
                "incoming": f"legacy:{legacy.pk}",
                "outgoing_voucher": self.proof.pk,
                "incoming_voucher": self.proof.pk,
                "reason": "合成既有新旧银行匹配",
            },
            self.maker,
        )

        old_review = self.seed_pre_upgrade_review(self.account, "合成升级前旧摘要：历史匹配已存在")

        self.assertNotEqual(ledger.balance(self.account, REVIEW_END, self.maker)[1], old_review.fingerprint)
        self.assertEqual(self.api_review_status(old_review), "needs_review")


@unittest.skipUnless(connection.vendor == "postgresql", "Requires actual PostgreSQL row locks and backend connections")
@override_settings(RMB_CASH_ACCOUNT_IDS=FINANCE_TEST_CASH_ACCOUNTS)
class FinanceIntegrationLockOrderPostgreSQLTests(FinanceLockOrderFixture, TransactionTestCase):
    LOCK_WAIT_TIMEOUT_SECONDS = 20

    def setUp(self):
        self.setup_lock_order_fixture()
        self.legacy = self.create_confirmed_legacy_income(bank_date="2026-10-18")
        self.create_opening(self.account, "1000.00")
        self.second_opening = self.create_opening(self.second, "1000.00")
        self.outgoing = self.fact(
            account=self.second.pk,
            actual_date="2026-10-19",
            direction="expense",
            amount=str(self.legacy.bank_net_amount),
            nature="internal_principal",
        )
        self.match_payload = {
            "outgoing": f"fact:{self.outgoing.pk}",
            "incoming": f"legacy:{self.legacy.pk}",
            "outgoing_voucher": self.proof.pk,
            "incoming_voucher": self.proof.pk,
            "reason": "合成PostgreSQL锁顺序本金核实",
        }

    def _wait_until_blocked_by(self, worker_pid, main_pid, account_lock_started, future):
        deadline = time.monotonic() + self.LOCK_WAIT_TIMEOUT_SECONDS
        last_observation = None
        while time.monotonic() < deadline:
            with connection.cursor() as cursor:
                # The lock owner stays in one transaction during this poll.
                cursor.execute("SELECT pg_stat_clear_snapshot()")
                cursor.execute(
                    """
                    SELECT wait_event_type, state, query, pg_blocking_pids(pid)
                    FROM pg_stat_activity WHERE pid = %s
                    """,
                    [worker_pid],
                )
                row = cursor.fetchone()
            if row:
                last_observation = {
                    "wait_event_type": row[0],
                    "state": row[1],
                    "query": row[2],
                    "blocking_pids": row[3],
                }
            if (
                account_lock_started.is_set()
                and row
                and row[1] == "active"
                and main_pid in row[3]
            ):
                return {
                    "confirmed": True,
                    "wait_event_type": row[0],
                    "state": row[1],
                    "query": row[2],
                    "blocking_pids": row[3],
                }
            if future.done():
                return {"confirmed": False, "last_observation": last_observation}
            time.sleep(0.05)
        return {"confirmed": False, "last_observation": last_observation}

    def _run_worker_behind_account_lock(
        self, locked_account, worker_call, owner_action, expected_pre_lock_tables
    ):
        worker_pid_queue = Queue(maxsize=1)
        account_lock_started = Event()
        worker_account_lock_queries = []
        worker_pre_account_lock_queries = []
        worker_queries_seen = []
        blocked = None
        main_pid = None
        main_database = None
        main_lock_details = []
        worker_future = None
        owner_result = None
        logs_after_owner_action = None

        def worker():
            close_old_connections()
            try:
                with connections["default"].cursor() as cursor:
                    cursor.execute("SET application_name TO 'finance-lock-order-test-worker'")
                    cursor.execute("SELECT pg_backend_pid(), current_database()")
                    backend_pid, database_name = cursor.fetchone()
                worker_pid_queue.put(backend_pid)

                def observe_real_account_lock(execute, sql, params, many, context):
                    normalized_sql = sql.lower()
                    if "crm_financeaccount" in normalized_sql and "for update" in normalized_sql:
                        if not account_lock_started.is_set():
                            worker_pre_account_lock_queries.extend(worker_queries_seen)
                        account_lock_started.set()
                        worker_account_lock_queries.append({"sql": sql, "params": repr(params)})
                    else:
                        worker_queries_seen.append(sql)
                    return execute(sql, params, many, context)

                try:
                    with connections["default"].execute_wrapper(observe_real_account_lock):
                        value = worker_call()
                    return {
                        "pid": backend_pid,
                        "database": database_name,
                        "account_lock_queries": worker_account_lock_queries,
                        "pre_account_lock_queries": worker_pre_account_lock_queries,
                        "kind": "completed",
                        "value": getattr(value, "pk", None),
                    }
                except APIException as exc:
                    return {
                        "pid": backend_pid,
                        "database": database_name,
                        "account_lock_queries": worker_account_lock_queries,
                        "pre_account_lock_queries": worker_pre_account_lock_queries,
                        "kind": "rejected",
                        "status": exc.status_code,
                    }
            finally:
                connections["default"].close()

        with ThreadPoolExecutor(max_workers=1) as pool:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute("SELECT pg_backend_pid(), current_database()")
                    main_pid, main_database = cursor.fetchone()
                self.assertTrue(connection.in_atomic_block)
                with connection.cursor() as cursor:
                    cursor.execute(
                        'SELECT id FROM "crm_financeaccount" WHERE id = %s FOR UPDATE',
                        [locked_account.pk],
                    )
                    self.assertEqual(cursor.fetchone()[0], locked_account.pk)
                    cursor.execute(
                        """
                        SELECT locktype, mode, granted,
                               CASE WHEN relation IS NULL THEN NULL ELSE relation::regclass::text END,
                               transactionid::text
                        FROM pg_locks WHERE pid = %s ORDER BY locktype, mode
                        """,
                        [main_pid],
                    )
                    main_lock_details = [list(row) for row in cursor.fetchall()]
                worker_future = pool.submit(worker)
                try:
                    worker_pid = worker_pid_queue.get(timeout=10)
                except Empty:
                    if worker_future.done():
                        worker_future.result()
                    self.fail("Worker did not establish its independent PostgreSQL backend")
                blocked = self._wait_until_blocked_by(worker_pid, main_pid, account_lock_started, worker_future)
                if blocked["confirmed"]:
                    observed_sql = [sql.lower() for sql in worker_pre_account_lock_queries]
                    missing_tables = [
                        table for table in expected_pre_lock_tables
                        if not any(table in sql for sql in observed_sql)
                    ]
                    self.assertFalse(
                        missing_tables,
                        "The worker must finish its service pre-read before it waits for the account lock; "
                        f"missing SQL tables={missing_tables}, observed={worker_pre_account_lock_queries}",
                    )
                    owner_result = owner_action()
                    logs_after_owner_action = OperationLog.objects.count()
            worker_result = worker_future.result(timeout=30)

        print(
            "FINANCE_LOCK_ORDER_EVIDENCE="
            + json.dumps(
                {
                    "main_backend_pid": main_pid,
                    "main_database": main_database,
                    "locked_account_id": locked_account.pk,
                    "main_pg_locks": main_lock_details,
                    "worker_backend_pid": worker_result["pid"],
                    "worker_database": worker_result.get("database"),
                    "worker_account_lock_queries": worker_result.get("account_lock_queries"),
                    "worker_pre_account_lock_queries": worker_result.get("pre_account_lock_queries"),
                    "account_lock_wait": blocked,
                    "owner_action_result": getattr(owner_result, "pk", None),
                    "worker_result": worker_result,
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            flush=True,
        )
        return {
            "main_pid": main_pid,
            "main_database": main_database,
            "locked_account_id": locked_account.pk,
            "main_pg_locks": main_lock_details,
            "worker_pid": worker_result["pid"],
            "worker_pre_account_lock_queries": worker_result.get("pre_account_lock_queries"),
            "blocked": blocked,
            "owner_result": owner_result,
            "logs_after_owner_action": logs_after_owner_action,
            "worker_result": worker_result,
        }

    def _assert_blocked_worker_rejected(self, result):
        self.assertEqual(result["main_database"], result["worker_result"].get("database"))
        self.assertIsNotNone(result["blocked"], "Worker must wait on the main transaction's real row lock")
        self.assertTrue(result["blocked"]["confirmed"], result["blocked"])
        self.assertTrue(
            any("for update" in item["sql"].lower() for item in result["worker_result"]["account_lock_queries"]),
            result["worker_result"],
        )
        self.assertNotEqual(result["main_pid"], result["worker_pid"], "Worker must use another backend PID")
        self.assertEqual(result["worker_result"]["kind"], "rejected", result["worker_result"])
        self.assertEqual(result["worker_result"]["status"], 400, result["worker_result"])
        self.assertEqual(OperationLog.objects.count(), result["logs_after_owner_action"])

    def test_waiting_historical_match_rechecks_classification_committed_first(self):
        balance_before = ledger.balance(self.second, REVIEW_END, self.maker)[0]
        logs_before = OperationLog.objects.count()

        result = self._run_worker_behind_account_lock(
            self.second,
            lambda: ledger.match_historical_transfer(self.match_payload, self.maker),
            lambda: ledger.classify(
                {"fact": self.outgoing.pk, "nature": "expense", "reason": "并发核实为对外支出"},
                self.maker,
            ),
            expected_pre_lock_tables=(
                "crm_financefact",
                "crm_rmbcashevent",
                "crm_financeaccountmapping",
            ),
        )

        self._assert_blocked_worker_rejected(result)
        self.assertEqual(FinanceClassification.objects.filter(fact=self.outgoing).count(), 1)
        self.assertEqual(ledger.effective_nature(self.outgoing), "expense")
        self.assertEqual(FinanceHistoricalTransfer.objects.count(), 0)
        self.assertEqual(OperationLog.objects.count(), logs_before + 1)
        self.assertEqual(ledger.balance(self.second, REVIEW_END, self.maker)[0], balance_before)

    def test_waiting_historical_match_rechecks_correction_committed_first(self):
        correction, _ = ledger.submit(
            self.data(
                kind="correction",
                account=self.second.pk,
                parent=self.outgoing.pk,
                actual_date="2026-10-20",
                amount=str(self.outgoing.amount),
                direction="expense",
                nature="unclassified",
            ),
            self.maker,
        )
        ledger.approve(correction.pk, self.reviewer)
        balance_before = ledger.balance(self.second, REVIEW_END, self.maker)[0]
        logs_before_owner_action = OperationLog.objects.count()

        result = self._run_worker_behind_account_lock(
            self.second,
            lambda: ledger.match_historical_transfer(self.match_payload, self.maker),
            lambda: ledger.post(correction.pk, self.maker, voucher_checked=True),
            expected_pre_lock_tables=(
                "crm_financefact",
                "crm_rmbcashevent",
                "crm_financeaccountmapping",
            ),
        )

        self._assert_blocked_worker_rejected(result)
        self.assertEqual(result["logs_after_owner_action"], logs_before_owner_action + 1)
        self.assertEqual(FinanceFact.objects.filter(parent=self.outgoing, kind="correction").count(), 1)
        self.assertIn(self.outgoing.pk, ledger.corrected_ids()[0])
        self.assertEqual(FinanceHistoricalTransfer.objects.count(), 0)
        self.assertEqual(ledger.balance(self.second, REVIEW_END, self.maker)[0], balance_before)

    def test_classification_waiting_behind_committed_historical_match_is_rejected(self):
        balance_before = ledger.balance(self.second, REVIEW_END, self.maker)[0]
        logs_before = OperationLog.objects.count()

        result = self._run_worker_behind_account_lock(
            self.second,
            lambda: ledger.classify(
                {"fact": self.outgoing.pk, "nature": "expense", "reason": "并发尝试改为对外支出"},
                self.maker,
            ),
            lambda: ledger.match_historical_transfer(self.match_payload, self.maker),
            expected_pre_lock_tables=("crm_financefact",),
        )

        self._assert_blocked_worker_rejected(result)
        self.assertEqual(FinanceHistoricalTransfer.objects.count(), 1)
        self.assertEqual(FinanceClassification.objects.filter(fact=self.outgoing).count(), 0)
        self.assertEqual(OperationLog.objects.count(), logs_before + 1)
        self.assertEqual(ledger.balance(self.second, REVIEW_END, self.maker)[0], balance_before)
