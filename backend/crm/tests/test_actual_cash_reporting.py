from datetime import date
from decimal import Decimal

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from crm.models import RmbCashEvent, Transaction
from crm.services.finance import record_transaction
from crm.tests.test_cash_events import ACCOUNTS, CashFixture, payload


@override_settings(RMB_CASH_ACCOUNT_IDS=ACCOUNTS)
class ActualCashReportingTests(CashFixture, TestCase):
    def setUp(self):
        self.setup_cash()
        self.client = APIClient()

    def _confirmed(self, event_payload):
        response = self.client.post("/api/rmb-cash-events/", event_payload, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        confirm = self.client.post(f"/api/rmb-cash-events/{response.data['id']}/confirm/", {"voucher_checked": True}, format="json")
        self.assertEqual(confirm.status_code, 200, confirm.data)
        return response.data["id"]

    def test_actual_api_uses_confirmed_bank_net_and_bank_date(self):
        self.receipt.transaction_date = date(2026, 9, 1)
        self.receipt.rmb_amount = Decimal("999.9999")
        self.receipt.save(update_fields=["transaction_date", "rmb_amount"])
        fx = payload([self.receipt], key="ACTUAL-SEP", bank_date="2026-09-30", bank_net_amount="700.00", fee_mode="none", fee_amount="0")
        self._confirmed(fx)
        fee_source = record_transaction(dict(transaction_no="ACTUAL-FEE", kind="other_expense", direction="expense", category="银行扣款", amount="10", currency="CNY", exchange_rate="1"))
        cny = payload([fee_source], key="ACTUAL-OCT", currency="CNY", kind="cny_direct", direction="expense", bank_date="2026-10-01", bank_net_amount="10.00", fee_mode="none", fee_amount="0", quoted_rate=None)
        self._confirmed(cny)
        pending_source = record_transaction(dict(transaction_no="ACTUAL-PENDING-SOURCE", kind="other_income", direction="income", category="其他收入", amount="2", currency="USD", exchange_rate="7"))
        pending = payload([pending_source], key="ACTUAL-PENDING", bank_date="2026-09-30", bank_net_amount="1.00", fee_mode="none", fee_amount="0")
        pending_response = self.client.post("/api/rmb-cash-events/", pending, format="json")
        self.assertEqual(pending_response.status_code, 201)
        cancelled_source = record_transaction(dict(transaction_no="ACTUAL-CANCELLED-SOURCE", kind="other_income", direction="income", category="其他收入", amount="2", currency="USD", exchange_rate="7"))
        cancelled = payload([cancelled_source], key="ACTUAL-CANCELLED", bank_date="2026-09-30", bank_net_amount="1.00", fee_mode="none", fee_amount="0")
        cancelled_response = self.client.post("/api/rmb-cash-events/", cancelled, format="json")
        self.assertEqual(cancelled_response.status_code, 201)
        self.assertEqual(self.client.post(f"/api/rmb-cash-events/{cancelled_response.data['id']}/cancel/", {"reason": "合成测试放弃"}, format="json").status_code, 200)

        response = self.client.get("/api/actual-rmb-cash/", {"date_from": "2026-09-01", "date_to": "2026-10-31"})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["basis"], "bank_cash_confirmed_v1")
        self.assertIsNone(response.data["coverage_since"])
        self.assertEqual(response.data["totals"], {"inflow": "700.00", "outflow": "10.00", "net": "690.00", "count": 2})
        self.assertEqual([(row["month"], row["net"]) for row in response.data["monthly"]], [("2026-09", "700.00"), ("2026-10", "-10.00")])
        self.assertEqual({row["event_no"] for row in response.data["events"]}, {"ACTUAL-SEP", "ACTUAL-OCT"})
        self.assertNotIn("ACTUAL-PENDING", {row["event_no"] for row in response.data["events"]})
        self.assertNotIn("ACTUAL-CANCELLED", {row["event_no"] for row in response.data["events"]})
        self.assertEqual(self.client.get("/api/actual-rmb-cash/", {"date_from": "2026-09-30", "date_to": "2026-09-30"}).data["totals"]["net"], "700.00")
        self.assertEqual(Transaction.objects.get(pk=self.receipt.pk).rmb_amount, Decimal("999.9999"))

    def test_report_center_actual_source_and_csv_share_same_amounts(self):
        self._confirmed(payload([self.receipt], key="ACTUAL-REPORT", bank_date="2026-09-30", bank_net_amount="705.00", fee_mode="included", fee_amount="5.00"))
        response = self.client.get("/api/reports/data/", {"source": "actual_cash", "group_by": "direction", "date_field": "bank_date", "date_from": "2026-09-01", "date_to": "2026-09-30"})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["basis"], "bank_cash_confirmed_v1")
        self.assertEqual(response.data["totals"]["amount"], Decimal("705.00"))
        csv_response = self.client.get("/api/reports/data/", {"source": "actual_cash", "group_by": "direction", "date_field": "bank_date", "date_from": "2026-09-01", "date_to": "2026-09-30", "export": "csv"})
        self.assertEqual(csv_response.status_code, 200)
        csv_text = csv_response.content.decode("utf-8-sig")
        self.assertIn("金额（银行实际人民币净额）", csv_text)
        self.assertIn("705.00", csv_text)
