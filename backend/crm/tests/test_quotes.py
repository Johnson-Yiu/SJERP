from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from crm.models import Customer, Product, Quote, QuoteItem, SKU
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
