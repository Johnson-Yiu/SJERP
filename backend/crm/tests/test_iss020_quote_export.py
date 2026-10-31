import io
import tempfile
import zipfile
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.test import override_settings
from openpyxl import load_workbook
from PIL import Image as PILImage
from rest_framework.test import APIClient

from crm.models import Customer, Order, PaymentPlan, Product, Quote, SKU
from crm.quote_snapshots import create_quote_items


class ISS020QuoteExportConsistencyTests(TestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp(prefix="iss020-media-")
        self.media_settings = override_settings(MEDIA_ROOT=self.media_root)
        self.media_settings.enable()
        self.addCleanup(self.media_settings.disable)
        self.client = APIClient()
        self.client.force_authenticate(get_user_model().objects.create_user(username="iss020-export"))
        self.customer = Customer.objects.create(code="ISS020-CUSTOMER", name="ISS-020 Buyer", country="Germany")
        self.product = Product.objects.create(code="ISS020-PRODUCT", name="ISS-020 Product")
        self.skus = [
            SKU.objects.create(product=self.product, sku=f"ISS020-SKU-{index}", sales_model=f"ISS020-MODEL-{index}")
            for index in (1, 2)
        ]

    def make_quote(self, *, buyer_company_name="ISS-020 Buyer", currency="USD", rows=None, quote_no="ISS020-EXPORT"):
        quote = Quote.objects.create(
            quote_no=quote_no,
            customer=self.customer,
            buyer_company_name=buyer_company_name,
            recipient_name="ISS-020 Recipient",
            buyer_address="ISS-020 Address",
            currency=currency,
            quote_date=date(2026, 10, 26),
            shipping_fee=Decimal("0.00"),
            discount=Decimal("0.00"),
        )
        create_quote_items(quote, rows or [
            {"sku": self.skus[0], "quantity": Decimal("1.00"), "unit_price": Decimal("10.00"), "description": "Line 1"},
        ])
        return quote

    def test_legacy_formal_quote_and_sales_order_keep_pre_iss020_amounts(self):
        rows = [
            {"sku": self.skus[0], "quantity": Decimal("1.00"), "unit_price": Decimal("1.005"), "description": "Line 1"},
            {"sku": self.skus[1], "quantity": Decimal("1.00"), "unit_price": Decimal("1.005"), "description": "Line 2"},
        ]
        legacy_quote = self.make_quote(rows=rows, quote_no="ISS020-HISTORY-QUOTE")
        Quote.objects.filter(pk=legacy_quote.pk).update(status="accepted", amount_calculation_version=1)
        legacy_quote.refresh_from_db()

        self.assertEqual(legacy_quote.total_amount, Decimal("2.010"))
        detail = self.client.get(f"/api/quotes/{legacy_quote.pk}/")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(Decimal(detail.data["total_amount"]), Decimal("2.01"))
        preview = self.client.get(f"/api/quotes/{legacy_quote.pk}/pi-data/")
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(Decimal(preview.data["totals"]["subtotal"]), Decimal("2.01"))
        self.assertEqual(Decimal(preview.data["totals"]["total_amount"]), Decimal("2.01"))

        legacy_order = Order.objects.create(
            order_no="ISS020-HISTORY-ORDER",
            customer=self.customer,
            order_date=date(2026, 10, 26),
            status="confirmed",
            currency="USD",
        )
        for row in rows:
            legacy_order.items.create(sku=row["sku"], quantity=row["quantity"], unit_price=row["unit_price"])
        PaymentPlan.objects.create(
            order=legacy_order,
            direction="receivable",
            currency="USD",
            planned_amount=Decimal("2.0100"),
        )
        Order.objects.filter(pk=legacy_order.pk).update(amount_calculation_version=1)
        legacy_order.refresh_from_db()

        self.assertEqual(legacy_order.base_amount, Decimal("2.010"))
        self.assertEqual(legacy_order.total_amount, Decimal("2.010"))
        self.assertEqual(
            sum(legacy_order.payment_plans.values_list("planned_amount", flat=True), Decimal("0")),
            Decimal("2.0100"),
        )

        current_order = Order.objects.create(
            order_no="ISS020-CURRENT-ORDER",
            customer=self.customer,
            order_date=date(2026, 10, 26),
            status="draft",
            currency="USD",
        )
        for row in rows:
            current_order.items.create(sku=row["sku"], quantity=row["quantity"], unit_price=row["unit_price"])
        self.assertEqual(current_order.amount_calculation_version, 2)
        self.assertEqual(current_order.total_amount, Decimal("2.02"))

    def test_quantity_change_uses_current_cent_rule_without_mutating_legacy_payment_plan(self):
        order = Order.objects.create(
            order_no="ISS020-HISTORY-QTY",
            customer=self.customer,
            order_date=date(2026, 10, 26),
            status="confirmed",
            currency="USD",
        )
        item = order.items.create(sku=self.skus[0], quantity=Decimal("1.00"), unit_price=Decimal("1.005"))
        plan = PaymentPlan.objects.create(
            order=order,
            direction="receivable",
            currency="USD",
            planned_amount=Decimal("1.0050"),
        )
        Order.objects.filter(pk=order.pk).update(amount_calculation_version=1)
        order.refresh_from_db()

        from crm.services.order_quantity_adjustments import preview_quantity_adjustment

        preview = preview_quantity_adjustment(order, {
            "version": order.quantity_change_version,
            "request_key": "iss020-history-qty",
            "reason": "兼容性核对",
            "items": [{"order_item": item.pk, "new_quantity": "2.00"}],
        })
        self.assertEqual(preview["financial"]["before_total"], "1.0050")
        self.assertEqual(preview["financial"]["after_total"], "2.0100")
        plan.refresh_from_db()
        self.assertEqual(plan.planned_amount, Decimal("1.0050"))

    def test_formal_export_rejects_missing_saved_critical_fields_without_file(self):
        quote = self.make_quote(buyer_company_name="", currency="")
        # Simulate a legacy/incomplete saved revision without triggering Quote.save defaults.
        Quote.objects.filter(pk=quote.pk).update(buyer_company_name="", currency="")

        response = self.client.get(f"/api/quotes/{quote.pk}/export/")

        self.assertEqual(response.status_code, 422)
        self.assertIn("buyer_company_name", response.data["fields"])
        self.assertIn("currency", response.data["fields"])
        self.assertNotEqual(response.get("Content-Type"), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        preview = self.client.get(f"/api/quotes/{quote.pk}/pi-data/")
        self.assertEqual(preview.status_code, 422)
        self.assertIn("buyer_company_name", preview.data["fields"])

    def test_formal_export_amount_words_match_the_saved_currency_and_total(self):
        quote = self.make_quote(rows=[
            {"sku": self.skus[0], "quantity": Decimal("1.00"), "unit_price": Decimal("246.00"), "description": "Line 1"},
        ])

        response = self.client.get(f"/api/quotes/{quote.pk}/export/")
        self.assertEqual(response.status_code, 200)
        sheet = load_workbook(io.BytesIO(response.content), data_only=False)["PI"]
        self.assertEqual(sheet["A15"].value, "SAY TOTAL US DOLLARS TWO HUNDRED FORTY SIX ONLY")
        self.assertNotIn("undefined", str(sheet["A15"].value).lower())

    def test_formal_export_totals_reconcile_with_displayed_line_amounts(self):
        quote = self.make_quote(rows=[
            {"sku": self.skus[0], "quantity": Decimal("1.00"), "unit_price": Decimal("1.005"), "description": "Line 1"},
            {"sku": self.skus[1], "quantity": Decimal("1.00"), "unit_price": Decimal("1.005"), "description": "Line 2"},
        ])

        response = self.client.get(f"/api/quotes/{quote.pk}/export/")
        self.assertEqual(response.status_code, 200)
        sheet = load_workbook(io.BytesIO(response.content), data_only=False)["PI"]
        displayed_line_total = sum(Decimal(str(sheet[f"M{row}"].value)) for row in (11, 12))
        displayed_subtotal = Decimal(str(sheet["M14"].value))
        self.assertEqual(displayed_line_total, displayed_subtotal)

        preview = self.client.get(f"/api/quotes/{quote.pk}/pi-data/")
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(Decimal(preview.data["totals"]["subtotal"]), displayed_subtotal)
        self.assertEqual(sum(Decimal(row["amount"]) for row in preview.data["products"]), displayed_subtotal)

    def test_three_decimal_prices_use_one_cent_rule_across_quote_pi_xlsx_and_order(self):
        quote = self.make_quote(
            currency="EUR",
            rows=[
                {"sku": self.skus[0], "quantity": Decimal("1.00"), "unit_price": Decimal("1.005"), "description": "Line 1"},
                {"sku": self.skus[1], "quantity": Decimal("1.00"), "unit_price": Decimal("1.005"), "description": "Line 2"},
            ],
        )
        quote.shipping_fee = Decimal("0.025")
        quote.discount = Decimal("0.005")
        quote.save(update_fields=["shipping_fee", "discount"])

        expected = Decimal("2.04")  # 1.01 + 1.01 + 0.03 - 0.01
        quote.refresh_from_db()
        self.assertEqual(quote.total_amount, expected)

        detail = self.client.get(f"/api/quotes/{quote.pk}/")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(Decimal(detail.data["total_amount"]), expected)

        preview = self.client.get(f"/api/quotes/{quote.pk}/pi-data/")
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(Decimal(preview.data["totals"]["subtotal"]), Decimal("2.02"))
        self.assertEqual(Decimal(preview.data["totals"]["total_amount"]), expected)
        self.assertEqual(sum(Decimal(row["amount"]) for row in preview.data["products"]), Decimal("2.02"))

        exported = self.client.get(f"/api/quotes/{quote.pk}/export/")
        self.assertEqual(exported.status_code, 200)
        sheet = load_workbook(io.BytesIO(exported.content), data_only=False)["PI"]
        self.assertEqual(Decimal(str(sheet["M13"].value)), Decimal("0.03"))
        self.assertEqual(Decimal(str(sheet["M14"].value)), Decimal("0.01"))
        self.assertEqual(Decimal(str(sheet["M15"].value)), expected)

        draft = self.client.get(f"/api/quotes/{quote.pk}/order-draft/")
        self.assertEqual(draft.status_code, 200)
        created = self.client.post("/api/orders/", draft.data, format="json")
        self.assertEqual(created.status_code, 201, created.data)
        order = Order.objects.get(pk=created.data["id"])
        self.assertEqual(order.total_amount, expected)
        self.assertEqual(Decimal(created.data["total_amount"]), expected)

    def test_formal_export_embeds_the_saved_image_snapshot(self):
        image_bytes = io.BytesIO()
        PILImage.new("RGB", (16, 16), "red").save(image_bytes, format="PNG")
        upload = SimpleUploadedFile(
            "iss020-image.png",
            image_bytes.getvalue(),
            content_type="image/png",
        )
        upload_response = self.client.post(f"/api/skus/{self.skus[0].pk}/image/", {"image": upload}, format="multipart")
        self.assertEqual(upload_response.status_code, 200, upload_response.data)
        self.skus[0].refresh_from_db()
        quote = self.make_quote()
        self.assertTrue(quote.items.get().image_snapshot.name)
        self.assertTrue(quote.items.get().image_snapshot.path)

        self.skus[0].image.delete(save=False)
        self.skus[0].save(update_fields=["image"])
        response = self.client.get(f"/api/quotes/{quote.pk}/export/")

        self.assertEqual(response.status_code, 200)
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            self.assertTrue(any(name.startswith("xl/media/") for name in archive.namelist()))
