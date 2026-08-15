from datetime import date
from decimal import Decimal
import tempfile

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.test.utils import override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APIClient

from crm.models import Contact, Customer, Product, Quote, QuoteItem, QuoteRevisionCounter, SKU
from crm.quote_numbers import allocate_revision_quote_no, allocate_root_quote_no


class QuoteRevisionTests(TestCase):
    def create_quote(self, country="Germany", quote_date=date(2026, 8, 15)):
        customer = Customer.objects.create(
            code=f"C-{Customer.objects.count() + 1:03d}",
            name=f"Buyer {Customer.objects.count() + 1}",
            country=country,
        )
        return Quote.objects.create(
            quote_no=allocate_root_quote_no(quote_date, country),
            customer=customer,
            quote_date=quote_date,
        )

    def create_revision(self, root):
        quote_no, revision_no = allocate_revision_quote_no(root)
        return Quote.objects.create(
            quote_no=quote_no,
            customer=root.customer,
            quote_date=root.quote_date,
            root_quote=root,
            revision_no=revision_no,
        )

    def test_root_number_uses_date_country_and_sequence(self):
        quote = self.create_quote(country="Germany", quote_date=date(2026, 8, 15))

        self.assertEqual(quote.quote_no, "SJ20260815DE001")

    def test_root_number_is_reserved_before_quote_creation(self):
        first = allocate_root_quote_no(date(2026, 8, 15), "Germany")
        second = allocate_root_quote_no(date(2026, 8, 15), "Germany")

        self.assertEqual(first, "SJ20260815DE001")
        self.assertEqual(second, "SJ20260815DE002")

    def test_revision_number_keeps_complete_root_identifier(self):
        root = self.create_quote(country="Germany", quote_date=date(2026, 8, 15))
        revision = self.create_revision(root)

        self.assertEqual(revision.quote_no, "SJ20260815DE001-1")
        self.assertEqual(revision.root_quote_id, root.id)
        self.assertEqual(revision.revision_no, 1)

    def test_revision_number_is_reserved_before_revision_creation(self):
        root = self.create_quote()

        self.assertEqual(allocate_revision_quote_no(root), ("SJ20260815DE001-1", 1))
        self.assertEqual(allocate_revision_quote_no(root), ("SJ20260815DE001-2", 2))

    def test_revision_99_is_last_available_identifier(self):
        root = self.create_quote()
        Quote.objects.create(
            quote_no=f"{root.quote_no}-98",
            customer=root.customer,
            quote_date=root.quote_date,
            root_quote=root,
            revision_no=98,
        )

        quote_no, revision_no = allocate_revision_quote_no(root)

        self.assertEqual((quote_no, revision_no), ("SJ20260815DE001-99", 99))
        Quote.objects.create(
            quote_no=quote_no,
            customer=root.customer,
            quote_date=root.quote_date,
            root_quote=root,
            revision_no=revision_no,
        )
        with self.assertRaises(ValidationError):
            allocate_revision_quote_no(root)

    def test_unsupported_country_is_rejected(self):
        with self.assertRaises(ValidationError):
            allocate_root_quote_no(date(2026, 8, 15), "Atlantis")

    def test_quote_snapshot_and_sku_image_fields_persist(self):
        quote = self.create_quote()
        quote.recipient_name = "Anna Schmidt"
        quote.buyer_address = "Berlin, Germany"
        quote.buyer_email = "anna@example.com"
        quote.buyer_phone = "+49 30 123456"
        quote.lead_time_days = 30
        quote.deposit_ratio = "0.30"
        quote.trading_terms = "FOB Shenzhen"
        quote.shipping_details = "Sea freight"
        quote.save()

        product = Product.objects.create(code="P-001", name="Panel")
        sku = SKU.objects.create(product=product, sku="SKU-001")
        item = QuoteItem.objects.create(
            quote=quote,
            sku=sku,
            quantity=1,
            unit_price=10,
            description="Dimmable panel light",
        )

        quote.refresh_from_db()
        self.assertEqual(quote.recipient_name, "Anna Schmidt")
        self.assertEqual(quote.deposit_ratio, Decimal("0.3000"))
        self.assertEqual(item.description, "Dimmable panel light")
        self.assertEqual(sku._meta.get_field("image").upload_to, "sku-images/%Y/%m/")


class QuoteApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.media_dir = tempfile.TemporaryDirectory()
        self.media_settings = override_settings(MEDIA_ROOT=self.media_dir.name)
        self.media_settings.enable()
        self.customer = Customer.objects.create(
            code="C-API-001",
            name="API Buyer",
            country="Germany",
            address="Berlin, Germany",
        )
        Contact.objects.create(
            customer=self.customer,
            name="Primary Contact",
            email="primary@example.com",
            phone="+49 30 123456",
            is_primary=True,
        )
        product = Product.objects.create(code="P-API-001", name="API Panel")
        self.sku = SKU.objects.create(product=product, sku="SKU-API-001")

    def tearDown(self):
        self.media_settings.disable()
        self.media_dir.cleanup()

    def root_quote_payload(self, **overrides):
        payload = {
            "customer": self.customer.id,
            "quote_date": "2026-08-15",
            "currency": "USD",
            "items": [{
                "sku": self.sku.id,
                "quantity": "2.00",
                "unit_price": "10.00",
                "description": "Dimmable panel light",
            }],
        }
        payload.update(overrides)
        return payload

    def create_quote(self, **overrides):
        response = self.client.post("/api/quotes/", self.root_quote_payload(**overrides), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return Quote.objects.get(pk=response.data["id"])

    def test_create_populates_contact_snapshot_and_item_description(self):
        response = self.client.post("/api/quotes/", self.root_quote_payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["quote_no"], "SJ20260815DE001")
        self.assertEqual(response.data["recipient_name"], "Primary Contact")
        self.assertEqual(response.data["buyer_address"], "Berlin, Germany")
        self.assertEqual(response.data["buyer_email"], "primary@example.com")
        self.assertEqual(response.data["items"][0]["description"], "Dimmable panel light")

    def test_create_ignores_client_quote_number_and_revision_fields(self):
        response = self.client.post(
            "/api/quotes/",
            self.root_quote_payload(quote_no="CLIENT-NUMBER", root_quote=123, revision_no=99),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["quote_no"], "SJ20260815DE001")
        self.assertIsNone(response.data["root_quote"])
        self.assertEqual(response.data["revision_no"], 0)

    def test_revise_creates_not_updates_and_returns_full_invoice_no(self):
        root = self.create_quote(notes="Original terms")

        response = self.client.post(
            f"/api/quotes/{root.id}/revise/",
            {"notes": "Revised terms", "items": [{
                "sku": self.sku.id,
                "quantity": "3.00",
                "unit_price": "12.00",
                "description": "Updated description",
            }]},
            format="json",
        )

        root.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["quote_no"], f"{root.quote_no}-1")
        self.assertEqual(response.data["root_quote"], root.id)
        self.assertEqual(response.data["revision_no"], 1)
        self.assertEqual(root.notes, "Original terms")
        self.assertEqual(root.items.get().description, "Dimmable panel light")
        self.assertEqual(response.data["items"][0]["description"], "Updated description")

    def test_revise_rejects_customer_change_that_would_mismatch_buyer_snapshot(self):
        root = self.create_quote()
        another_customer = Customer.objects.create(code="C-API-002", name="Other Buyer", country="Germany")

        response = self.client.post(
            f"/api/quotes/{root.id}/revise/",
            {"customer": another_customer.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("customer", response.data)
        self.assertEqual(Quote.objects.count(), 1)

    def test_create_returns_400_for_unsupported_country(self):
        unsupported_customer = Customer.objects.create(code="C-API-003", name="Atlantis Buyer", country="Atlantis")

        response = self.client.post(
            "/api/quotes/",
            self.root_quote_payload(customer=unsupported_customer.id),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_revise_returns_400_after_revision_99(self):
        root = self.create_quote()
        QuoteRevisionCounter.objects.create(root_quote=root, last_value=99)

        response = self.client.post(f"/api/quotes/{root.id}/revise/", {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_put_and_patch_reject_changes_to_saved_quotes(self):
        quote = self.create_quote()

        put_response = self.client.put(f"/api/quotes/{quote.id}/", self.root_quote_payload(notes="Changed"), format="json")
        patch_response = self.client.patch(f"/api/quotes/{quote.id}/", {"notes": "Changed"}, format="json")

        self.assertEqual(put_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(patch_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(put_response.data["detail"], "已保存报价请创建迭代版本")
        self.assertEqual(patch_response.data["detail"], "已保存报价请创建迭代版本")

    def test_pi_data_returns_snapshots_totals_payment_splits_and_product_image_url(self):
        upload = SimpleUploadedFile(
            "panel.gif",
            b"GIF87a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;",
            content_type="image/gif",
        )
        upload_response = self.client.post(f"/api/skus/{self.sku.id}/image/", {"image": upload}, format="multipart")
        self.assertEqual(upload_response.status_code, status.HTTP_200_OK)
        quote = self.create_quote(shipping_fee="5.00", discount="1.00", deposit_ratio="0.30", trading_terms="FOB Shenzhen")

        response = self.client.get(f"/api/quotes/{quote.id}/pi-data/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["invoice_no"], quote.quote_no)
        self.assertEqual(response.data["buyer"]["name"], "Primary Contact")
        self.assertEqual(Decimal(response.data["totals"]["subtotal"]), Decimal("20.00"))
        self.assertEqual(Decimal(response.data["totals"]["total_amount"]), Decimal("24.00"))
        self.assertEqual(Decimal(response.data["payment_splits"]["deposit_amount"]), Decimal("7.20"))
        self.assertEqual(response.data["products"][0]["description"], "Dimmable panel light")
        self.assertIn("/media/sku-images/", response.data["products"][0]["image_url"])

    def test_sku_image_upload_rejects_non_image_mime_type(self):
        upload = SimpleUploadedFile("not-an-image.txt", b"not an image", content_type="text/plain")

        response = self.client.post(f"/api/skus/{self.sku.id}/image/", {"image": upload}, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("image", response.data)
