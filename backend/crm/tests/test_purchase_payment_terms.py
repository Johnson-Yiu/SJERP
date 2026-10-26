from copy import deepcopy
from datetime import date
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from crm.models import Product, SKU, Supplier, PurchaseOrder, PaymentPlan
from crm.payment_terms import default_payment_terms
from crm.services.finance import ensure_default_payment_plans


class PurchasePaymentTermsTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.supplier = Supplier.objects.create(code="PT", name="Payment terms test")
        self.sku = SKU.objects.create(sku="TERMS", product=Product.objects.create(code="TERMS", name="Terms sample"))

    def terms(self, ratios=("0.5", "0.5")):
        result = default_payment_terms()
        for row, ratio in zip(result, ratios):
            row["ratio"] = ratio
        return result

    def create(self, terms=None, price="1000", arrival="2026-10-30"):
        payload = {"supplier": self.supplier.pk, "order_date": "2026-10-10", "expected_arrival_date": arrival,
            "currency": "USD", "exchange_rate": "7", "items": [{"sku": self.sku.pk, "quantity": "1", "unit_price": price}]}
        if terms is not None:
            payload["payment_terms_snapshot"] = terms
        response = self.client.post("/api/purchase-orders/", payload, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        return PurchaseOrder.objects.get(pk=response.data["id"])

    def place(self, purchase):
        response = self.client.post(f"/api/purchase-orders/{purchase.pk}/place/")
        self.assertEqual(response.status_code, 200, response.data)
        return list(purchase.payment_plans.order_by("id"))

    def test_default_snapshot_does_not_parse_remarks(self):
        self.supplier.payment_terms = "100% paid later"
        self.supplier.save()
        self.supplier.payment_terms_config = self.terms()
        self.supplier.save()
        self.assertEqual(self.create().payment_terms_snapshot, [])

    def test_inherit_override_and_supplier_change_do_not_rewrite_snapshot_or_plans(self):
        self.supplier.payment_terms_config = self.terms()
        self.supplier.save()
        purchase = self.create()
        self.assertEqual(purchase.payment_terms_snapshot, [])
        override = self.terms(("0.2", "0.8"))
        response = self.client.patch(f"/api/purchase-orders/{purchase.pk}/", {"payment_terms_snapshot": override, "exchange_rate": "7"}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.supplier.refresh_from_db()
        self.assertEqual(self.supplier.payment_terms_config, self.terms())
        self.supplier.payment_terms_config = [{"label": "全款", "ratio": "1", "due_basis": "no_date", "offset_days": 0}]
        self.supplier.save()
        purchase.refresh_from_db()
        self.assertEqual(purchase.payment_terms_snapshot, override)
        plans = self.place(purchase)
        self.assertEqual([plan.planned_amount for plan in plans], [Decimal("200"), Decimal("800")])
        self.assertEqual(len(ensure_default_payment_plans(purchase)), 2)
        self.assertEqual(purchase.payment_plans.count(), 2)
        self.assertEqual(self.client.get(f"/api/purchase-orders/{purchase.pk}/").data["payment_plans"][0]["notes"], "预付款")
        response = self.client.patch(f"/api/purchase-orders/{purchase.pk}/", {"payment_terms_snapshot": self.terms(), "exchange_rate": "7"}, format="json")
        self.assertEqual(response.status_code, 400, response.data)

    def test_three_stages_rounding_dates_and_missing_dates(self):
        terms = [
            {"label": "首期", "ratio": "0.2", "due_basis": "order_date", "offset_days": 3},
            {"label": "中期", "ratio": "0.3", "due_basis": "expected_arrival_date", "offset_days": 2},
            {"label": "末期", "ratio": "0.5", "due_basis": "no_date", "offset_days": 9},
        ]
        purchase = self.create(terms, price="10.0001")
        plans = self.place(purchase)
        self.assertEqual(sum((plan.planned_amount for plan in plans), Decimal("0")), purchase.total_amount)
        self.assertEqual([p.due_date for p in plans], [date(2026, 10, 13), date(2026, 11, 1), None])
        plans = self.place(self.create(terms, arrival=None))
        self.assertIsNone(plans[1].due_date)
        tiny = self.create(terms, price="0.0001")
        plans = self.place(tiny)
        self.assertEqual(sum((p.planned_amount for p in plans), Decimal("0")), tiny.total_amount)

    def test_empty_snapshot_does_not_synthesize_payment_plans(self):
        purchase = self.create()
        PurchaseOrder.objects.filter(pk=purchase.pk).update(payment_terms_snapshot=[])
        plans = self.place(purchase)
        self.assertEqual(plans, [])
        ensure_default_payment_plans(purchase)
        self.assertEqual(PaymentPlan.objects.filter(purchase_order=purchase).count(), 0)

    def test_invalid_rules_rejected_by_supplier_and_purchase(self):
        cases = [self.terms(("0.2", "0.7")), [{}], self.terms() * 3]
        for field, value in (("ratio", "0"), ("ratio", "NaN"), ("label", " "), ("due_basis", "invalid"), ("offset_days", -1), ("offset_days", 0.5)):
            rows = deepcopy(self.terms())
            rows[0][field] = value
            cases.append(rows)
        for rules in cases:
            with self.subTest(rules=rules):
                response = self.client.patch(f"/api/suppliers/{self.supplier.pk}/", {"payment_terms_config": rules}, format="json")
                self.assertEqual(response.status_code, 400, response.data)
                purchase = self.create()
                response = self.client.patch(f"/api/purchase-orders/{purchase.pk}/", {"payment_terms_snapshot": rules, "exchange_rate": "7"}, format="json")
                self.assertEqual(response.status_code, 400, response.data)
        purchase = self.create()
        self.assertEqual(self.client.patch(f"/api/purchase-orders/{purchase.pk}/", {"payment_terms_snapshot": [], "exchange_rate": "7"}, format="json").status_code, 200)
        self.assertEqual(self.client.patch(f"/api/suppliers/{self.supplier.pk}/", {"payment_terms_config": []}, format="json").status_code, 200)
