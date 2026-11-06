"""Isolated evidence for whether existing APIs allow empty replacement drafts."""

from django.test import TestCase

from crm.models import Order, PurchaseOrder, Quote, Supplier
from crm.tests import test_quote_buyer_tax_id as tax_fixtures


class ReplacementCreationBlockerTests(TestCase):
    def setUp(self):
        tax_fixtures.QuoteBuyerTaxTests.setUp(self)

    def test_existing_order_and_purchase_apis_reject_empty_items(self):
        supplier = Supplier.objects.create(code="RB", name="Synthetic Replacement Supplier")
        before = (Order.objects.count(), PurchaseOrder.objects.count())
        responses = (
            self.client.post("/api/orders/", {"customer": self.customer.pk,
                "order_date": "2026-11-05", "currency": "USD", "exchange_rate": "7.2", "items": []}, format="json"),
            self.client.post("/api/purchase-orders/", {"supplier": supplier.pk,
                "order_date": "2026-11-05", "currency": "USD", "exchange_rate": "7.2", "items": []}, format="json"),
        )
        for response in responses:
            self.assertEqual(response.status_code, 400, response.data)
            self.assertIn("items", response.data)
            self.assertIn("至少", str(response.data["items"]))
        self.assertEqual((Order.objects.count(), PurchaseOrder.objects.count()), before)

    def test_quote_api_can_save_empty_items_but_it_is_not_a_complete_quote(self):
        response = self.client.post("/api/quotes/", {"customer": self.customer.pk,
            "quote_date": "2026-11-05", "currency": "USD", "exchange_rate": "7.2", "items": []}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        quote = Quote.objects.get(pk=response.data["id"])
        self.assertEqual(quote.status, "draft")
        self.assertFalse(quote.items.exists())
        result = self.client.get(f"/api/quotes/{quote.pk}/pi-data/")
        self.assertEqual(result.status_code, 422, result.data)
        self.assertIn("items", result.data["fields"])
