from datetime import date

from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from crm.models import Customer, Order, Product, Quote, SKU
from crm.serializers import QuoteSerializer


class QuoteBuyerCountrySnapshotTests(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create(code="SYN-COUNTRY", name="Synthetic buyer", country="Germany")
        product = Product.objects.create(code="SYN-COUNTRY-P", name="Synthetic product")
        self.sku = SKU.objects.create(product=product, sku="SYN-COUNTRY-SKU")
        self.client = APIClient()

    def create_quote(self):
        response = self.client.post("/api/quotes/", {
            "customer": self.customer.pk, "quote_date": "2026-11-05",
            "buyer_country_snapshot": "Untrusted",
            "items": [{"sku": self.sku.pk, "quantity": "1", "unit_price": "10"}],
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        return Quote.objects.get(pk=response.data["id"])

    def test_new_saved_quote_and_revision_retain_original_country(self):
        quote = self.create_quote()
        self.assertEqual(quote.buyer_country_snapshot, "Germany")
        self.customer.country = "France"
        self.customer.save(update_fields=["country"])
        result = self.client.post(f"/api/quotes/{quote.pk}/revise/", {
            "revision_summary": "Synthetic revision", "buyer_country_snapshot": "Untrusted",
        }, format="json")
        self.assertEqual(result.status_code, 201, result.data)
        self.assertEqual(result.data["buyer_country_snapshot"], "Germany")
        self.assertEqual(self.client.get(f"/api/quotes/{quote.pk}/").data["buyer_country_snapshot"], "Germany")

    def test_unknown_legacy_and_explicit_none_remain_unknown(self):
        quote = self.create_quote()
        Quote.objects.filter(pk=quote.pk).update(buyer_country_snapshot=None)
        self.customer.country = "France"
        self.customer.save(update_fields=["country"])
        response = self.client.post(f"/api/quotes/{quote.pk}/revise/", {"revision_summary": "Unknown"}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertIsNone(response.data["buyer_country_snapshot"])
        original = Quote.objects.get(pk=quote.pk)
        self.assertIsNone(original.buyer_country_snapshot)
        explicit = Quote.objects.create(quote_no="SYN-EXPLICIT-UNKNOWN", customer=self.customer,
                                        quote_date=date(2026, 11, 5), buyer_country_snapshot=None)
        self.assertIsNone(explicit.buyer_country_snapshot)

    def test_saved_snapshot_cannot_be_overwritten_through_model_save(self):
        quote = self.create_quote()
        quote.buyer_country_snapshot = "France"
        with self.assertRaises(ValidationError):
            quote.save(update_fields=["buyer_country_snapshot"])
        quote.refresh_from_db()
        self.assertEqual(quote.buyer_country_snapshot, "Germany")

    def test_order_confirmation_revision_keeps_quote_country(self):
        quote = self.create_quote()
        self.customer.country = "France"
        self.customer.save(update_fields=["country"])
        draft = self.client.get(f"/api/quotes/{quote.pk}/order-draft/")
        self.assertEqual(draft.status_code, 200, draft.data)
        created = self.client.post('/api/orders/', dict(draft.data, shipping_fee="1.00"), format="json")
        self.assertEqual(created.status_code, 201, created.data)
        confirmed = self.client.post(f"/api/orders/{created.data['id']}/confirm/", {}, format="json")
        self.assertEqual(confirmed.status_code, 200, confirmed.data)
        order = Order.objects.get(pk=created.data['id'])
        self.assertEqual(order.quote.parent_quote_id, quote.pk)
        self.assertEqual(order.quote.buyer_country_snapshot, "Germany")
        # Confirmation preserves the saved quote, not the later customer edit.
        self.assertEqual(order.customer_country_snapshot, "Germany")

    @override_settings(APP_STAGE="production", DEBUG=False, DEVELOPMENT_SUPERADMIN=False, RBAC_ENFORCEMENT=True)
    def test_customer_country_is_hidden_without_customer_view(self):
        quote = Quote.objects.create(quote_no="SYN-REDACT", customer=self.customer, quote_date=date(2026, 11, 5))
        self.assertIsNone(QuoteSerializer(quote, context={"user": AnonymousUser()}).data["buyer_country_snapshot"])
