from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal as D
import hashlib
import json
from threading import Barrier
import unittest
from unittest.mock import patch

from django.apps import apps
from django.contrib.auth.models import AnonymousUser
from django.core.serializers.json import DjangoJSONEncoder
from django.db import connection, close_old_connections, connections
from django.test import TestCase, TransactionTestCase, override_settings
from rest_framework.exceptions import APIException
from rest_framework.test import APIClient

from crm.models import CashSourceAllocation, Customer, Order, PaymentPlan, Product, RmbCashEvent, SKU, Transaction
from crm.services import cash_events as cash
from crm.services.finance import allocate_advance, record_contract_refund, record_transaction, void_transaction
from crm.tests import test_finance_data_scope as scope_fixture

ACCOUNTS = ("SYNTH_FX", "SYNTH_CNY")
URL = "/api/rmb-cash-events/"


def legacy_hash():
    data = {m.__name__: list(m.objects.order_by("pk").values()) for m in apps.get_app_config("crm").get_models() if m not in {RmbCashEvent, CashSourceAllocation}}
    return hashlib.sha256(json.dumps(data, sort_keys=True, cls=DjangoJSONEncoder).encode()).hexdigest()


def payload(rows, amounts=None, key="BANK-1", currency="USD", **changes):
    amounts = amounts or [format(r.amount, ".0f" if currency == "JPY" else ".2f") for r in rows]
    p = dict(event_no=key, request_key=key, kind="fx_settlement", currency=currency, direction="income", bank_date="2026-10-18", bank_net_amount="705.00", fee_mode="included", fee_amount="5.00", source_account="SYNTH_FX", rmb_account="SYNTH_CNY", bank_reference="SYNTH-BANK-REF", evidence_reference="SYNTH-VOUCHER", evidence_sha256="a" * 64, evidence_note="合成银行凭证人工核实", quoted_rate="7.100000", sources=[dict(transaction_id=r.pk, amount=a, verified=True) for r, a in zip(rows, amounts)])
    p.update(changes)
    return p


class CashFixture:
    def setup_cash(self):
        self.client = APIClient()
        self.user = AnonymousUser()
        self.customer = Customer.objects.create(code="BANK-C", name="Synthetic customer")
        self.order = Order.objects.create(order_no="BANK-O", customer=self.customer, currency="USD", exchange_rate=7, status="confirmed", order_date=date(2026, 10, 18))
        self.sku = SKU.objects.create(sku="BANK-SKU", product=Product.objects.create(code="BANK-P", name="Synthetic product"))
        self.order.items.create(sku=self.sku, quantity=1, unit_price=100)
        self.plan = PaymentPlan.objects.create(order=self.order, direction="receivable", currency="USD", planned_amount=100)
        self.receipt = record_transaction(dict(transaction_no="BANK-T", plan=self.plan, amount="100", exchange_rate="7", currency="USD"))

    def register(self, p):
        r = self.client.post(URL, p, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        return r.data["id"]

    def confirm(self, pk, expected=200, **body):
        r = self.client.post(f"{URL}{pk}/confirm/", body or {"voucher_checked": True}, format="json")
        self.assertEqual(r.status_code, expected, r.data)
        return r


@override_settings(RMB_CASH_ACCOUNT_IDS=ACCOUNTS)
class CashEventTests(CashFixture, TestCase):
    def setUp(self):
        self.setup_cash()

    def test_a_b_unconverted_then_bank_net_confirmed_without_legacy_writes(self):
        self.assertEqual(RmbCashEvent.objects.count(), 0)
        before = legacy_hash()
        old_report = self.client.get("/api/finance-dashboard/").data
        p = payload([self.receipt])
        preview = self.client.post(URL + "preview/", p, format="json")
        self.assertEqual(preview.status_code, 200, preview.data)
        self.assertEqual(RmbCashEvent.objects.count(), 0)
        pk = self.register(p)
        self.assertEqual(cash.available(self.receipt), D("100"))
        r = self.confirm(pk)
        self.assertEqual(D(r.data["bank_net_amount"]), D("705"))
        self.assertEqual(D(r.data["fee_amount"]), D("5"))
        self.assertEqual(cash.available(self.receipt), 0)
        self.assertEqual(r.data["created_actor"]["kind"], "development_superadmin")
        self.assertIsNone(r.data["coverage_since"])
        self.assertEqual(before, legacy_hash())
        self.assertEqual(old_report, self.client.get("/api/finance-dashboard/").data)
        print("P2A-DATABASE_VERIFICATION", json.dumps({"before": before, "after": legacy_hash(), "bank_net": "705.00", "included_fee": "5.00", "source_used": "100.0000", "legacy_unchanged": True}))

    def test_c_partial_60_40_and_overallocation(self):
        for n, amount in enumerate(["60", "40"]):
            pk = self.register(payload([self.receipt], [amount], key=f"PART-{n}"))
            self.confirm(pk)
        count = RmbCashEvent.objects.count()
        r = self.client.post(URL, payload([self.receipt], ["0.01"], key="OVER"), format="json")
        self.assertEqual(r.status_code, 409)
        self.assertEqual(RmbCashEvent.objects.count(), count)
        self.assertEqual(sum(CashSourceAllocation.objects.values_list("amount", flat=True)), D("100"))

    def test_d_split_family_is_cash_rows_not_root_total(self):
        order = Order.objects.create(order_no="SPLIT-O", customer=self.customer, currency="USD", exchange_rate=7, status="confirmed", order_date=date(2026, 10, 18))
        order.items.create(sku=self.sku, quantity=1, unit_price=100)
        for amount in [30, 70]: PaymentPlan.objects.create(order=order, direction="receivable", currency="USD", planned_amount=amount)
        root = record_transaction(dict(transaction_no="SPLIT-T", order=order, customer=self.customer, amount="100", currency="USD", exchange_rate="7", kind="customer_receipt"))
        extra = root.split_rows.get()
        self.assertEqual(root.amount, D("30")); self.assertEqual(extra.amount, D("70"))
        bad = payload([root, extra], ["100", "70"])
        self.assertEqual(self.client.post(URL, bad, format="json").status_code, 409)
        pk = self.register(payload([root, extra]))
        self.confirm(pk)
        self.assertEqual(RmbCashEvent.objects.get(pk=pk).amount, D("100"))
        self.assertEqual(CashSourceAllocation.objects.count(), 2)
        self.assertEqual(self.client.post(URL, payload([self.receipt, self.receipt], ["10", "10"], key="DUP"), format="json").status_code, 400)

    def test_advance_allocation_does_not_consume_cash_source(self):
        source = record_transaction(dict(transaction_no="ADV-BANK", kind="unallocated_advance", direction="income", customer=self.customer, amount="100", currency="USD", exchange_rate="7", category="合成预收"))
        plan = PaymentPlan.objects.create(order=self.order, direction="receivable", currency="USD", planned_amount=100)
        allocate_advance(source, plan, "100")
        source.refresh_from_db()
        self.assertEqual(source.allocated_amount, 100)
        before = legacy_hash()
        self.confirm(self.register(payload([source])))
        self.assertEqual(before, legacy_hash())

    def test_e_separate_fee_uses_independent_cny_source_and_no_double_included_fee(self):
        parent = self.register(payload([self.receipt])); self.confirm(parent)
        fee = record_transaction(dict(transaction_no="FEE-T", kind="bank_fee", direction="expense", category="银行手续费", amount="5", currency="CNY", exchange_rate="1"))
        p = payload([fee], key="FEE-1", currency="CNY", kind="bank_fee", direction="expense", bank_net_amount="5", fee_mode="none", fee_amount="0", quoted_rate=None, fee_for=parent)
        self.assertEqual(self.client.post(URL, p, format="json").status_code, 400)
        other = record_transaction(dict(transaction_no="FX-OTHER", kind="other_income", direction="income", category="合成", amount="100", currency="USD", exchange_rate="7"))
        parent2 = self.register(payload([other], key="GROSS", bank_net_amount="710", fee_mode="none", fee_amount="0")); self.confirm(parent2)
        p.update(fee_for=parent2)
        before = legacy_hash(); self.confirm(self.register(p)); self.assertEqual(before, legacy_hash())
        self.assertEqual(sum(e.bank_net_amount if e.direction == "income" else -e.bank_net_amount for e in RmbCashEvent.objects.filter(pk__in=[parent2, RmbCashEvent.objects.get(request_key="FEE-1").pk])), D("705"))

    def test_f_cny_direct_identical_amounts_are_distinct_real_events(self):
        for direction in ("income", "expense"):
            source = record_transaction(dict(transaction_no="CNY-" + direction, kind="other", direction=direction, category="合成", amount="200", currency="CNY", exchange_rate="1"))
            for n in range(2):
                self.confirm(self.register(payload([source], ["100"], key=f"CNY-{direction}-{n}", currency="CNY", kind="cny_direct", direction=direction, bank_net_amount="100", fee_mode="none", fee_amount="0", quoted_rate=None)))
        self.assertEqual(RmbCashEvent.objects.filter(status="confirmed").count(), 4)

    def test_g_missing_voucher_account_and_manual_check_fail_without_writes(self):
        pk = self.register(payload([self.receipt], evidence_reference="", evidence_sha256="", evidence_note=""))
        before = legacy_hash(); self.confirm(pk, 400); self.assertEqual(before, legacy_hash())
        self.assertEqual(RmbCashEvent.objects.get(pk=pk).status, "pending")
        good = self.register(payload([self.receipt], key="GOOD"))
        self.confirm(good, 400, voucher_checked=False)
        with override_settings(RMB_CASH_ACCOUNT_IDS=()): self.confirm(good, 400)
        self.assertEqual(cash.available(self.receipt), D("100"))
        self.confirm(good)

    def test_h_refund_void_and_correction_protection_are_atomic(self):
        pk = self.register(payload([self.receipt])); self.confirm(pk)
        before = legacy_hash()
        for function in (lambda: void_transaction(self.receipt, "合成作废"), lambda: record_contract_refund(self.order, {"amount": "10", "currency": "USD"})):
            with self.assertRaises(APIException): function()
            self.assertEqual(before, legacy_hash())
        with self.assertRaises(APIException):
            record_transaction(dict(transaction_no="UNSAFE-REPLACE", replaces=self.receipt, kind="other_income", direction="income", category="合成", amount="100", currency="USD", exchange_rate="7"))
        self.assertEqual(before, legacy_hash())
        self.assertEqual(self.client.post(f"{URL}{pk}/cancel/", {"reason": "不能撤销事实"}, format="json").status_code, 400)
        self.assertEqual(self.client.post(URL, payload([self.receipt], key="CORR", correction_of=pk), format="json").status_code, 400)
        self.assertEqual(cash.available(self.receipt), 0)
        event = RmbCashEvent.objects.get(pk=pk); event.bank_net_amount = D("1")
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError): event.save()
        with self.assertRaises(ValidationError): event.delete()
        a = event.sources.get(); a.amount = D("1")
        with self.assertRaises(ValidationError): a.save()
        self.assertEqual(RmbCashEvent.objects.get(pk=pk).bank_net_amount, D("705"))

    def test_unrelated_refunds_remain_legal_and_unknown_refunds_block_preview(self):
        self.confirm(self.register(payload([self.receipt])))
        other = Customer.objects.create(code="OTHER", name="Other synthetic")
        order = Order.objects.create(order_no="OTHER-O", customer=other, currency="USD", exchange_rate=7, status="confirmed", order_date=date(2026, 10, 18))
        order.items.create(sku=self.sku, quantity=1, unit_price=100)
        p = PaymentPlan.objects.create(order=order, direction="receivable", currency="USD", planned_amount=100)
        receipt = record_transaction(dict(transaction_no="OTHER-T", plan=p, amount="100", exchange_rate="7", currency="USD"))
        refund = record_contract_refund(order, {"amount": "10", "currency": "USD"})
        void_transaction(refund, "作废业务退款不证明银行资金已经退回")
        r = self.client.post(URL + "preview/", payload([receipt], key="UNKNOWN"), format="json")
        self.assertEqual(r.status_code, 400)
        sources = self.client.get(URL + "sources/?currency=USD").data["results"]
        self.assertIsNone(next(s for s in sources if s["id"] == receipt.pk)["remaining_candidate_amount"])

    def test_i_idempotency_lookup_conflict_cancel_and_immutable_confirm_payload(self):
        p = payload([self.receipt]); pk = self.register(p)
        retry = self.client.post(URL, p, format="json"); self.assertEqual(retry.status_code, 200); self.assertEqual(retry.data["id"], pk)
        different = dict(p, bank_net_amount="706")
        self.assertEqual(self.client.post(URL, different, format="json").status_code, 409)
        self.confirm(pk, 400, voucher_checked=True, bank_net_amount="1")
        self.confirm(pk); self.confirm(pk)
        self.assertEqual(self.client.get(URL + "by-request-key/", {"request_key": p["request_key"]}).data["status"], "confirmed")
        self.assertEqual(RmbCashEvent.objects.count(), 1); self.assertEqual(CashSourceAllocation.objects.count(), 1)
        for method in (self.client.patch, self.client.put, self.client.delete): self.assertEqual(method(f"{URL}{pk}/", {}, format="json").status_code, 405)

    def test_cancel_pending_retains_evidence_and_allows_original_void(self):
        pk = self.register(payload([self.receipt]))
        with self.assertRaises(APIException): void_transaction(self.receipt, "待确认关联")
        r = self.client.post(f"{URL}{pk}/cancel/", {"reason": "凭证录入错误，放弃草稿"}, format="json")
        self.assertEqual(r.status_code, 200)
        void_transaction(self.receipt, "已放弃草稿")
        self.assertEqual(RmbCashEvent.objects.get(pk=pk).evidence_sha256, "a" * 64)
        self.confirm(pk, 400)

    def test_failure_after_event_creation_rolls_back_both_tables(self):
        with patch.object(CashSourceAllocation.objects, "create", side_effect=RuntimeError("synthetic failure")):
            with self.assertRaises(RuntimeError): cash.register_event(payload([self.receipt]), self.user)
        self.assertEqual(RmbCashEvent.objects.count(), 0); self.assertEqual(CashSourceAllocation.objects.count(), 0)

    def test_k_invalid_money_rate_sources_and_unknown_fields(self):
        for field, values in {"bank_net_amount": ["NaN", "Infinity", "-1", "0", "0.001", "1.000", "1000000000000", 1.5, True], "quoted_rate": ["NaN", "Infinity", "-1", "1.0000001", "1.0000000"], "currency": ["XYZ", [], {}], "kind": [[], {}], "direction": [[], {}], "fee_amount": ["-1", "0.001"], "fee_mode": ["separate", [], {}]}.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    self.assertEqual(self.client.post(URL, payload([self.receipt], **{field: value}), format="json").status_code, 400)
        self.assertEqual(self.client.post(URL, payload([self.receipt], password="forbidden"), format="json").status_code, 400)
        p = payload([self.receipt]); p["sources"][0]["verified"] = False
        self.assertEqual(self.client.post(URL, p, format="json").status_code, 400)
        self.assertEqual(RmbCashEvent.objects.count(), 0)

    def test_mixed_currency_stale_snapshot_and_event_number_conflict(self):
        pk = self.register(payload([self.receipt]))
        # Independent fixture mutation simulates unsupported historical source editing.
        Transaction.objects.filter(pk=self.receipt.pk).update(exchange_rate=D("7.1"))
        self.confirm(pk, 400)
        self.assertEqual(RmbCashEvent.objects.get(pk=pk).status, "pending")
        self.assertEqual(self.client.post(URL, payload([self.receipt], key="OTHER-KEY", event_no="BANK-1"), format="json").status_code, 409)
        p = payload([self.receipt], currency="EUR", key="MIXED")
        self.assertEqual(self.client.post(URL, p, format="json").status_code, 400)
        self.assertEqual(self.client.get(URL + "not-an-id/").status_code, 404)

    def test_confirm_failure_after_status_update_is_rolled_back(self):
        pk = self.register(payload([self.receipt]))
        save = RmbCashEvent.save
        def fail(instance, *args, **kwargs):
            save(instance, *args, **kwargs)
            raise RuntimeError("synthetic failure after status write")
        before = legacy_hash()
        with patch.object(RmbCashEvent, "save", fail):
            with self.assertRaises(RuntimeError): cash.confirm_event(pk, self.user, voucher_checked=True)
        self.assertEqual(RmbCashEvent.objects.get(pk=pk).status, "pending")
        self.assertEqual(cash.available(self.receipt), D("100")); self.assertEqual(before, legacy_hash())

    def test_legacy_contract_only_party_is_protected_and_snapshot_owner_cannot_leak(self):
        source = record_transaction(dict(transaction_no="LEGACY-CONTRACT-ONLY", kind="other_income", direction="income", category="合成", amount="100", currency="USD", exchange_rate="7", order=self.order))
        self.assertIsNone(source.customer_id)
        self.confirm(self.register(payload([source])))
        with self.assertRaises(APIException): record_contract_refund(self.order, {"amount": "10", "currency": "USD"})

    def test_l_historical_fraction_jpy_precision_and_reference_round_half_up(self):
        for currency, amount, accepted, rejected in [("USD", "100.0001", "100.00", "0.0001"), ("JPY", "100.1234", "100", "0.1")]:
            source = Transaction.objects.create(transaction_no="OLD-" + currency, amount=D(amount), currency=currency, direction="income", kind="other_income", exchange_rate=D("0.010050"), transaction_date=date(2026, 10, 18))
            before = legacy_hash()
            pk = self.register(payload([source], [accepted], key="PREC-" + currency, currency=currency))
            self.confirm(pk)
            self.assertEqual(before, legacy_hash())
            self.assertEqual(cash.available(source), D(amount) - D(accepted))
            self.assertEqual(self.client.post(URL, payload([source], [rejected], key="BAD-" + currency, currency=currency), format="json").status_code, 400)
            self.assertEqual(self.client.get(f"{URL}{pk}/").data["reference_amount"], "1.01")


@override_settings(**scope_fixture.RBAC_SETTINGS, RMB_CASH_ACCOUNT_IDS=ACCOUNTS, PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class CashPermissionsTests(TestCase):
    make_employee = scope_fixture.FinanceDataScopeTests.make_employee

    def setUp(self):
        scope_fixture.FinanceDataScopeTests.setUp(self)

    def test_k_merged_batch_hidden_entirely_and_all_actions_scoped(self):
        self.client.force_authenticate(self.all_user.user)
        p = payload(self.receipts[:2], key="MERGED", currency="CNY", kind="cny_direct", bank_net_amount="20", fee_mode="none", fee_amount="0", quoted_rate=None)
        r = self.client.post(URL, p, format="json"); self.assertEqual(r.status_code, 201, r.data); pk = r.data["id"]
        self.client.force_authenticate(self.employee_a.user)
        for path in (f"{URL}{pk}/", URL + "by-request-key/?request_key=MERGED"):
            response = self.client.get(path); self.assertEqual(response.status_code, 404); self.assertNotIn("bank_net_amount", response.data)
        self.assertEqual(self.client.get(URL).data["results"], [])
        self.assertEqual(self.client.post(f"{URL}{pk}/confirm/", {"voucher_checked": True}, format="json").status_code, 404)
        self.assertEqual(self.client.post(URL + "preview/", p, format="json").status_code, 404)
        self.assertEqual(self.client.post(URL, p, format="json").status_code, 404)
        self.assertEqual(self.client.post(f"{URL}{pk}/cancel/", {"reason": "not visible"}, format="json").status_code, 404)
        ids = {r["id"] for r in self.client.get(URL + "sources/").data["results"]}
        self.assertNotIn(self.receipts[1].pk, ids)

    def test_no_finance_or_transaction_view_no_amounts_and_write_rights(self):
        from crm.models import RolePermission
        for module in ("finance", "transactions"):
            RolePermission.objects.filter(role=self.roles["self"], module=module).update(can_view=False)
            for path in (URL, URL + "sources/", URL + "by-request-key/?request_key=ANY"):
                r = self.client.get(path); self.assertEqual(r.status_code, 403); self.assertNotIn("amount", r.data)
            RolePermission.objects.filter(role=self.roles["self"], module=module).update(can_view=True)
        RolePermission.objects.filter(role=self.roles["self"], module="finance").update(can_create=False)
        p = payload([self.receipts[0]], currency="CNY", kind="cny_direct", bank_net_amount="10", fee_mode="none", fee_amount="0", quoted_rate=None)
        self.assertEqual(self.client.post(URL, p, format="json").status_code, 403)
        RolePermission.objects.filter(role=self.roles["self"], module="finance").update(can_create=True)
        r = self.client.post(URL, p, format="json"); self.assertEqual(r.status_code, 201, r.data)
        RolePermission.objects.filter(role=self.roles["self"], module="finance").update(can_update=False)
        self.assertEqual(self.client.post(f"{URL}{r.data['id']}/confirm/", {"voucher_checked": True}, format="json").status_code, 403)

    def test_missing_contract_module_hides_whole_source_family(self):
        from crm.models import RolePermission
        source = Transaction.objects.create(transaction_no="HIDDEN-FAMILY-ADVANCE", amount=5, currency="CNY", direction="income", kind="unallocated_advance", customer=self.customer_a, transaction_date=date(2026, 10, 18), split_from=self.receipts[0])
        RolePermission.objects.filter(role=self.roles["self"], module="orders").update(can_view=False)
        ids = {r["id"] for r in self.client.get(URL + "sources/").data["results"]}
        self.assertNotIn(source.pk, ids); self.assertNotIn(self.receipts[0].pk, ids)


@unittest.skipUnless(connection.vendor == "postgresql", "Real PostgreSQL locks required")
@override_settings(RMB_CASH_ACCOUNT_IDS=ACCOUNTS)
class CashConcurrencyTests(CashFixture, TransactionTestCase):
    def setUp(self): self.setup_cash()

    def race(self, fn):
        barrier = Barrier(2)
        def work(index):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return fn(index)
            finally: connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool: return list(pool.map(work, range(2)))

    def test_j_different_keys_compete_for_same_source(self):
        ids = [cash.register_event(payload([self.receipt], ["60"], key=f"RACE-{n}"), self.user)[0].pk for n in range(2)]
        def action(n):
            try: cash.confirm_event(ids[n], self.user, voucher_checked=True); return "confirmed"
            except cash.CashConflict: return "conflict"
        results = self.race(action)
        self.assertCountEqual(results, ["confirmed", "conflict"])
        self.assertEqual(RmbCashEvent.objects.filter(status="confirmed").count(), 1)
        self.assertEqual(cash.available(self.receipt), D("40"))
        print("P2A_REAL_POSTGRES_CONCURRENCY", json.dumps({"case": "different_keys_shared_source", "results": results, "source": "100.0000", "confirmed_usage": "60.0000", "remaining": "40.0000", "vendor": connection.vendor}))

    def test_i_concurrent_same_request_creates_one_event_and_one_allocation(self):
        p = payload([self.receipt])
        ids = self.race(lambda n: cash.register_event(p, self.user)[0].pk)
        self.assertEqual(ids[0], ids[1]); self.assertEqual(RmbCashEvent.objects.count(), 1); self.assertEqual(CashSourceAllocation.objects.count(), 1)
        results = self.race(lambda n: cash.confirm_event(ids[n], self.user, voucher_checked=True).pk)
        self.assertEqual(results, ids); self.assertEqual(cash.available(self.receipt), 0)
        print("P2A_REAL_POSTGRES_CONCURRENCY", json.dumps({"case": "same_request_and_confirm", "one_event": True, "one_allocation": True, "vendor": connection.vendor}))

    def test_h_confirm_races_void_and_refund_never_releases_or_changes_legacy(self):
        pk = cash.register_event(payload([self.receipt]), self.user)[0].pk
        before = legacy_hash()
        def action(n):
            if n == 0: cash.confirm_event(pk, self.user, voucher_checked=True); return "confirmed"
            try: void_transaction(self.receipt, "race"); return "unsafe_void"
            except APIException: return "void_rejected"
        self.assertCountEqual(self.race(action), ["confirmed", "void_rejected"])
        def refund(n):
            if n == 0: cash.confirm_event(pk, self.user, voucher_checked=True); return "idempotent"
            try: record_contract_refund(self.order, {"amount": "10", "currency": "USD"}); return "unsafe_refund"
            except APIException: return "refund_rejected"
        self.assertCountEqual(self.race(refund), ["idempotent", "refund_rejected"])
        self.assertEqual(before, legacy_hash())
        print("P2A_REAL_POSTGRES_CONCURRENCY", json.dumps({"case": "confirm_void_refund", "legacy_unchanged": True, "remaining": "0.0000", "vendor": connection.vendor}))


class CashMigrationTests(TransactionTestCase):
    def test_additive_migration_preserves_historical_rows_and_decimal_fields(self):
        from django.db.migrations.executor import MigrationExecutor
        executor = MigrationExecutor(connection)
        latest_targets = [node for node in executor.loader.graph.leaf_nodes() if node[0] == "crm"]
        executor.migrate([("crm", "0076_customer_owner_profile")])
        try:
            before_state = executor.loader.project_state([("crm", "0076_customer_owner_profile")]).apps
            old = before_state.get_model("crm", "Transaction")
            old.objects.create(transaction_no="LEGACY-FOUR", transaction_date=date(2026, 10, 1), direction="income", kind="other_income", category="Synthetic", amount=D("12.3401"), currency="USD", exchange_rate=D("7.123456"), rmb_amount=D("87.9034"), allocated_amount=D("0.0001"))
            before = {m.__name__: list(m.objects.order_by("pk").values()) for m in before_state.get_app_config("crm").get_models()}
            executor = MigrationExecutor(connection)
            executor.migrate([("crm", "0077_rmb_cash_events")])
            # Query the historical 0077 app registry.  The live registry also
            # contains fields/models introduced by later migrations (for
            # example Order.quantity_change_version in 0078), which do not
            # exist in the database while this comparison is running.
            after_state = executor.loader.project_state([("crm", "0077_rmb_cash_events")]).apps
            after = {
                m.__name__: list(m.objects.order_by("pk").values())
                for m in after_state.get_app_config("crm").get_models()
                if m.__name__ not in {"RmbCashEvent", "CashSourceAllocation"}
            }
            self.assertEqual(before, after)
            self.assertEqual(Transaction._meta.get_field("amount").decimal_places, 4)
            self.assertEqual(Transaction._meta.get_field("rmb_amount").decimal_places, 4)
            self.assertEqual(PaymentPlan._meta.get_field("settled_amount").decimal_places, 4)
            self.assertEqual(RmbCashEvent.objects.count(), 0); self.assertEqual(CashSourceAllocation.objects.count(), 0)
            print("P2A_MIGRATION_VERIFICATION", json.dumps({"vendor": connection.vendor, "all_legacy_rows_equal": True, "old_amount": "12.3401", "old_rmb": "87.9034", "old_allocated": "0.0001", "new_bank_facts": 0}))
        finally:
            MigrationExecutor(connection).migrate(latest_targets)
