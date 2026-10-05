from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from crm.models import Customer, Order, PaymentPlan, PurchaseOrder, Supplier


class PaymentPlanFilterApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.alpha = Customer.objects.create(code="PPF-C1", name="Alpha GmbH")
        self.beta = Customer.objects.create(code="PPF-C2", name="Beta GmbH")
        self.supplier = Supplier.objects.create(code="PPF-S1", name="Supplier North")
        self.other_supplier = Supplier.objects.create(code="PPF-S2", name="Supplier South")
        self.alpha_order = self.make_order("SO-2026-00032", self.alpha)
        self.alpha_other_order = self.make_order("SO-2026-00033", self.alpha)
        self.beta_order = self.make_order("SO-PPF-BETA", self.beta)
        self.purchase = self.make_purchase("PO-2026-00015", self.supplier)
        self.other_purchase = self.make_purchase("PO-PPF-SOUTH", self.other_supplier)

    def make_order(self, order_no, customer):
        return Order.objects.create(
            order_no=order_no,
            customer=customer,
            order_date=date(2026, 10, 1),
            currency="USD",
            status="confirmed",
        )

    def make_purchase(self, purchase_no, supplier):
        return PurchaseOrder.objects.create(
            purchase_no=purchase_no,
            supplier=supplier,
            order_date=date(2026, 10, 1),
            status="ordered",
            currency="USD",
        )

    def make_plan(self, *, order=None, purchase_order=None, due_date=None, status="open"):
        return PaymentPlan.objects.create(
            order=order,
            purchase_order=purchase_order,
            direction="receivable" if order else "payable",
            due_date=due_date,
            planned_amount=Decimal("100"),
            currency="USD",
            status=status,
            settled_amount=Decimal("100") if status == "settled" else Decimal("0"),
        )

    def plan_ids(self, response):
        self.assertEqual(response.status_code, 200, response.data)
        return {row["id"] for row in response.data.get("results", response.data)}

    def test_receivables_search_by_customer_and_order_number(self):
        alpha_plan = self.make_plan(order=self.alpha_order)
        self.make_plan(order=self.beta_order)

        by_customer = self.client.get("/api/payment-plans/", {"direction": "receivable", "search": "Alpha GmbH"})
        by_order = self.client.get("/api/payment-plans/", {"direction": "receivable", "search": "SO-2026-00032"})

        self.assertEqual(self.plan_ids(by_customer), {alpha_plan.id})
        self.assertEqual(self.plan_ids(by_order), {alpha_plan.id})

    def test_payables_search_by_supplier_and_purchase_number(self):
        supplier_plan = self.make_plan(purchase_order=self.purchase)
        self.make_plan(purchase_order=self.other_purchase)

        by_supplier = self.client.get("/api/payment-plans/", {"direction": "payable", "search": "Supplier North"})
        by_purchase = self.client.get("/api/payment-plans/", {"direction": "payable", "search": "PO-2026-00015"})

        self.assertEqual(self.plan_ids(by_supplier), {supplier_plan.id})
        self.assertEqual(self.plan_ids(by_purchase), {supplier_plan.id})

    def test_due_from_due_to_and_inclusive_range_filter_independently(self):
        dates = [date(2026, 9, 30), date(2026, 10, 1), date(2026, 10, 15), date(2026, 10, 31), date(2026, 11, 1)]
        plans = [self.make_plan(order=self.alpha_order, due_date=due_date) for due_date in dates]
        undated = self.make_plan(order=self.alpha_order, due_date=None)

        due_from = self.plan_ids(self.client.get("/api/payment-plans/", {"direction": "receivable", "due_from": "2026-10-01"}))
        due_to = self.plan_ids(self.client.get("/api/payment-plans/", {"direction": "receivable", "due_to": "2026-10-31"}))
        both = self.plan_ids(self.client.get("/api/payment-plans/", {
            "direction": "receivable", "due_from": "2026-10-01", "due_to": "2026-10-31",
        }))

        self.assertEqual(due_from, {plan.id for plan in plans[1:]})
        self.assertEqual(due_to, {plan.id for plan in plans[:4]})
        self.assertEqual(both, {plan.id for plan in plans[1:4]})
        self.assertNotIn(undated.id, due_from | due_to | both)

    def test_search_date_status_and_direction_filters_intersect(self):
        matching = self.make_plan(order=self.alpha_order, due_date=date(2026, 10, 15))
        self.make_plan(order=self.alpha_other_order, due_date=date(2026, 11, 1))
        self.make_plan(order=self.beta_order, due_date=date(2026, 10, 15))
        self.make_plan(order=self.alpha_order, due_date=date(2026, 10, 15), status="settled")
        self.make_plan(purchase_order=self.purchase, due_date=date(2026, 10, 15))

        response = self.client.get("/api/payment-plans/", {
            "direction": "receivable", "status": "open", "search": "Alpha GmbH",
            "due_from": "2026-10-01", "due_to": "2026-10-31",
        })

        self.assertEqual(self.plan_ids(response), {matching.id})

    def test_contract_id_filters_combine_with_due_range(self):
        selected_receivable = self.make_plan(order=self.alpha_order, due_date=date(2026, 10, 15))
        self.make_plan(order=self.alpha_other_order, due_date=date(2026, 10, 15))
        selected_payable = self.make_plan(purchase_order=self.purchase, due_date=date(2026, 10, 15))
        self.make_plan(purchase_order=self.other_purchase, due_date=date(2026, 10, 15))

        receivables = self.client.get("/api/payment-plans/", {
            "direction": "receivable", "order": self.alpha_order.id,
            "due_from": "2026-10-01", "due_to": "2026-10-31",
        })
        payables = self.client.get("/api/payment-plans/", {
            "direction": "payable", "purchase_order": self.purchase.id,
            "due_from": "2026-10-01", "due_to": "2026-10-31",
        })

        self.assertEqual(self.plan_ids(receivables), {selected_receivable.id})
        self.assertEqual(self.plan_ids(payables), {selected_payable.id})

    def test_direction_constraint_prevents_cross_type_search_leaks(self):
        receivable = self.make_plan(order=self.alpha_order)
        payable = self.make_plan(purchase_order=self.purchase)

        wrong_receivable = self.client.get("/api/payment-plans/", {"direction": "receivable", "search": "PO-2026-00015"})
        wrong_payable = self.client.get("/api/payment-plans/", {"direction": "payable", "search": "SO-2026-00032"})

        self.assertEqual(self.plan_ids(wrong_receivable), set())
        self.assertEqual(self.plan_ids(wrong_payable), set())
        self.assertEqual(self.plan_ids(self.client.get("/api/payment-plans/", {"direction": "receivable"})), {receivable.id})
        self.assertEqual(self.plan_ids(self.client.get("/api/payment-plans/", {"direction": "payable"})), {payable.id})

    def test_overdue_semantics_remain_open_and_strictly_before_today(self):
        overdue = self.make_plan(order=self.alpha_order, due_date=date(2026, 10, 4))
        due_today = self.make_plan(order=self.alpha_other_order, due_date=date(2026, 10, 5))
        settled = self.make_plan(order=self.alpha_order, due_date=date(2026, 10, 1), status="settled")

        with patch("crm.views.timezone.localdate", return_value=date(2026, 10, 5)):
            response = self.client.get("/api/payment-plans/", {
                "direction": "receivable", "status": "", "overdue": "true", "due_from": "2026-10-01",
            })
            settled_overdue = self.client.get("/api/payment-plans/", {
                "direction": "receivable", "status": "settled", "overdue": "true",
            })

        self.assertEqual(self.plan_ids(response), {overdue.id})
        self.assertNotIn(due_today.id, self.plan_ids(response))
        self.assertEqual(self.plan_ids(settled_overdue), set())
        self.assertNotIn(settled.id, self.plan_ids(response))

    def test_invalid_due_date_values_return_clear_bad_request(self):
        for key, value in (("due_from", "not-a-date"), ("due_to", "2026-02-30"), ("due_from", "2026-1-2")):
            with self.subTest(key=key, value=value):
                response = self.client.get("/api/payment-plans/", {"direction": "receivable", key: value})
                self.assertEqual(response.status_code, 400, response.data)
                self.assertIn(key, response.data)
                self.assertIn("YYYY-MM-DD", str(response.data[key]))

    def test_due_from_after_due_to_returns_clear_bad_request(self):
        response = self.client.get("/api/payment-plans/", {
            "direction": "receivable", "due_from": "2026-11-01", "due_to": "2026-10-01",
        })

        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("due_from", response.data)
        self.assertIn("due_to", str(response.data["due_from"]))
