from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from crm.models import Customer, Product, SKU, Quote, Order


class SalesSafetyTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = Customer.objects.create(code="C-R0A", name="R0A Buyer", country="Germany")
        product = Product.objects.create(code="P-R0A", name="R0A Light")
        self.sku = SKU.objects.create(product=product, sku="SKU-R0A", currency="USD", default_price=99)

    def payload(self, kind="quotes", **changes):
        data = {"customer": self.customer.pk, "quote_date" if kind == "quotes" else "order_date": "2026-10-10",
                "currency": "USD", "exchange_rate": "7.2", "items": [{"sku": self.sku.pk, "quantity": "10", "unit_price": "10"}]}
        data.update(changes)
        return data

    def create_quote(self, **changes):
        response = self.client.post("/api/quotes/", self.payload(**changes), format="json")
        self.assertEqual(response.status_code, 201, response.data)
        return Quote.objects.get(pk=response.data["id"])

    def test_sales_rate_rejects_invalid_cny_and_nonpositive_foreign_rates(self):
        for kind in ("quotes", "orders"):
            for currency, rate in (("CNY", "7.2"), ("USD", "0"), ("EUR", "-1")):
                with self.subTest(kind=kind, currency=currency, rate=rate):
                    response = self.client.post(f"/api/{kind}/", self.payload(kind, currency=currency, exchange_rate=rate), format="json")
                    self.assertEqual(response.status_code, 400, response.data)
                    self.assertIn("exchange_rate", response.data)

    def test_new_sales_rate_defaults_and_explicit_foreign_rate(self):
        for kind in ("quotes", "orders"):
            for currency, expected in (("USD", "7.2"), ("CNY", "1")):
                data = self.payload(kind, currency=currency)
                data.pop("exchange_rate")
                response = self.client.post(f"/api/{kind}/", data, format="json")
                self.assertEqual(response.status_code, 201, response.data)
                self.assertEqual(Decimal(response.data["exchange_rate"]), Decimal(expected))
            for currency in ("EUR", "GBP"):
                data = self.payload(kind, currency=currency)
                data.pop("exchange_rate")
                self.assertEqual(self.client.post(f"/api/{kind}/", data, format="json").status_code, 400)
                data["exchange_rate"] = "8.3"
                self.assertEqual(self.client.post(f"/api/{kind}/", data, format="json").status_code, 201)

    def test_new_quote_defaults_to_thirty_percent(self):
        self.assertEqual(self.create_quote().deposit_ratio, Decimal("0.30"))

    def test_revision_preserves_historical_deposit_and_rate(self):
        for ratio in ("1", "0.5", "0"):
            quote = self.create_quote(deposit_ratio=ratio, exchange_rate="6.9")
            response = self.client.post(f"/api/quotes/{quote.pk}/revise/", {"revision_summary": "R0A 保留历史条款"}, format="json")
            self.assertEqual(response.status_code, 201, response.data)
            revised = Quote.objects.get(pk=response.data["id"])
            self.assertEqual(revised.deposit_ratio, Decimal(ratio))
            self.assertEqual(revised.exchange_rate, Decimal("6.9"))
            quote.refresh_from_db()
            self.assertEqual(quote.deposit_ratio, Decimal(ratio))

    def test_order_draft_initializes_delivery_and_preserves_quote_price(self):
        for days in (10, None, 0):
            quote = self.create_quote(lead_time_days=days)
            response = self.client.get(f"/api/quotes/{quote.pk}/order-draft/")
            self.assertEqual(response.status_code, 200)
            draft = response.data
            expected = draft["order_date"] + timedelta(days=days) if days is not None else None
            self.assertEqual(draft["expected_ship_date"], expected)
            self.assertEqual(draft["items"][0]["unit_price"], Decimal("10"))
            self.assertEqual(draft["currency"], quote.currency)

    def test_confirmed_order_payment_plan_uses_source_ratio_or_direct_default(self):
        for ratio in (None, "0.30", "1", "0.5", "0"):
            data = self.payload("orders")
            if ratio is not None:
                quote = self.create_quote(deposit_ratio=ratio)
                data["quote"] = quote.pk
            response = self.client.post("/api/orders/", data, format="json")
            self.assertEqual(response.status_code, 201, response.data)
            order = Order.objects.get(pk=response.data["id"])
            confirmed = self.client.post(f"/api/orders/{order.pk}/confirm/", {}, format="json")
            self.assertEqual(confirmed.status_code, 200, confirmed.data)
            amounts = sorted(order.payment_plans.values_list("planned_amount", flat=True))
            deposit = Decimal(ratio if ratio is not None else "0.30") * Decimal("100")
            self.assertEqual(amounts, sorted(x for x in (deposit, Decimal("100") - deposit) if x > 0))
