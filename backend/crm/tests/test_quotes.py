from datetime import date
from decimal import Decimal
import io
import tempfile
import zipfile
from xml.etree import ElementTree

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.test.utils import override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APIClient

from crm.models import Contact, Customer, Product, Quote, QuoteItem, QuoteRevisionCounter, SKU
from crm.quote_numbers import allocate_revision_quote_no, allocate_root_quote_no


def unzip_member(xlsx_bytes, member_name):
    with zipfile.ZipFile(io.BytesIO(xlsx_bytes)) as archive:
        return archive.read(member_name)


def xlsx_cell_text(xlsx_bytes, cell_reference):
    namespace = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    sheet = ElementTree.fromstring(unzip_member(xlsx_bytes, "xl/worksheets/sheet1.xml"))
    cell = sheet.find(f".//x:c[@r='{cell_reference}']", namespace)
    if cell is None:
        return None
    value = cell.findtext("x:v", default="", namespaces=namespace)
    if cell.get("t") != "s":
        return value
    shared_strings = ElementTree.fromstring(unzip_member(xlsx_bytes, "xl/sharedStrings.xml"))
    item = shared_strings.findall("x:si", namespace)[int(value)]
    return "".join(item.itertext())


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

    def test_create_accepts_localized_chinese_country_names(self):
        for country, expected_iso_code in (("美国", "US"), ("法国", "FR"), ("阿联酋", "AE")):
            with self.subTest(country=country):
                self.customer.country = country
                self.customer.save(update_fields=["country"])

                response = self.client.post("/api/quotes/", self.root_quote_payload(), format="json")

                self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
                self.assertEqual(response.data["quote_no"], f"SJ20260815{expected_iso_code}001")

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

    def test_sku_image_can_be_cleared_after_upload(self):
        upload = SimpleUploadedFile(
            "panel.gif",
            b"GIF87a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01;",
            content_type="image/gif",
        )
        self.client.post(f"/api/skus/{self.sku.id}/image/", {"image": upload}, format="multipart")

        response = self.client.delete(f"/api/skus/{self.sku.id}/image/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.sku.refresh_from_db()
        self.assertFalse(self.sku.image)
        self.assertEqual(response.data["image"], None)


class QuoteExportTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = Customer.objects.create(
            code="C-EXPORT-001",
            name="Export Buyer GmbH",
            country="Germany",
            address="Berlin, Germany",
        )
        self.product = Product.objects.create(code="P-EXPORT-001", name="Export Panel")
        self.sku_1 = SKU.objects.create(product=self.product, sku="SKU-001", unit="pcs")
        self.sku_2 = SKU.objects.create(product=self.product, sku="SKU-002", unit="pcs")
        self.sku_3 = SKU.objects.create(product=self.product, sku="SKU-003", unit="pcs")
        self.sku_4 = SKU.objects.create(product=self.product, sku="SKU-004", unit="pcs")
        self.multi_item_quote = self.create_quote(
            quote_no=allocate_root_quote_no(date(2026, 8, 15), "Germany"),
            items=[
                (self.sku_1, "Dimmable panel light", "2.00", "10.00"),
                (self.sku_2, "Emergency panel light", "3.00", "12.50"),
            ],
        )

    def create_quote(self, quote_no, items):
        quote = Quote.objects.create(
            quote_no=quote_no,
            customer=self.customer,
            quote_date=date(2026, 8, 15),
            valid_until=date(2026, 9, 14),
            currency="USD",
            shipping_fee=Decimal("5.00"),
            discount=Decimal("1.00"),
            recipient_name="Anna Schmidt",
            buyer_address="Berlin, Germany",
            buyer_email="anna@example.com",
            buyer_phone="+49 30 123456",
            lead_time_days=20,
            deposit_ratio=Decimal("0.3000"),
            trading_terms="FOB Shenzhen",
            shipping_details="Sea freight",
            notes="Cartons marked with buyer reference.",
        )
        QuoteItem.objects.bulk_create([
            QuoteItem(
                quote=quote,
                sku=sku,
                description=description,
                quantity=Decimal(quantity),
                unit_price=Decimal(unit_price),
            )
            for sku, description, quantity, unit_price in items
        ])
        return quote

    def create_revision(self, root):
        quote_no, revision_no = allocate_revision_quote_no(root)
        revision = self.create_quote(
            quote_no=quote_no,
            items=[
                (item.sku, item.description, str(item.quantity), str(item.unit_price))
                for item in root.items.select_related("sku")
            ],
        )
        revision.root_quote = root
        revision.revision_no = revision_no
        revision.save(update_fields=["root_quote", "revision_no"])
        return revision

    def test_export_filename_and_invoice_use_full_revision_identifier(self):
        revision = self.create_revision(self.multi_item_quote)

        response = self.client.get(f"/api/quotes/{revision.id}/export/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(f'{revision.quote_no}.xlsx', response["Content-Disposition"])
        self.assertTrue(response.content.startswith(b"PK"))
        self.assertIn(revision.quote_no.encode(), unzip_member(response.content, "xl/worksheets/sheet1.xml"))

    def test_export_two_items_contains_sku_codes_and_arial_style(self):
        response = self.client.get(f"/api/quotes/{self.multi_item_quote.id}/export/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        sheet_xml = unzip_member(response.content, "xl/worksheets/sheet1.xml")
        self.assertIn(b"SKU-001", sheet_xml)
        self.assertIn(b"SKU-002", sheet_xml)
        self.assertIn(b"Arial", unzip_member(response.content, "xl/styles.xml"))

    def test_export_expands_product_rows_and_shifts_fixed_bank_section(self):
        quote = self.create_quote(
            quote_no="SJ20260815DE099",
            items=[
                (self.sku_1, "Panel one", "1.00", "10.00"),
                (self.sku_2, "Panel two", "2.00", "11.00"),
                (self.sku_3, "Panel three", "3.00", "12.00"),
                (self.sku_4, "Panel four", "4.00", "13.00"),
            ],
        )

        response = self.client.get(f"/api/quotes/{quote.id}/export/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        sheet_xml = unzip_member(response.content, "xl/worksheets/sheet1.xml")
        self.assertIn(b"SKU-004", sheet_xml)
        self.assertEqual(xlsx_cell_text(response.content, "A23"), "BANK INFORMATION")
        self.assertEqual(xlsx_cell_text(response.content, "I3"), "Guangzhou Sunjack Lighting Co., Ltd.")
        self.assertEqual(xlsx_cell_text(response.content, "C24"), "Guangzhou Sunjack Lighting Co., Ltd.")
        self.assertEqual(xlsx_cell_text(response.content, "A31"), "Bank Code")
        self.assertEqual(xlsx_cell_text(response.content, "C31"), "007")
        self.assertEqual(xlsx_cell_text(response.content, "A32"), "Branch Code")
        self.assertTrue(xlsx_cell_text(response.content, "A33").startswith("IMPORTANT NOTICE"))

    @override_settings(QUOTE_XLSX_NODE_BINARY="definitely-not-a-real-node-binary")
    def test_export_failure_returns_422_without_changing_quote(self):
        before = Quote.objects.get(pk=self.multi_item_quote.pk)

        response = self.client.get(f"/api/quotes/{before.id}/export/")

        after = Quote.objects.get(pk=before.pk)
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertEqual(after.updated_at, before.updated_at)
        self.assertEqual(after.quote_no, before.quote_no)

    def test_export_negative_total_returns_422_without_changing_quote(self):
        self.multi_item_quote.discount = Decimal("1000.00")
        self.multi_item_quote.save()
        before = Quote.objects.get(pk=self.multi_item_quote.pk)
        failure_client = APIClient()
        failure_client.raise_request_exception = False

        response = failure_client.get(f"/api/quotes/{before.id}/export/")

        after = Quote.objects.get(pk=before.pk)
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertEqual(after.updated_at, before.updated_at)
        self.assertEqual(after.quote_no, before.quote_no)
