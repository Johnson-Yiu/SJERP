"""Read-only code audit probes; writes only Django's disposable test database."""
import json
from decimal import Decimal

from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model

from crm.models import OperationLog, RmbCashEvent
from crm.services.finance import record_transaction
from crm.tests.test_cash_events import ACCOUNTS, CashFixture, payload


@override_settings(RMB_CASH_ACCOUNT_IDS=ACCOUNTS)
class AuditProbes(CashFixture, TestCase):
    def setUp(self):
        self.setup_cash()

    def cny_payload(self, source, key, amount="100", **changes):
        return payload([source], [amount], key=key, currency="CNY",
                       kind="cny_direct", direction=source.direction,
                       bank_net_amount=amount, fee_mode="none", fee_amount="0",
                       quoted_rate=None, **changes)

    def source(self, number, amount="100", direction="income", kind="other"):
        return record_transaction(dict(transaction_no=number, kind=kind,
                                       direction=direction, category="合成审查数据",
                                       amount=amount, currency="CNY", exchange_rate="1"))

    def totals(self):
        response = self.client.get("/api/actual-rmb-cash/", {
            "date_from": "2026-10-01", "date_to": "2026-10-31"})
        self.assertEqual(response.status_code, 200, response.data)
        return response.data["totals"]

    def test_same_bank_fact_different_request_keys_is_not_deduplicated(self):
        source = self.source("AUDIT-DUP", amount="200")
        for key in ("AUDIT-DUP-1", "AUDIT-DUP-2"):
            self.confirm(self.register(self.cny_payload(source, key)))
        self.assertEqual(RmbCashEvent.objects.filter(status="confirmed").count(), 2)
        self.assertEqual(Decimal(self.totals()["inflow"]), Decimal("200"))
        print("AUDIT-DUPLICATE", json.dumps({"same_source": source.pk,
            "same_bank_reference": "SYNTH-BANK-REF", "same_accounts_date_amount": True,
            "distinct_request_keys": True, "confirmed_events": 2, "totals": self.totals()}))

    def test_intended_internal_transfer_has_no_supported_exclusion(self):
        for direction in ("income", "expense"):
            source = self.source("AUDIT-TRANSFER-" + direction, direction=direction)
            self.confirm(self.register(self.cny_payload(source, "AUDIT-TRANSFER-" + direction)))
        totals = self.totals()
        self.assertEqual(Decimal(totals["inflow"]), Decimal("100"))
        self.assertEqual(Decimal(totals["outflow"]), Decimal("100"))
        self.assertEqual(Decimal(totals["net"]), Decimal("0"))
        print("AUDIT-INTERNAL-TRANSFER-REPRESENTED-AS-DIRECT", json.dumps(totals))

    def test_independent_bank_fee_api_does_not_require_fx_parent(self):
        source = self.source("AUDIT-FEE", amount="5", direction="expense", kind="bank_fee")
        p = self.cny_payload(source, "AUDIT-FEE", amount="5")
        p["kind"] = "bank_fee"
        self.confirm(self.register(p))
        event = RmbCashEvent.objects.get(request_key="AUDIT-FEE")
        self.assertIsNone(event.fee_for_id)
        self.assertEqual(Decimal(self.totals()["outflow"]), Decimal("5"))
        print("AUDIT-INDEPENDENT-FEE", json.dumps({"fee_for": None,
              "create_http": 201, "confirm_http": 200, "totals": self.totals()}))

    def test_unknown_classification_and_opening_balance_have_no_supported_kind(self):
        source = self.source("AUDIT-UNKNOWN")
        for kind in ("unknown", "internal_transfer", "opening_balance"):
            p = self.cny_payload(source, "AUDIT-" + kind)
            p["kind"] = kind
            response = self.client.post("/api/rmb-cash-events/", p, format="json")
            self.assertEqual(response.status_code, 400, response.data)
            print("AUDIT-UNSUPPORTED-KIND", json.dumps({"kind": kind,
                "status": response.status_code, "error": str(response.data)}, ensure_ascii=False))
        self.assertEqual(RmbCashEvent.objects.count(), 0)

    @override_settings(AUDIT_LOG_ENABLED=True)
    def test_authenticated_cash_actions_do_not_create_operation_log(self):
        user = get_user_model().objects.create_user(username="synthetic-auditor")
        self.client.force_authenticate(user)
        before = OperationLog.objects.count()
        source = self.source("AUDIT-LOG")
        pk = self.register(self.cny_payload(source, "AUDIT-LOG"))
        self.confirm(pk)
        self.assertEqual(OperationLog.objects.count(), before)
        event = RmbCashEvent.objects.get(pk=pk)
        self.assertTrue(event.created_actor)
        self.assertTrue(event.confirmed_actor)
        print("AUDIT-OPERATION-LOG", json.dumps({"authenticated": True,
              "audit_enabled": True, "operation_log_delta": 0,
              "event_actor_snapshots_present": True}))
