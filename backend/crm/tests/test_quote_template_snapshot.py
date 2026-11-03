from copy import deepcopy
from hashlib import sha256
import json
from datetime import date
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from shutil import copy2
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.db import connection, IntegrityError
from django.test import SimpleTestCase, TestCase
from openpyxl import load_workbook
from rest_framework.test import APIClient

from crm.models import Customer, Product, Quote, QuoteTemplateAsset, SKU
from crm.quote_snapshots import create_quote_items
from crm.quotation_template_config import quotation_templates

from crm.quote_template_snapshot import (
    QuoteTemplateSnapshotError,
    capture_template,
    validated_template_bytes,
)


class QuoteTemplateCaptureTests(SimpleTestCase):
    def test_capture_preserves_bytes_digest_and_seller_for_both_templates(self):
        for template_id in ("standard_en_no_discount", "standard_en_with_discount"):
            with self.subTest(template_id=template_id):
                snapshot = capture_template(template_id)
                content = validated_template_bytes(snapshot)
                self.assertEqual(sha256(content).hexdigest(), snapshot["sha256"])
                self.assertTrue(snapshot["seller"]["name"])
                self.assertEqual(len(snapshot["bank"]), 9)
                self.assertEqual(snapshot["template_id"], template_id)

    def test_corrupt_bytes_or_missing_seller_are_rejected(self):
        original = capture_template("standard_en_no_discount")
        for field, value in (("bytes_base64", "aGVsbG8="), ("seller", {}), ("notice", "altered")):
            with self.subTest(field=field):
                snapshot = deepcopy(original)
                snapshot[field] = value
                with self.assertRaises(QuoteTemplateSnapshotError):
                    validated_template_bytes(snapshot)

    def test_unknown_template_fails_closed(self):
        with self.assertRaises(QuoteTemplateSnapshotError):
            capture_template("unknown")


class QuoteTemplateIntegrationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = Customer.objects.create(code="FREEZE-C", name="Synthetic Buyer", country="Germany")
        product = Product.objects.create(code="FREEZE-P", name="Synthetic Product")
        sku = SKU.objects.create(product=product, sku="FREEZE-S", sales_model="FREEZE-M")
        self.quote = Quote.objects.create(quote_no="FREEZE-Q", customer=self.customer, quote_date=date(2026, 1, 1))
        create_quote_items(self.quote, [{"sku": sku, "quantity": 1, "unit_price": 10}])

    def test_draft_preview_uses_current_template_only_for_new_quote(self):
        expected = self.client.get(f"/api/quotes/{self.quote.pk}/pi-data/").data["seller"]
        with patch("crm.quote_template_snapshot.capture_template", side_effect=QuoteTemplateSnapshotError("unavailable")):
            revised = self.client.get("/api/quotes/preview-template/", {"quote_id": self.quote.pk})
            new = self.client.get("/api/quotes/preview-template/")
        self.assertEqual(revised.status_code, 200)
        self.assertEqual(revised.data["seller"], expected)
        self.assertEqual(new.status_code, 422)
        Quote.objects.filter(pk=self.quote.pk).update(pi_template_snapshots={})
        self.assertEqual(self.client.get("/api/quotes/preview-template/", {"quote_id": self.quote.pk}).status_code, 422)
        self.assertEqual(self.client.get("/api/quotes/preview-template/", {"quote_id": 999999}).status_code, 404)

    def test_saved_api_and_workbook_ignore_current_template_changes(self):
        before = self.client.get(f"/api/quotes/{self.quote.pk}/pi-data/")
        first = self.client.get(f"/api/quotes/{self.quote.pk}/export/")
        self.assertEqual((before.status_code, first.status_code), (200, 200))
        first_seller = load_workbook(BytesIO(first.content))["PI"]["I3"].value
        with patch("crm.quotation_template_config.quotation_templates", {}):
            after = self.client.get(f"/api/quotes/{self.quote.pk}/pi-data/")
            second = self.client.get(f"/api/quotes/{self.quote.pk}/export/")
        self.assertEqual((after.status_code, second.status_code), (200, 200))
        self.assertEqual(before.data["seller"], after.data["seller"])
        self.assertEqual(first_seller, load_workbook(BytesIO(second.content))["PI"]["I3"].value)
        self.assertEqual(first_seller, before.data["seller"]["name"])

    def test_historical_unknown_and_corruption_fail_closed(self):
        Quote.objects.filter(pk=self.quote.pk).update(pi_template_snapshots={})
        for path in ("pi-data", "export"):
            self.assertEqual(self.client.get(f"/api/quotes/{self.quote.pk}/{path}/").status_code, 422)
        self.assertEqual(self.client.post(f"/api/quotes/{self.quote.pk}/mark-sent/").status_code, 422)
        self.quote.refresh_from_db()
        self.assertEqual(self.quote.status, "draft")
        revision = self.client.post(f"/api/quotes/{self.quote.pk}/revise/", {"revision_summary": "Synthetic"}, format="json")
        self.assertEqual(revision.status_code, 201)
        self.assertEqual(Quote.objects.get(pk=revision.data["id"]).pi_template_snapshots, {})
        self.assertEqual(self.client.get(f"/api/quotes/{revision.data['id']}/export/").status_code, 422)

    def test_saved_template_cannot_be_changed_by_model_save(self):
        self.quote.pi_template_snapshots = {}
        with self.assertRaises(ValidationError):
            self.quote.save()

    def test_resources_are_shared_and_corruption_is_rejected(self):
        other = Quote.objects.create(quote_no="FREEZE-SHARED", customer=self.customer, quote_date=date(2026, 1, 2))
        self.assertEqual(self.quote.pi_template_snapshots, other.pi_template_snapshots)
        self.assertEqual(QuoteTemplateAsset.objects.count(), 2)
        digest = self.quote.pi_template_snapshots["standard_en_no_discount"]
        asset = QuoteTemplateAsset.objects.get(pk=digest)
        changed = deepcopy(asset.snapshot)
        changed["print_template"] += "corruption"
        with self.assertRaises(ValidationError):
            QuoteTemplateAsset.objects.filter(pk=digest).update(snapshot=changed)
        with connection.cursor() as cursor:
            cursor.execute("UPDATE crm_quotetemplateasset SET snapshot = %s WHERE digest = %s", [json.dumps(changed), digest])
        for path in ("pi-data", "export"):
            self.assertEqual(self.client.get(f"/api/quotes/{self.quote.pk}/{path}/").status_code, 422)

    def test_new_quote_uses_new_template_but_old_quote_keeps_original(self):
        from crm.quote_template_snapshot import PROJECT_ROOT

        old = self.client.get(f"/api/quotes/{self.quote.pk}/pi-data/")
        with TemporaryDirectory(prefix="quote-template-") as directory:
            root = Path(directory)
            for config in quotation_templates.values():
                destination = root / config.file
                destination.parent.mkdir(parents=True, exist_ok=True)
                copy2(PROJECT_ROOT / config.file, destination)
                workbook = load_workbook(destination)
                workbook[config.sheet]["I3"] = "NEW SYNTHETIC SELLER"
                workbook.save(destination)
            from crm.quote_template_snapshot import PRINT_TEMPLATE_PATH
            print_template = root / "print.html"
            print_template.write_text(PRINT_TEMPLATE_PATH.read_text(encoding="utf-8").replace("Proforma Invoice", "SYNTHETIC NEW PRINT VERSION"), encoding="utf-8")
            with patch("crm.quote_template_snapshot.PROJECT_ROOT", root), patch("crm.quote_template_snapshot.PRINT_TEMPLATE_PATH", print_template):
                fresh = Quote.objects.create(quote_no="FREEZE-NEW", customer=self.customer, quote_date=date(2026, 1, 2))
                fresh.items.create(sku=self.quote.items.first().sku, quantity=1, unit_price=10)
                current = self.client.get(f"/api/quotes/{fresh.pk}/pi-data/")
                repeated = self.client.get(f"/api/quotes/{self.quote.pk}/pi-data/")
                exported = self.client.get(f"/api/quotes/{self.quote.pk}/export/")
        self.assertEqual(current.status_code, 200)
        self.assertEqual(current.data["seller"]["name"], "NEW SYNTHETIC SELLER")
        self.assertIn("SYNTHETIC NEW PRINT VERSION", current.data["print_html"])
        self.assertEqual(repeated.data["print_html"], old.data["print_html"])
        self.assertEqual(repeated.data["seller"], old.data["seller"])
        self.assertEqual(load_workbook(BytesIO(exported.content))["PI"]["I3"].value, old.data["seller"]["name"])

    def test_revision_inherits_saved_resource_references(self):
        response = self.client.post(f"/api/quotes/{self.quote.pk}/revise/", {"revision_summary": "Synthetic revision"}, format="json")
        self.assertEqual(response.status_code, 201)
        revision = Quote.objects.get(pk=response.data["id"])
        self.assertEqual(revision.pi_template_snapshots, self.quote.pi_template_snapshots)
        preview = self.client.get(f"/api/quotes/{revision.pk}/pi-data/")
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(preview.data["seller"], self.client.get(f"/api/quotes/{self.quote.pk}/pi-data/").data["seller"])

    def test_failed_quote_insert_rolls_back_new_assets(self):
        from crm.quote_template_snapshot import PRINT_TEMPLATE_PATH
        with TemporaryDirectory(prefix="quote-rollback-") as directory:
            template = Path(directory) / "print.html"
            template.write_text(PRINT_TEMPLATE_PATH.read_text(encoding="utf-8") + "\n<!-- synthetic version -->", encoding="utf-8")
            with patch("crm.quote_template_snapshot.PRINT_TEMPLATE_PATH", template):
                with self.assertRaises(IntegrityError):
                    Quote.objects.create(quote_no=self.quote.quote_no, customer=self.customer, quote_date=date(2026, 1, 1))
        self.assertEqual(QuoteTemplateAsset.objects.count(), 2)
