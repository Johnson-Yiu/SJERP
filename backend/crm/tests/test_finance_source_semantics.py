from datetime import date
from decimal import Decimal

from django.test import TestCase
from rest_framework.exceptions import APIException
from rest_framework.test import APIClient

from crm.models import FinanceFact
from crm.services import finance_closeout as ledger
from crm.tests.test_finance_closeout import CloseoutFixture


class FinanceSourceSemanticsTests(CloseoutFixture, TestCase):
    def setUp(self):
        self.setup_ledger()
        self.client = APIClient()
        self.client.force_authenticate(self.maker)
        self.period = {"date_from": "2026-01-01", "date_to": "2026-01-31"}

    def finance_snapshot(self):
        actual = self.client.get("/api/actual-rmb-cash/", self.period)
        self.assertEqual(actual.status_code, 200, actual.data)
        facts = self.client.get("/api/finance-ledger/facts/", self.period)
        self.assertEqual(facts.status_code, 200, facts.data)
        report = self.client.get("/api/reports/data/", {
            **self.period, "source": "actual_cash", "group_by": "direction",
        })
        self.assertEqual(report.status_code, 200, report.data)
        return {
            "fact_count": FinanceFact.objects.count(),
            "balance": ledger.balance(self.account, self.period["date_to"]),
            "events": sorted(
                (row.pk, row.direction, row.bank_net_amount)
                for row in ledger.reporting_events(self.maker, self.period["date_from"], self.period["date_to"])
            ),
            "actual_totals": actual.data["totals"],
            "ledger_totals": facts.data["totals"],
            "report_totals": report.data["totals"],
        }

    def test_pending_and_simulated_commands_cannot_change_financial_statistics(self):
        self.fact(kind="opening", actual_date="2026-01-01", amount="1000.00")
        self.fact(actual_date="2026-01-02", amount="125.00")
        before = self.finance_snapshot()

        for truth in ("needs_verification", "simulated"):
            with self.subTest(truth=truth):
                instruction, created = ledger.submit(
                    self.data(truth=truth, actual_date="2026-01-10", amount="999.00"),
                    self.maker,
                )
                self.assertTrue(created)
                self.assertEqual(instruction.status, "pending")
                with self.assertRaises(APIException):
                    ledger.approve(instruction.pk, self.reviewer)
                with self.assertRaises(APIException):
                    ledger.post(instruction.pk, self.maker, voucher_checked=True)
                instruction.refresh_from_db()
                self.assertEqual(instruction.status, "pending")
                self.assertEqual(self.finance_snapshot(), before)

    def test_effective_correction_transfer_principal_and_independent_fee_accounting(self):
        self.fact(kind="opening", actual_date="2026-01-01", amount="1000.00")
        original = self.fact(actual_date="2026-01-02", amount="100.00")
        correction = self.fact(
            kind="correction", parent=original.pk,
            actual_date="2026-01-04", amount="90.00", direction="income",
        )
        outgoing = self.fact(
            actual_date="2026-01-06", amount="40.00", direction="expense",
            nature="internal_principal",
        )
        incoming = self.fact(
            account=self.second.pk, actual_date="2026-01-07", amount="40.00",
            direction="income", nature="internal_principal",
        )
        fee = self.fact(
            actual_date="2026-01-07", amount="3.00", direction="expense",
            nature="bank_fee",
        )

        before_match = ledger.reporting_events(
            self.maker, self.period["date_from"], self.period["date_to"]
        )
        before_ids = {row.pk for row in before_match}
        self.assertIn(-outgoing.pk, before_ids)
        self.assertIn(-incoming.pk, before_ids)
        self.assertIn(-fee.pk, before_ids)

        ledger.match_transfer({
            "outgoing": outgoing.pk, "incoming": incoming.pk,
            "reason": "隔离合成两端银行凭证已核对",
        }, self.maker)

        original.refresh_from_db()
        self.assertEqual(original.amount, Decimal("100.00"))
        events = ledger.reporting_events(
            self.maker, self.period["date_from"], self.period["date_to"]
        )
        self.assertCountEqual(
            [(row.pk, row.direction, row.bank_net_amount) for row in events],
            [(-correction.pk, "income", Decimal("90.00")),
             (-fee.pk, "expense", Decimal("3.00"))],
        )
        self.assertEqual(
            ledger.balance(self.account, date(2026, 1, 31))[0],
            Decimal("1047.00"),
        )

        actual = self.client.get("/api/actual-rmb-cash/", self.period)
        self.assertEqual(actual.status_code, 200, actual.data)
        self.assertEqual(actual.data["totals"]["inflow"], "90.00")
        self.assertEqual(actual.data["totals"]["outflow"], "3.00")
        self.assertEqual(actual.data["totals"]["net"], "87.00")

        facts = self.client.get("/api/finance-ledger/facts/", self.period)
        self.assertEqual(facts.status_code, 200, facts.data)
        transfer_rows = [
            row for row in facts.data["facts"]
            if row["id"] in {outgoing.pk, incoming.pk}
        ]
        self.assertEqual(len(transfer_rows), 2)
        self.assertTrue(all(not row["company_flow_included"] for row in transfer_rows))
        self.assertEqual(facts.data["totals"]["inflow"], "90.00")
        self.assertEqual(facts.data["totals"]["outflow"], "3.00")
