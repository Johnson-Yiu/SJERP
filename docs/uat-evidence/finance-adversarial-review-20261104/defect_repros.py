"""Explicit failing business-rule reproductions, not fixed by this review.

Run manage.py test defect_repros with this directory on PYTHONPATH.
These assertions deliberately stay unchanged until coordinated product fixes.
Normal CI success is NOT acceptance of these known defects.
"""
from django.test import TestCase
from crm.tests.test_finance_adversarial_review import AdversarialFixture
from crm.tests import test_finance_adversarial_review as probes
from django.test import override_settings


class ConfirmedDefectReproductions(AdversarialFixture, TestCase):
    def setUp(self):
        self.setup_adversarial()

    def test_adv01_effective_expense_classification_must_not_be_hidden_as_internal_principal(self):
        out = self.fact(direction="expense", amount="47.00", nature="internal_principal")
        inc = self.fact(account=self.cash, amount="47.00", nature="internal_principal", actual_date="2026-04-05")
        self.api("classifications", {"fact": out["id"], "nature": "expense", "reason": "合成核实为对外支出，不是内部本金"}, 201)
        detail = self.api("fact_detail", {"id": out["id"]}, method="get")
        self.assertEqual(detail["nature"], "expense")
        payload = {"outgoing": out["id"], "incoming": inc["id"], "reason": "反例：不能用原性质覆盖已核实分类"}
        response = self.client.post("/api/finance-ledger/transfers/", payload, format="json")
        self.records.append({"path": "/api/finance-ledger/transfers/", "request": payload, "status": response.status_code, "body": response.data})
        self.actual()
        self.facts()
        csv = self.client.get("/api/finance-ledger/facts/", {"export": "csv"})
        self.records.append({"path": "/api/finance-ledger/facts/?export=csv", "csv": csv.content.decode("utf-8-sig")})
        self.assertEqual(response.status_code, 400, response.data)
        self.assert_surfaces("47", "47")

    def test_adv02_internal_pairing_after_completed_reconciliation_requires_new_review(self):
        self.fact(kind="opening", amount="100.00", actual_date="2026-04-01")
        out = self.fact(direction="expense", amount="47.00", nature="internal_principal")
        inc = self.fact(account=self.cash, amount="47.00", nature="internal_principal", actual_date="2026-04-05")
        ident = self.review("53.00")
        self.api("transfers", {"outgoing": out["id"], "incoming": inc["id"], "reason": "合成核对后补充本金核实"}, 201)
        self.assertEqual(self.balance(), 53)
        row = next(r for r in self.state()["reviews"] if r["id"] == ident)
        self.assertEqual(row["status"], "needs_review")


@override_settings(**probes.scope_fixture.RBAC_SETTINGS, RMB_CASH_ACCOUNT_IDS=("SYNTH_FX", "SYNTH_CNY"), PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class AuthorizedRoleDefectReproduction(probes.HiddenSourceFixture, TestCase):
    def setUp(self):
        self.setup_hidden()

    def test_adv03_authorized_global_finance_role_can_reach_scoped_preview(self):
        user, data = self.hidden_candidate()
        # finance + transactions rights and all data scope are explicitly granted;
        # only contract visibility is withheld. This must reach the scoped preview.
        self.api("preview", data, user=user)
