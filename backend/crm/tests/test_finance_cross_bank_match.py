from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import SimpleNamespace
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection, connections
from django.test import TestCase, TransactionTestCase, override_settings
from rest_framework.exceptions import APIException

from crm.models import FinanceBankFactMatch, FinanceFact
from crm.services import cash_events as cash, finance_closeout as ledger
from crm.tests.test_cash_events import CashFixture, payload
from crm.tests.test_finance_closeout import CloseoutFixture


@override_settings(RMB_CASH_ACCOUNT_IDS=("SYNTH_FX", "SYNTH_CNY"))
class CrossModuleBankTests(CloseoutFixture, CashFixture, TestCase):
    def setUp(self):
        self.setup_ledger()
        self.setup_cash()
        self.proof = ledger.upload(SimpleUploadedFile("fact.pdf", b"%PDF-1.4\nsynthetic fact\n%%EOF"), self.maker)
        self.bank_event, _ = cash.register_event(payload([self.receipt], key="BANK-CROSS", bank_net_amount="700.00", fee_amount="5.00"), self.maker)
        ledger.map_account({"account": self.account.pk, "legacy_code": "SYNTH_CNY", "reason": "核对合成银行账户"}, self.maker)

    def event(self):
        return self.bank_event

    def fact_data(self):
        return self.data(actual_date="2026-10-18", amount="700.00")

    def test_fact_first_requires_review_and_links_only_after_review(self):
        fact = self.fact(actual_date="2026-10-18", amount="700.00")
        event = self.event()
        candidates = cash.duplicate_candidates(event.request_payload, self.maker, exclude_id=event.pk)
        self.assertEqual(candidates["count"], 1)
        with self.assertRaises(APIException):
            cash.confirm_event(event.pk, self.maker, voucher_checked=True)
        cash.confirm_event(event.pk, self.maker, voucher_checked=True, duplicate_token=candidates["token"], duplicate_reason="两份银行凭证属于同一笔", same_fact=fact.pk)
        self.assertTrue(FinanceBankFactMatch.objects.filter(fact=fact, event=event).exists())
        rows = ledger.reporting_events(self.maker, "2026-10-01", "2026-10-31")
        self.assertEqual([(r.bank_net_amount, r.fee_amount, r.currency) for r in rows], [(Decimal("700"), Decimal("5"), "USD")])
        self.assertIn(event.pk, ledger.matched_legacy_ids(self.maker))
        from crm.actual_cash_api import _visible_events
        from datetime import date
        visible = _visible_events(SimpleNamespace(user=self.maker), date(2026, 10, 1), date(2026, 10, 31))
        self.assertEqual(sum(row.bank_net_amount for row in visible), Decimal("700"))

    def test_event_first_links_and_distinct_same_amount_stays_separate(self):
        event = self.event()
        cash.confirm_event(event.pk, self.maker, voucher_checked=True)
        data = self.fact_data()
        candidate = ledger.duplicate_candidates(ledger.normalize(data), self.maker)
        data.update(duplicate_review_token=candidate["token"], duplicate_review_reason="两份银行凭证属于同一笔", same_legacy_event=event.pk)
        instruction, _ = ledger.submit(data, self.maker)
        fact = ledger.post(instruction.pk, self.maker, voucher_checked=True)
        self.assertTrue(FinanceBankFactMatch.objects.filter(fact=fact, event=event).exists())
        second = self.fact_data()
        candidate = ledger.duplicate_candidates(ledger.normalize(second), self.maker)
        second.update(duplicate_review_token=candidate["token"], duplicate_review_reason="银行流水核实为另一笔交易")
        instruction, _ = ledger.submit(second, self.maker)
        ledger.post(instruction.pk, self.maker, voucher_checked=True)
        self.assertEqual(sum(row.bank_net_amount for row in ledger.reporting_events(self.maker, "2026-10-01", "2026-10-31")), Decimal("1400"))

    def test_link_audit_failure_rolls_back_confirmation(self):
        fact = self.fact(actual_date="2026-10-18", amount="700.00")
        event = self.event()
        candidates = cash.duplicate_candidates(event.request_payload, self.maker, exclude_id=event.pk)
        with patch("crm.services.finance_closeout.audit", side_effect=RuntimeError("audit unavailable")):
            with self.assertRaises(RuntimeError):
                cash.confirm_event(event.pk, self.maker, voucher_checked=True, duplicate_token=candidates["token"], duplicate_reason="两份银行凭证属于同一笔", same_fact=fact.pk)
        event.refresh_from_db()
        self.assertEqual(event.status, "pending")
        self.assertFalse(FinanceBankFactMatch.objects.exists())
        self.assertEqual(FinanceFact.objects.count(), 1)


@override_settings(RMB_CASH_ACCOUNT_IDS=("SYNTH_FX", "SYNTH_CNY"))
class CrossModuleBankConcurrencyTests(CloseoutFixture, CashFixture, TransactionTestCase):
    def test_concurrent_confirmation_and_post_cannot_both_ignore_candidates(self):
        if connection.vendor != "postgresql":
            self.skipTest("Requires PostgreSQL advisory locks")
        self.setup_ledger()
        self.setup_cash()
        self.proof = ledger.upload(SimpleUploadedFile("fact.pdf", b"%PDF-1.4\nsynthetic fact\n%%EOF"), self.maker)
        event, _ = cash.register_event(payload([self.receipt], key="BANK-CONCURRENT", bank_net_amount="700.00", fee_amount="5.00"), self.maker)
        ledger.map_account({"account": self.account.pk, "legacy_code": "SYNTH_CNY", "reason": "核对合成银行账户"}, self.maker)
        instruction, _ = ledger.submit(self.data(actual_date="2026-10-18", amount="700.00"), self.maker)
        barrier = Barrier(2)

        def run(operation):
            try:
                barrier.wait(timeout=10)
                if operation == "fact":
                    ledger.post(instruction.pk, self.maker, voucher_checked=True)
                else:
                    cash.confirm_event(event.pk, self.maker, voucher_checked=True)
                return "ok"
            except APIException:
                return "review"
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(run, ("fact", "event")))
        self.assertCountEqual(results, ["ok", "review"])
        event.refresh_from_db()
        self.assertEqual(FinanceFact.objects.count() + int(event.status == "confirmed"), 1)
