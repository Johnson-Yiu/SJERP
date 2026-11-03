"""Unknown historical buyer snapshots must never become today's customer."""

import io
from datetime import date
from unittest.mock import patch

from django.test import TestCase
from openpyxl import load_workbook
from rest_framework.test import APIClient

from crm.models import Customer, Order, Product, Quote, QuoteRevisionCounter, SKU


class UnknownBuyerRevisionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = Customer.objects.create(
            code="UNKNOWN-BUYER", name="Original Buyer", country="Germany",
        )
        product = Product.objects.create(code="UNKNOWN-PRODUCT", name="Synthetic Product")
        self.sku = SKU.objects.create(product=product, sku="UNKNOWN-SKU")

    def create_quote(self, **changes):
        payload = {
            "customer": self.customer.pk, "quote_date": "2026-11-03",
            "currency": "USD", "recipient_name": "", "buyer_email": "",
            "buyer_phone": "", "buyer_address": "",
            "items": [{"sku": self.sku.pk, "quantity": "2", "unit_price": "10"}],
            **changes,
        }
        response = self.client.post("/api/quotes/", payload, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        return Quote.objects.get(pk=response.data["id"])

    def legacy_quote(self, buyer=""):
        quote = self.create_quote()
        # Reproduce an existing incomplete historical snapshot, not a new
        # production backfill or change to the immutable snapshot API.
        Quote.objects.filter(pk=quote.pk).update(buyer_company_name=buyer)
        self.customer.name = "Current Master Is Not Historical"
        self.customer.save(update_fields=["name"])
        quote.refresh_from_db()
        return quote

    def assert_saved_buyer(self, quote, expected):
        quote.refresh_from_db()
        self.assertEqual(quote.buyer_company_name, expected)
        detail = self.client.get(f"/api/quotes/{quote.pk}/")
        self.assertEqual(detail.status_code, 200, detail.data)
        self.assertEqual(detail.data["buyer_company_name"], expected)
        for field in ("recipient_name", "buyer_email", "buyer_phone", "buyer_address"):
            self.assertEqual(detail.data[field], "")

    def test_new_api_quote_omitted_buyer_still_prefills_and_buyer_is_readonly(self):
        quote = self.create_quote(buyer_company_name="Untrusted Client Name")
        self.assertEqual(quote.buyer_company_name, "Original Buyer")

    def test_new_model_omitted_and_explicit_blank_buyer_are_distinct(self):
        for index, fields, expected in (
            (1, {}, "Original Buyer"),
            (2, {"buyer_company_name": ""}, ""),
            (3, {"buyer_company_name": "Explicit Snapshot"}, "Explicit Snapshot"),
        ):
            with self.subTest(fields=fields):
                quote = Quote.objects.create(
                    quote_no=f"SYNTHETIC-{index}", customer=self.customer,
                    quote_date=date(2026, 11, 3), **fields,
                )
                quote.refresh_from_db()
                self.assertEqual(quote.buyer_company_name, expected)

    def test_existing_blank_survives_full_and_partial_save_and_deferred_load(self):
        quote = self.legacy_quote()
        quote.notes = "Ordinary internal lifecycle save"
        quote.save()
        self.assert_saved_buyer(quote, "")
        quote = Quote.objects.only("pk", "notes").get(pk=quote.pk)
        quote.notes = "Deferred instance"
        quote.save(update_fields=["notes"])
        self.assert_saved_buyer(quote, "")
        quote.status = "sent"
        quote.save(update_fields=["status"])
        self.assert_saved_buyer(quote, "")

    def test_revision_without_explicit_buyer_never_prefills_current_master(self):
        source = self.legacy_quote()
        revision = Quote.objects.create(
            quote_no=f"{source.quote_no}-1", customer=self.customer,
            quote_date=source.quote_date, parent_quote=source, root_quote=source,
            revision_no=1,
        )
        self.assertEqual(revision.buyer_company_name, "")
        revision.refresh_from_db()
        self.assertEqual(revision.buyer_company_name, "")

    def test_regular_revision_preserves_empty_and_nonempty_historical_buyer(self):
        for buyer in ("", "Historical Buyer"):
            with self.subTest(buyer=buyer):
                quote = self.legacy_quote(buyer)
                old_values = Quote.objects.filter(pk=quote.pk).values().get()
                response = self.client.post(
                    f"/api/quotes/{quote.pk}/revise/",
                    {"revision_summary": "Synthetic revision", "buyer_company_name": "Do Not Replace"},
                    format="json",
                )
                self.assertEqual(response.status_code, 201, response.data)
                revision = Quote.objects.get(pk=response.data["id"])
                self.assertEqual(revision.parent_quote_id, quote.pk)
                self.assert_saved_buyer(revision, buyer)
                self.assertEqual(Quote.objects.filter(pk=quote.pk).values().get(), old_values)
                child = self.client.post(
                    f"/api/quotes/{revision.pk}/revise/",
                    {"revision_summary": "Second generation"}, format="json",
                )
                self.assertEqual(child.status_code, 201, child.data)
                self.assertEqual(child.data["buyer_company_name"], buyer)
                if buyer:
                    preview = self.client.get(f"/api/quotes/{revision.pk}/pi-data/")
                    self.assertEqual(preview.status_code, 200, preview.data)
                    self.assertEqual(preview.data["buyer"]["company_name"], buyer)
                    self.assertEqual(preview.data["buyer"]["email"], "")
                    exported = self.client.get(f"/api/quotes/{revision.pk}/export/")
                    self.assertEqual(exported.status_code, 200)
                    workbook = load_workbook(io.BytesIO(exported.content))
                    text = "\n".join(str(cell.value or "") for row in workbook.active for cell in row)
                    self.assertIn(buyer, text)
                    self.assertNotIn(self.customer.name, text)
                    workbook.close()

    def test_order_confirmation_revision_preserves_empty_and_nonempty_buyer(self):
        for buyer in ("", "Historical Buyer"):
            with self.subTest(buyer=buyer):
                quote = self.legacy_quote(buyer)
                old_values = Quote.objects.filter(pk=quote.pk).values().get()
                draft = self.client.get(f"/api/quotes/{quote.pk}/order-draft/")
                self.assertEqual(draft.status_code, 200, draft.data)
                payload = dict(draft.data, shipping_fee="1.00")
                saved = self.client.post("/api/orders/", payload, format="json")
                self.assertEqual(saved.status_code, 201, saved.data)
                confirmed = self.client.post(f"/api/orders/{saved.data['id']}/confirm/", {}, format="json")
                self.assertEqual(confirmed.status_code, 200, confirmed.data)
                order = Order.objects.get(pk=saved.data["id"])
                self.assertNotEqual(order.quote_id, quote.pk)
                self.assertEqual(order.quote.parent_quote_id, quote.pk)
                self.assert_saved_buyer(order.quote, buyer)
                self.assertEqual(Quote.objects.filter(pk=quote.pk).values().get(), old_values)

    def test_unknown_buyer_revision_pi_and_xlsx_reject_without_live_master_fallback(self):
        quote = self.legacy_quote()
        revised = self.client.post(
            f"/api/quotes/{quote.pk}/revise/", {"revision_summary": "Keep unknown"}, format="json",
        )
        self.assertEqual(revised.status_code, 201, revised.data)
        for quote_id in (quote.pk, revised.data["id"]):
            for action in ("pi-data", "export"):
                with self.subTest(quote_id=quote_id, action=action):
                    response = self.client.get(f"/api/quotes/{quote_id}/{action}/")
                    self.assertEqual(response.status_code, 422, response.data)
                    self.assertIn("buyer_company_name", response.data["fields"])
                    self.assertNotIn("spreadsheetml", response.get("Content-Type", ""))

    def test_failed_revision_item_creation_rolls_back_version_and_original(self):
        quote = self.legacy_quote()
        old_values = Quote.objects.filter(pk=quote.pk).values().get()
        counters = list(QuoteRevisionCounter.objects.values())
        with patch("crm.views.create_quote_items", side_effect=RuntimeError("Synthetic item failure")):
            with self.assertRaisesMessage(RuntimeError, "Synthetic item failure"):
                self.client.post(
                    f"/api/quotes/{quote.pk}/revise/",
                    {"revision_summary": "Rollback"}, format="json",
                )
        self.assertEqual(Quote.objects.count(), 1)
        self.assertEqual(Quote.objects.filter(pk=quote.pk).values().get(), old_values)
        self.assertEqual(list(QuoteRevisionCounter.objects.values()), counters)
        retried = self.client.post(
            f"/api/quotes/{quote.pk}/revise/", {"revision_summary": "Retry"}, format="json",
        )
        self.assertEqual(retried.status_code, 201, retried.data)
        self.assertEqual(retried.data["buyer_company_name"], "")
        self.assertEqual(retried.data["revision_no"], 1)

    def test_immutable_saved_quote_api_still_rejects_direct_edit(self):
        quote = self.legacy_quote()
        response = self.client.patch(
            f"/api/quotes/{quote.pk}/", {"buyer_company_name": "Current Buyer", "notes": "Edit"}, format="json",
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.assert_saved_buyer(quote, "")

    def test_failed_order_revision_rolls_back_draft_quote_link_and_counter(self):
        quote = self.legacy_quote()
        draft = self.client.get(f"/api/quotes/{quote.pk}/order-draft/")
        self.assertEqual(draft.status_code, 200, draft.data)
        saved = self.client.post("/api/orders/", dict(draft.data, shipping_fee="1.00"), format="json")
        self.assertEqual(saved.status_code, 201, saved.data)
        order_id = saved.data["id"]
        old_order = Order.objects.filter(pk=order_id).values().get()
        old_quote = Quote.objects.filter(pk=quote.pk).values().get()
        counters = list(QuoteRevisionCounter.objects.values())
        with patch("crm.serializers.create_quote_items", side_effect=RuntimeError("Synthetic order revision failure")):
            with self.assertRaisesMessage(RuntimeError, "Synthetic order revision failure"):
                self.client.post(f"/api/orders/{order_id}/confirm/", {}, format="json")
        self.assertEqual(Order.objects.filter(pk=order_id).values().get(), old_order)
        self.assertEqual(Quote.objects.filter(pk=quote.pk).values().get(), old_quote)
        self.assertEqual(Quote.objects.count(), 1)
        self.assertEqual(list(QuoteRevisionCounter.objects.values()), counters)
        retried = self.client.post(f"/api/orders/{order_id}/confirm/", {}, format="json")
        self.assertEqual(retried.status_code, 200, retried.data)
        self.assert_saved_buyer(Order.objects.get(pk=order_id).quote, "")
