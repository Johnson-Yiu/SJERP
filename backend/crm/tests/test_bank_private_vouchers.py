from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.exceptions import APIException

from crm.models import FinanceBankVoucherBinding, RmbCashEvent
from crm.services import bank_vouchers, cash_events
from crm.tests.test_cash_events import ACCOUNTS, CashFixture, bank_voucher, payload


@override_settings(RMB_CASH_ACCOUNT_IDS=ACCOUNTS)
class BankPrivateVoucherTests(CashFixture, TestCase):
    def setUp(self):
        self.setup_cash()

    def test_manually_supplied_sha_cannot_confirm_new_bank_fact(self):
        data = payload([self.receipt])
        proof = data.pop("private_voucher")
        event, _ = cash_events.register_event(data, self.user)
        with self.assertRaises(APIException):
            cash_events.confirm_event(event.pk, self.user, voucher_checked=True)
        event.refresh_from_db()
        self.assertEqual(event.status, "pending")
        bank_vouchers.bind(event, proof, self.user)
        cash_events.confirm_event(event.pk, self.user, voucher_checked=True)
        self.assertEqual(FinanceBankVoucherBinding.objects.filter(event=event).count(), 1)

    def test_tampered_file_does_not_confirm_or_release_source(self):
        event, _ = cash_events.register_event(payload([self.receipt]), self.user)
        proof = bank_voucher([self.receipt])
        with proof.file.open("wb") as target:
            target.write(b"%PDF-tampered")
        with self.assertRaises(APIException):
            cash_events.confirm_event(event.pk, self.user, voucher_checked=True)
        event.refresh_from_db()
        self.assertEqual(event.status, "pending")
        self.assertEqual(cash_events.available(self.receipt), self.receipt.amount)

    def test_binding_audit_failure_rolls_back_whole_registration(self):
        with patch("crm.services.bank_vouchers.ledger.audit", side_effect=RuntimeError("synthetic audit failure")):
            with self.assertRaises(RuntimeError):
                cash_events.register_event(payload([self.receipt]), self.user)
        self.assertFalse(RmbCashEvent.objects.exists())
        self.assertFalse(FinanceBankVoucherBinding.objects.exists())

    def test_missing_scope_cannot_download_bank_file_from_account_endpoint(self):
        proof = bank_voucher([self.receipt])
        response = self.client.get(f"/api/finance-ledger/voucher-download/?id={proof.pk}")
        self.assertEqual(response.status_code, 403)
        event, _ = cash_events.register_event(payload([self.receipt]), self.user)
        response = self.client.get(f"/api/rmb-cash-events/{event.pk}/voucher-download/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertIn(b"Synthetic bank voucher", b"".join(response.streaming_content))
