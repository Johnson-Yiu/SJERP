"""Independent bank fees keep the existing source, voucher and idempotency contract."""
from decimal import Decimal

from django.test import TestCase, override_settings

from crm.models import CashSourceAllocation, RmbCashEvent
from crm.services.finance import record_transaction
from crm.tests.test_cash_events import ACCOUNTS, CashFixture, legacy_hash, payload


@override_settings(RMB_CASH_ACCOUNT_IDS=ACCOUNTS)
class IndependentBankFeeTests(CashFixture, TestCase):
    def setUp(self):
        self.setup_cash()
        self.fee = record_transaction(dict(transaction_no="SYNTH-INDEPENDENT-FEE", kind="bank_fee", direction="expense", category="银行手续费", amount="5", currency="CNY", exchange_rate="1"))
        self.data = payload([self.fee], key="INDEPENDENT-FEE", currency="CNY", kind="bank_fee", direction="expense", bank_net_amount="5.00", fee_mode="none", fee_amount="0", quoted_rate=None, fee_for=None)

    def test_no_parent_preview_register_confirm_replay_counts_once(self):
        before = legacy_hash()
        preview = self.client.post("/api/rmb-cash-events/preview/", self.data, format="json")
        self.assertEqual(preview.status_code, 200, preview.data)
        self.assertIsNone(preview.data["payload"]["fee_for"])
        self.assertFalse(RmbCashEvent.objects.exists())
        pk = self.register(self.data)
        replay = self.client.post("/api/rmb-cash-events/", self.data, format="json")
        self.assertEqual(replay.status_code, 200)
        self.assertEqual(replay.data["id"], pk)
        self.confirm(pk, 400, voucher_checked=False)
        self.confirm(pk)
        self.confirm(pk)
        self.assertEqual(CashSourceAllocation.objects.count(), 1)
        self.assertEqual(RmbCashEvent.objects.count(), 1)
        self.assertIsNone(RmbCashEvent.objects.get().fee_for_id)
        totals = self.client.get("/api/actual-rmb-cash/", {"date_from": "2026-10-01", "date_to": "2026-10-31"}).data["totals"]
        self.assertEqual(totals, {"inflow": "0", "outflow": "5.00", "net": "-5.00", "count": 1})
        self.assertEqual(legacy_hash(), before)

    def test_optional_parent_still_checks_status_account_kind_and_included_fee(self):
        parent = self.register(payload([self.receipt], fee_mode="none", fee_amount="0"))
        self.data["fee_for"] = parent
        self.assertEqual(self.client.post("/api/rmb-cash-events/preview/", self.data, format="json").status_code, 400)
        self.confirm(parent)
        for changes, expected in [({"fee_for": 999999}, 404), ({"rmb_account": "WRONG"}, 400), ({"fee_for": 0}, 400)]:
            response = self.client.post("/api/rmb-cash-events/preview/", {**self.data, **changes}, format="json")
            self.assertEqual(response.status_code, expected, response.data)
        self.assertEqual(self.client.post("/api/rmb-cash-events/preview/", self.data, format="json").status_code, 200)
        self.confirm(self.register(self.data))
        self.assertEqual(RmbCashEvent.objects.count(), 2)

    def test_fee_source_precision_voucher_and_quota_remain_required(self):
        for changes in ({"sources": []}, {"bank_net_amount": "5.001"}, {"currency": "USD"}, {"sources": [{"transaction_id": self.fee.pk, "amount": "5.00", "verified": False}]}):
            response = self.client.post("/api/rmb-cash-events/", {**self.data, **changes}, format="json")
            self.assertEqual(response.status_code, 400, response.data)
        pk = self.register({**self.data, "evidence_sha256": ""})
        self.confirm(pk, 400)
        self.assertEqual(RmbCashEvent.objects.get(pk=pk).status, "pending")
        self.assertEqual(self.fee.amount, Decimal("5"))
