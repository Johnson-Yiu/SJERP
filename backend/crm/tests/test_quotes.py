from datetime import date
from decimal import Decimal
import io
import tempfile
import zipfile
from xml.etree import ElementTree

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.test.utils import override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APIClient

from crm.models import Contact, Customer, InventoryMovement, Order, Product, Quote, QuoteItem, QuoteRevisionCounter, SKU, Transaction
from crm.quote_numbers import allocate_revision_quote_no, allocate_root_quote_no
from crm.quote_snapshots import create_quote_items


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
        second_sku = SKU.objects.create(product=self.sku.product, sku="SKU-API-002")

        first_response = self.client.post(
            f"/api/quotes/{root.id}/revise/",
            {"revision_summary": "调整报价条款", "notes": "Revised terms", "items": [{
                "sku": self.sku.id,
                "quantity": "3.00",
                "unit_price": "12.00",
                "description": "Updated description",
            }]},
            format="json",
        )
        first_revision = Quote.objects.get(pk=first_response.data["id"])
        second_response = self.client.post(
            f"/api/quotes/{first_revision.id}/revise/",
            {
                "revision_summary": "延长有效期",
                "valid_until": "2026-09-21",
                "shipping_fee": "12.50",
                "discount": "5.00",
                "deposit_ratio": "0.40",
                "lead_time_days": 25,
                "trading_terms": "CIF Hamburg",
                "shipping_details": "DHL air freight",
                "notes": "Second revision",
                "items": [
                    {
                        "sku": self.sku.id,
                        "quantity": "2.00",
                        "unit_price": "10.00",
                        "description": "Dimmable panel light",
                    },
                    {
                        "sku": second_sku.id,
                        "quantity": "4.00",
                        "unit_price": "7.50",
                        "description": "Emergency panel light",
                    },
                ],
            },
            format="json",
        )

        root.refresh_from_db()
        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(first_response.data["quote_no"], f"{root.quote_no}-1")
        self.assertEqual(first_response.data["root_quote"], root.id)
        self.assertEqual(first_response.data["revision_no"], 1)
        self.assertEqual(second_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second_response.data["quote_no"], f"{root.quote_no}-2")
        self.assertEqual(second_response.data["root_quote"], root.id)
        self.assertEqual(second_response.data["revision_no"], 2)
        self.assertEqual(root.notes, "Original terms")
        self.assertEqual(root.items.get().description, "Dimmable panel light")
        self.assertEqual(first_response.data["items"][0]["description"], "Updated description")
        self.assertEqual(root.items.count(), 1)
        self.assertEqual(
            list(
                Quote.objects.filter(
                    pk__in=[root.pk, first_response.data["id"], second_response.data["id"]],
                ).order_by("revision_no").values_list("quote_no", flat=True)
            ),
            [root.quote_no, f"{root.quote_no}-1", f"{root.quote_no}-2"],
        )

    def test_revise_requires_a_non_blank_revision_summary(self):
        root = self.create_quote()

        response = self.client.post(f"/api/quotes/{root.id}/revise/", {"revision_summary": "   "}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("revision_summary", response.data)
        self.assertEqual(Quote.objects.count(), 1)

    def test_revise_records_the_direct_parent_version(self):
        root = self.create_quote()
        first = self.client.post(
            f"/api/quotes/{root.id}/revise/", {"revision_summary": "更新产品数量"}, format="json"
        )
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        first_revision = Quote.objects.get(pk=first.data["id"])

        branch = self.client.post(
            f"/api/quotes/{first_revision.id}/revise/", {"revision_summary": "更新付款条款"}, format="json"
        )

        self.assertEqual(branch.status_code, status.HTTP_201_CREATED)
        self.assertEqual(branch.data["parent_quote"], first_revision.id)
        self.assertEqual(branch.data["parent_quote_no"], first_revision.quote_no)
        self.assertEqual(branch.data["revision_summary"], "更新付款条款")
        branch_revision = Quote.objects.get(pk=branch.data["id"])
        self.assertEqual(branch_revision.parent_quote_id, first_revision.id)
        self.assertEqual(branch_revision.revision_summary, "更新付款条款")
        self.assertEqual(branch_revision.root_quote_id, root.id)

    def test_serializer_and_context_expose_quote_revision_lineage(self):
        root = self.create_quote()
        response = self.client.post(f"/api/quotes/{root.id}/revise/", {"revision_summary": "首次修订"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["root_quote_no"], root.quote_no)
        self.assertEqual(response.data["revision_label"], "Revision 1")

        context = self.client.get(f"/api/context/quotes/{response.data['id']}/")

        self.assertEqual(context.status_code, status.HTTP_200_OK)
        self.assertEqual(context.data["lineage"], {
            "root_quote_id": root.id,
            "root_quote_no": root.quote_no,
            "revision_no": 1,
            "revision_label": "Revision 1",
        })

    def test_revise_rejects_customer_change_that_would_mismatch_buyer_snapshot(self):
        root = self.create_quote()
        another_customer = Customer.objects.create(code="C-API-002", name="Other Buyer", country="Germany")

        response = self.client.post(
            f"/api/quotes/{root.id}/revise/",
            {"revision_summary": "错误的客户变更", "customer": another_customer.id},
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

        response = self.client.post(f"/api/quotes/{root.id}/revise/", {"revision_summary": "超过编号上限"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_put_and_patch_reject_changes_to_saved_quotes(self):
        quote = self.create_quote()

        put_response = self.client.put(f"/api/quotes/{quote.id}/", self.root_quote_payload(notes="Changed"), format="json")
        patch_response = self.client.patch(f"/api/quotes/{quote.id}/", {"notes": "Changed"}, format="json")

        self.assertEqual(put_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(patch_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(put_response.data["detail"], "已保存报价请创建迭代版本")
        self.assertEqual(patch_response.data["detail"], "已保存报价请创建迭代版本")

    def test_delete_rejects_saved_quotes_but_order_delete_remains_available(self):
        quote = self.create_quote()
        order = Order.objects.create(
            order_no="SO-DELETE-001",
            customer=self.customer,
            order_date=date(2026, 8, 15),
        )

        quote_response = self.client.delete(f"/api/quotes/{quote.id}/")
        order_response = self.client.delete(f"/api/orders/{order.id}/")

        self.assertEqual(quote_response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertTrue(Quote.objects.filter(pk=quote.pk).exists())
        self.assertEqual(order_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Order.objects.filter(pk=order.pk).exists())

    def test_saved_pi_uses_buyer_and_sku_snapshots_after_source_records_change(self):
        upload = SimpleUploadedFile(
            "historical-panel.gif",
            b"GIF87a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;",
            content_type="image/gif",
        )
        upload_response = self.client.post(
            f"/api/skus/{self.sku.id}/image/",
            {"image": upload},
            format="multipart",
        )
        self.assertEqual(upload_response.status_code, status.HTTP_200_OK)
        self.sku.unit = "set"
        self.sku.save(update_fields=["unit"])
        quote = self.create_quote()
        snapshot_image_name = quote.items.get().image_snapshot.name

        self.customer.name = "Renamed Buyer"
        self.customer.save(update_fields=["name"])
        self.sku.sku = "RENAMED-SKU"
        self.sku.unit = "box"
        self.sku.product.name = "Renamed Product"
        self.sku.product.save(update_fields=["name"])
        self.sku.save(update_fields=["sku", "unit"])
        self.client.delete(f"/api/skus/{self.sku.id}/image/")
        revision_response = self.client.post(f"/api/quotes/{quote.id}/revise/", {"revision_summary": "复制快照"}, format="json")
        self.assertEqual(revision_response.status_code, status.HTTP_201_CREATED)

        for quote_id in (quote.id, revision_response.data["id"]):
            with self.subTest(quote_id=quote_id):
                response = self.client.get(f"/api/quotes/{quote_id}/pi-data/")
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(response.data["buyer"]["company_name"], "API Buyer")
                self.assertEqual(response.data["products"][0]["sku"], "SKU-API-001")
                self.assertEqual(response.data["products"][0]["unit"], "set")
                self.assertEqual(response.data["products"][0]["product_name"], "API Panel")
                self.assertIn("/media/quote-item-images/", response.data["products"][0]["image_url"])
        self.assertEqual(quote.items.get().image_snapshot.name, snapshot_image_name)

    def test_pi_data_returns_snapshots_totals_payment_splits_and_product_image_urls(self):
        upload = SimpleUploadedFile(
            "panel.gif",
            b"GIF87a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;",
            content_type="image/gif",
        )
        upload_response = self.client.post(f"/api/skus/{self.sku.id}/image/", {"image": upload}, format="multipart")
        self.assertEqual(upload_response.status_code, status.HTTP_200_OK)
        sku_without_image = SKU.objects.create(product=self.sku.product, sku="SKU-API-NO-IMAGE")
        quote = self.create_quote(
            shipping_fee="12.50",
            discount="5.00",
            deposit_ratio="0.40",
            trading_terms="CIF Hamburg",
            items=[
                {
                    "sku": self.sku.id,
                    "quantity": "2.00",
                    "unit_price": "10.00",
                    "description": "Dimmable panel light",
                },
                {
                    "sku": sku_without_image.id,
                    "quantity": "4.00",
                    "unit_price": "7.50",
                    "description": "Emergency panel light",
                },
            ],
        )

        response = self.client.get(f"/api/quotes/{quote.id}/pi-data/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["invoice_no"], quote.quote_no)
        self.assertEqual(response.data["buyer"]["name"], "Primary Contact")
        self.assertEqual(Decimal(response.data["totals"]["subtotal"]), Decimal("50.00"))
        self.assertEqual(Decimal(response.data["totals"]["shipping_fee"]), Decimal("12.50"))
        self.assertEqual(Decimal(response.data["totals"]["discount"]), Decimal("5.00"))
        self.assertEqual(Decimal(response.data["totals"]["total_amount"]), Decimal("57.50"))
        self.assertEqual(Decimal(response.data["payment_splits"]["deposit_ratio"]), Decimal("0.4000"))
        self.assertEqual(Decimal(response.data["payment_splits"]["deposit_amount"]), Decimal("23.00"))
        self.assertEqual(Decimal(response.data["payment_splits"]["balance_amount"]), Decimal("34.50"))
        self.assertEqual(response.data["products"][0]["description"], "Dimmable panel light")
        self.assertIn("/media/quote-item-images/", response.data["products"][0]["image_url"])
        self.assertEqual(response.data["products"][1]["image_url"], "")

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
        upload_response = self.client.post(f"/api/skus/{self.sku.id}/image/", {"image": upload}, format="multipart")
        self.assertEqual(upload_response.status_code, status.HTTP_200_OK)
        self.sku.refresh_from_db()
        self.assertTrue(self.sku.image)

        response = self.client.delete(f"/api/skus/{self.sku.id}/image/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.sku.refresh_from_db()
        self.assertFalse(self.sku.image)
        self.assertEqual(response.data["image"], None)

    def test_important_notes_are_shared_by_the_revision_chain_and_sanitized(self):
        root = self.create_quote()
        revision_response = self.client.post(f"/api/quotes/{root.id}/revise/", {"revision_summary": "新增沟通备注"}, format="json")
        self.assertEqual(revision_response.status_code, status.HTTP_201_CREATED)
        revision = Quote.objects.get(pk=revision_response.data["id"])

        created = self.client.post(
            f"/api/quotes/{revision.id}/important-notes/",
            {"content": '<p><strong>4000K</strong> confirmed.</p><script>alert("x")</script>'},
            format="json",
        )
        shared = self.client.get(f"/api/quotes/{root.id}/important-notes/")

        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        self.assertEqual(shared.status_code, status.HTTP_200_OK)
        self.assertEqual(len(shared.data), 1)
        self.assertEqual(shared.data[0]["source_quote_no"], revision.quote_no)
        self.assertEqual(shared.data[0]["source_revision_no"], 1)
        self.assertIn("<strong>4000K</strong>", shared.data[0]["content"])
        self.assertNotIn("<script>", shared.data[0]["content"])

    def test_important_note_can_be_deactivated_without_deletion(self):
        quote = self.create_quote()
        created = self.client.post(
            f"/api/quotes/{quote.id}/important-notes/",
            {"content": "<p>Old payment term.</p>"},
            format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)

        response = self.client.post(
            f"/api/quotes/{quote.id}/important-notes/{created.data['id']}/deactivate/",
            format="json",
        )
        notes = self.client.get(f"/api/quotes/{quote.id}/important-notes/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["is_active"])
        self.assertEqual(len(notes.data), 1)
        self.assertFalse(notes.data[0]["is_active"])

    def test_important_note_deactivation_records_operator_and_can_be_restored(self):
        quote = self.create_quote()
        created = self.client.post(
            f"/api/quotes/{quote.id}/important-notes/",
            {"content": "<p>Confirm carton label before production.</p>"},
            format="json",
        )
        operator = get_user_model().objects.create_user(username="note-operator", password="safe-password")
        self.client.force_authenticate(operator)

        deactivated = self.client.post(
            f"/api/quotes/{quote.id}/important-notes/{created.data['id']}/deactivate/",
            format="json",
        )
        restored = self.client.post(
            f"/api/quotes/{quote.id}/important-notes/{created.data['id']}/restore/",
            format="json",
        )

        self.assertEqual(deactivated.status_code, status.HTTP_200_OK)
        self.assertFalse(deactivated.data["is_active"])
        self.assertIsNotNone(deactivated.data["deactivated_at"])
        self.assertEqual(deactivated.data["deactivated_by_name"], "note-operator")
        self.assertEqual(restored.status_code, status.HTTP_200_OK)
        self.assertTrue(restored.data["is_active"])
        self.assertEqual(restored.data["deactivated_at"], deactivated.data["deactivated_at"])
        self.assertEqual(restored.data["deactivated_by_name"], "note-operator")

    def test_important_note_rejects_html_without_visible_text(self):
        quote = self.create_quote()

        response = self.client.post(
            f"/api/quotes/{quote.id}/important-notes/",
            {"content": "<p><br></p>"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("content", response.data)

    def test_workbench_lists_orders_from_every_version_of_the_quote_chain(self):
        root = self.create_quote()
        revision_response = self.client.post(f"/api/quotes/{root.id}/revise/", {"revision_summary": "创建关联订单"}, format="json")
        self.assertEqual(revision_response.status_code, status.HTTP_201_CREATED)
        revision = Quote.objects.get(pk=revision_response.data["id"])
        root_order = Order.objects.create(
            order_no="SO-WORKBENCH-ROOT",
            customer=self.customer,
            quote=root,
            order_date=date(2026, 8, 16),
        )
        revision_order = Order.objects.create(
            order_no="SO-WORKBENCH-REVISION",
            customer=self.customer,
            quote=revision,
            order_date=date(2026, 8, 17),
        )

        response = self.client.get(f"/api/quotes/{revision.id}/workbench/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["root_quote_no"], root.quote_no)
        self.assertEqual({row["order_no"] for row in response.data["orders"]}, {root_order.order_no, revision_order.order_no})
        self.assertEqual(
            {row["source_quote_no"] for row in response.data["orders"]},
            {root.quote_no, revision.quote_no},
        )
        self.assertEqual([row["quote_no"] for row in response.data["revisions"]], [root.quote_no, revision.quote_no])

    def test_order_draft_copies_quote_and_accepts_source_only_after_save(self):
        quote = self.create_quote(
            shipping_fee="12.50",
            discount="2.00",
            notes="Use confirmed carton marks.",
            items=[{
                "sku": self.sku.id,
                "quantity": "3.00",
                "unit_price": "11.25",
                "description": "Dimmable panel light",
            }],
        )

        draft = self.client.get(f"/api/quotes/{quote.id}/order-draft/")

        self.assertEqual(draft.status_code, status.HTTP_200_OK)
        self.assertEqual(draft.data["quote"], quote.id)
        self.assertEqual(draft.data["customer"], self.customer.id)
        self.assertEqual(draft.data["status"], "draft")
        self.assertEqual(Decimal(draft.data["shipping_fee"]), Decimal("12.50"))
        self.assertEqual(draft.data["items"][0]["sku"], self.sku.id)
        self.assertEqual(Decimal(draft.data["items"][0]["quantity"]), Decimal("3.00"))
        self.assertEqual(Decimal(draft.data["items"][0]["unit_price"]), Decimal("11.2500"))

        saved = self.client.post("/api/orders/", draft.data, format="json")
        quote.refresh_from_db()

        self.assertEqual(saved.status_code, status.HTTP_201_CREATED, getattr(saved, "data", None))
        self.assertEqual(saved.data["quote"], quote.id)
        self.assertEqual(quote.status, "accepted")

    def test_order_with_commercial_changes_creates_and_links_quote_revision(self):
        quote = self.create_quote(
            shipping_fee="12.50",
            discount="2.00",
            notes="Use confirmed carton marks.",
            items=[{
                "sku": self.sku.id,
                "quantity": "3.00",
                "unit_price": "11.25",
                "description": "Dimmable panel light",
            }],
        )
        draft = self.client.get(f"/api/quotes/{quote.id}/order-draft/").data
        draft["shipping_fee"] = "18.50"
        draft["items"][0]["quantity"] = "4.00"

        saved = self.client.post("/api/orders/", draft, format="json")

        self.assertEqual(saved.status_code, status.HTTP_201_CREATED, getattr(saved, "data", None))
        order = Order.objects.get(pk=saved.data["id"])
        revision = order.quote
        quote.refresh_from_db()
        self.assertNotEqual(revision.id, quote.id)
        self.assertEqual(revision.parent_quote_id, quote.id)
        self.assertEqual(revision.root_quote_id, quote.id)
        self.assertEqual(revision.revision_no, 1)
        self.assertEqual(revision.status, "accepted")
        self.assertIn("产品明细", revision.revision_summary)
        self.assertIn("运费", revision.revision_summary)
        self.assertEqual(Decimal(revision.shipping_fee), Decimal("18.50"))
        self.assertEqual(Decimal(revision.items.get().quantity), Decimal("4.00"))
        self.assertEqual(revision.items.get().description, "Dimmable panel light")
        self.assertEqual(Decimal(quote.shipping_fee), Decimal("12.50"))
        self.assertEqual(Decimal(quote.items.get().quantity), Decimal("3.00"))
        self.assertEqual(quote.status, "draft")

    def test_invalid_order_with_quote_does_not_accept_the_quote(self):
        quote = self.create_quote()

        response = self.client.post(
            "/api/orders/",
            {
                "order_no": "SO-INVALID-QUOTE",
                "customer": self.customer.id,
                "quote": quote.id,
                "order_date": "2026-08-18",
                "items": [],
            },
            format="json",
        )
        quote.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotEqual(quote.status, "accepted")


class OrderWorkbenchTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = Customer.objects.create(code="C-ORDER-WORKBENCH", name="Order Workbench Buyer", country="Germany")
        product = Product.objects.create(code="P-ORDER-WORKBENCH", name="Order Workbench Light")
        self.sku = SKU.objects.create(product=product, sku="SKU-ORDER-WORKBENCH", default_price="15.00", cost_price="7.00")
        self.quote = Quote.objects.create(quote_no="SJ20260819DE001", customer=self.customer, quote_date=date(2026, 8, 19))
        self.order = Order.objects.create(
            order_no="SO-ORDER-WORKBENCH",
            customer=self.customer,
            quote=self.quote,
            order_date=date(2026, 8, 19),
            expected_ship_date=date(2026, 9, 3),
            status="production",
        )
        self.order.items.create(sku=self.sku, quantity="3.00", unit_price="15.00", cost_price="7.00")

    def test_workbench_returns_order_fulfillment_and_payment_context(self):
        Transaction.objects.create(
            transaction_no="TX-ORDER-WORKBENCH",
            transaction_date=date(2026, 8, 20),
            direction="income",
            category="订单定金",
            amount="20.00",
            customer=self.customer,
            order=self.order,
        )
        InventoryMovement.objects.create(
            movement_no="IM-ORDER-WORKBENCH",
            movement_date=date(2026, 8, 21),
            type="sale_out",
            sku=self.sku,
            order=self.order,
            quantity="1.00",
            warehouse="中山成品仓",
        )

        response = self.client.get(f"/api/orders/{self.order.id}/workbench/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["order"]["order_no"], self.order.order_no)
        self.assertEqual(response.data["source_quote"]["quote_no"], self.quote.quote_no)
        self.assertEqual(response.data["items"][0]["sku_code"], self.sku.sku)
        self.assertEqual(response.data["payments"][0]["transaction_no"], "TX-ORDER-WORKBENCH")
        self.assertEqual(response.data["payments"][0].get("status_display"), "已确认")
        self.assertEqual(response.data["inventory"][0]["movement_no"], "IM-ORDER-WORKBENCH")
        self.assertEqual(Decimal(response.data["payment_summary"]["paid_amount"]), Decimal("20.00"))
        self.assertEqual(Decimal(response.data["fulfillment_summary"]["shipped_quantity"]), Decimal("1.00"))


class QuoteExportTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(username="quote-exporter", password="test-pass")
        self.client.force_authenticate(self.user)
        self.customer = Customer.objects.create(
            code="C-EXPORT-001",
            name="Export Buyer GmbH",
            country="Germany",
            address="Berlin, Germany",
        )
        self.product = Product.objects.create(code="P-EXPORT-001", name="Export Panel")
        self.sku_1 = SKU.objects.create(product=self.product, sku="SKU-001", sales_model="MODEL-001", unit="pcs")
        self.sku_2 = SKU.objects.create(product=self.product, sku="SKU-002", sales_model="MODEL-002", unit="pcs")
        self.sku_3 = SKU.objects.create(product=self.product, sku="SKU-003", sales_model="MODEL-003", unit="pcs")
        self.sku_4 = SKU.objects.create(product=self.product, sku="SKU-004", sales_model="MODEL-004", unit="pcs")
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
        create_quote_items(quote, [
            {
                "sku": sku,
                "description": description,
                "quantity": Decimal(quantity),
                "unit_price": Decimal(unit_price),
            }
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
        revisions = [self.create_revision(self.multi_item_quote), self.create_revision(self.multi_item_quote)]

        for revision_number, revision in enumerate(revisions, start=1):
            with self.subTest(revision_number=revision_number):
                response = self.client.get(f"/api/quotes/{revision.id}/export/")

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(
                    response["Content-Disposition"],
                    f'attachment; filename="{self.multi_item_quote.quote_no}-{revision_number}.xlsx"',
                )
                self.assertTrue(response.content.startswith(b"PK"))
                self.assertEqual(xlsx_cell_text(response.content, "L9"), revision.quote_no)

    @override_settings(DEBUG=False)
    def test_export_requires_authentication_and_allows_authenticated_operator_in_production(self):
        anonymous = APIClient()

        denied = anonymous.get(f"/api/quotes/{self.multi_item_quote.id}/export/")
        allowed = self.client.get(f"/api/quotes/{self.multi_item_quote.id}/export/")

        self.assertEqual(denied.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(allowed.status_code, status.HTTP_200_OK)

    @override_settings(DEBUG=True)
    def test_export_allows_anonymous_operator_in_development(self):
        response = APIClient().get(f"/api/quotes/{self.multi_item_quote.id}/export/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_export_uses_saved_buyer_and_sku_snapshots_after_sources_change(self):
        self.customer.name = "Renamed Export Buyer"
        self.customer.save(update_fields=["name"])
        self.sku_1.sku = "RENAMED-SKU"
        self.sku_1.unit = "box"
        self.sku_1.save(update_fields=["sku", "unit"])

        response = self.client.get(f"/api/quotes/{self.multi_item_quote.id}/export/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(xlsx_cell_text(response.content, "B3"), "Export Buyer GmbH")
        self.assertEqual(xlsx_cell_text(response.content, "C11"), "MODEL-001")
        self.assertEqual(xlsx_cell_text(response.content, "K11"), "pcs")

    def test_export_uses_selected_currency_in_both_price_headers(self):
        for currency in ("USD", "CNY", "EUR", "GBP"):
            with self.subTest(currency=currency):
                self.multi_item_quote.currency = currency
                self.multi_item_quote.save(update_fields=["currency"])

                response = self.client.get(f"/api/quotes/{self.multi_item_quote.id}/export/")

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(xlsx_cell_text(response.content, "L10"), f"Unit Price\n{currency}")
                self.assertEqual(xlsx_cell_text(response.content, "M10"), f"Total\n{currency}")

    def test_export_uses_validity_days_40_percent_deposit_and_non_default_terms(self):
        self.multi_item_quote.valid_until = date(2026, 8, 22)
        self.multi_item_quote.deposit_ratio = Decimal("0.4000")
        self.multi_item_quote.trading_terms = "CIF Hamburg"
        self.multi_item_quote.shipping_details = "DHL air freight"
        self.multi_item_quote.save(update_fields=[
            "valid_until", "deposit_ratio", "trading_terms", "shipping_details",
        ])

        response = self.client.get(f"/api/quotes/{self.multi_item_quote.id}/export/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        notes = xlsx_cell_text(response.content, "A17")
        self.assertIn("Price Valid Date: 7 Days.", notes)
        self.assertIn("40% (USD 24.60) payment in advance", notes)
        self.assertIn("Trading terms: CIF Hamburg", notes)
        self.assertIn("Shipping details: DHL air freight", notes)

    def test_export_two_items_contains_sku_codes_and_arial_style(self):
        response = self.client.get(f"/api/quotes/{self.multi_item_quote.id}/export/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        sheet_xml = unzip_member(response.content, "xl/worksheets/sheet1.xml")
        self.assertIn(b"MODEL-001", sheet_xml)
        self.assertIn(b"MODEL-002", sheet_xml)
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
        self.assertEqual(xlsx_cell_text(response.content, "A24"), "BANK INFORMATION")
        self.assertEqual(xlsx_cell_text(response.content, "I3"), "Guangzhou Sunjack Lighting Co., Ltd.")
        self.assertEqual(xlsx_cell_text(response.content, "C25"), "Guangzhou Sunjack Lighting Co., Ltd.")
        self.assertEqual(xlsx_cell_text(response.content, "A32"), "Bank Code")
        self.assertEqual(xlsx_cell_text(response.content, "C32"), "007")
        self.assertEqual(xlsx_cell_text(response.content, "A33"), "Branch Code")
        self.assertTrue(xlsx_cell_text(response.content, "A34").startswith("IMPORTANT NOTICE"))

    def test_export_uses_no_discount_template_when_discount_is_zero(self):
        self.multi_item_quote.discount = Decimal("0.00")
        self.multi_item_quote.save(update_fields=["discount"])

        response = self.client.get(f"/api/quotes/{self.multi_item_quote.id}/export/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(xlsx_cell_text(response.content, "A14"), "Sub Total")
        self.assertTrue(xlsx_cell_text(response.content, "A16").startswith("NOTES:"))
        self.assertEqual(xlsx_cell_text(response.content, "A21"), "BANK INFORMATION")

    def test_export_uses_discount_template_and_writes_discount_amount(self):
        response = self.client.get(f"/api/quotes/{self.multi_item_quote.id}/export/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(xlsx_cell_text(response.content, "A14"), "Discount")
        self.assertEqual(Decimal(xlsx_cell_text(response.content, "M14")), Decimal("1.00"))
        self.assertEqual(xlsx_cell_text(response.content, "A15"), "Sub Total")
        self.assertTrue(xlsx_cell_text(response.content, "A17").startswith("NOTES:"))
        self.assertEqual(xlsx_cell_text(response.content, "A22"), "BANK INFORMATION")

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
        failure_client.force_authenticate(self.user)
        failure_client.raise_request_exception = False

        response = failure_client.get(f"/api/quotes/{before.id}/export/")

        after = Quote.objects.get(pk=before.pk)
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertEqual(after.updated_at, before.updated_at)
        self.assertEqual(after.quote_no, before.quote_no)
