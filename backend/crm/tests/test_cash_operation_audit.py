from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from crm.models import CashSourceAllocation, OperationLog, RmbCashEvent
from crm.services import cash_events
from crm.tests.test_cash_events import ACCOUNTS, CashFixture, payload


@override_settings(RMB_CASH_ACCOUNT_IDS=ACCOUNTS, AUDIT_LOG_ENABLED=True)
class CashOperationAuditTests(CashFixture, TestCase):
    def setUp(self):
        self.setup_cash()
        self.user = get_user_model().objects.create_superuser("cash-audit-test", "", "test-only-password")

    def test_registered_and_confirmed_once_with_real_operator(self):
        data = payload([self.receipt], key="AUDIT-ONCE")
        event, created = cash_events.register_event(data, self.user)
        self.assertTrue(created)
        replay, created = cash_events.register_event(data, self.user)
        self.assertFalse(created)
        self.assertEqual(event.pk, replay.pk)
        cash_events.confirm_event(event.pk, self.user, voucher_checked=True)
        cash_events.confirm_event(event.pk, self.user, voucher_checked=True)
        logs = list(OperationLog.objects.filter(entity="crm.rmbcashevent").order_by("pk"))
        self.assertEqual(len(logs), 2)
        self.assertTrue(all(row.operator_id == self.user.pk for row in logs))
        self.assertEqual(logs[1].before_data["status"], "pending")
        self.assertEqual(logs[1].after_data["status"], "confirmed")

    def test_audit_failure_rolls_back_registration_and_confirmation(self):
        data = payload([self.receipt], key="AUDIT-FAIL")
        with patch("crm.services.finance_closeout.audit", side_effect=RuntimeError("synthetic audit failure")):
            with self.assertRaises(RuntimeError):
                cash_events.register_event(data, self.user)
        self.assertFalse(RmbCashEvent.objects.filter(request_key="AUDIT-FAIL").exists())
        self.assertFalse(CashSourceAllocation.objects.exists())
        event, _ = cash_events.register_event(data, self.user)
        with patch("crm.services.finance_closeout.audit", side_effect=RuntimeError("synthetic audit failure")):
            with self.assertRaises(RuntimeError):
                cash_events.confirm_event(event.pk, self.user, voucher_checked=True)
        event.refresh_from_db()
        self.assertEqual(event.status, "pending")
        self.assertIsNone(event.confirmed_at)
        self.assertEqual(OperationLog.objects.filter(entity="crm.rmbcashevent").count(), 1)

    def test_cancel_reason_and_failed_audit_leave_pending_state(self):
        event, _ = cash_events.register_event(payload([self.receipt], key="AUDIT-CANCEL"), self.user)
        with patch("crm.services.finance_closeout.audit", side_effect=RuntimeError("synthetic audit failure")):
            with self.assertRaises(RuntimeError):
                cash_events.cancel_pending(event.pk, self.user, "synthetic reason")
        event.refresh_from_db()
        self.assertEqual(event.status, "pending")
        cash_events.cancel_pending(event.pk, self.user, "synthetic reason")
        log = OperationLog.objects.filter(entity="crm.rmbcashevent").order_by("pk").last()
        self.assertEqual(log.before_data["status"], "pending")
        self.assertEqual(log.after_data["status"], "cancelled")
        self.assertEqual(log.after_data["cancelled_reason"], "synthetic reason")

    def test_development_identity_is_not_a_fabricated_user(self):
        from django.contrib.auth.models import AnonymousUser

        event, _ = cash_events.register_event(payload([self.receipt], key="AUDIT-DEVELOPMENT"), AnonymousUser())
        self.assertEqual(event.created_actor["kind"], "development_superadmin")
        log = OperationLog.objects.get(entity="crm.rmbcashevent")
        self.assertIsNone(log.operator_id)
        self.assertEqual(log.metadata["actor"]["kind"], "development_superadmin")
