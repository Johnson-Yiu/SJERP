"""Evidence probes assert observed gaps, not acceptance of the requested rules."""
from dataclasses import replace
from datetime import date
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.test import TestCase
from openpyxl import load_workbook
from rest_framework.test import APIClient

from crm.models import Customer, Product, Quote, SKU
from crm.quotation_export_dto import build_quotation_export_dto
from crm.quotation_template_config import quotation_templates
from crm.quote_export import build_pi_export_payload
from crm.quote_xlsx_renderer import PROJECT_ROOT


class SnapshotGapProbes(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create(code="AUDIT037", name="OLD BUYER", country="Germany")
        product = Product.objects.create(code="AUDIT037", name="Audit product")
        self.sku = SKU.objects.create(product=product, sku="AUDIT037", default_price="10")
        self.quote = Quote.objects.create(quote_no="SJ20261103DE901", customer=self.customer,
                                          quote_date=date(2026, 11, 3), status="sent",
                                          recipient_name="OLD RECIPIENT", buyer_address="OLD ADDRESS")
        self.quote.items.create(sku=self.sku, quantity="1", unit_price="10")

    def test_legacy_unknown_buyer_is_replaced_on_revision(self):
        Quote.objects.filter(pk=self.quote.pk).update(buyer_company_name="")
        self.customer.name = "CURRENT MASTER NOT HISTORICAL"
        self.customer.save(update_fields=["name"])
        response = APIClient().post(f"/api/quotes/{self.quote.pk}/revise/",
                                    {"revision_summary": "仅修改说明"}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.quote.refresh_from_db()
        revision = Quote.objects.get(pk=response.data["id"])
        self.assertEqual(self.quote.buyer_company_name, "")
        self.assertEqual(revision.buyer_company_name, self.customer.name)
        self.assertEqual(build_quotation_export_dto(revision).buyer["company_name"], self.customer.name)
        print("GAP_LEGACY_REVISION", {"source": self.quote.buyer_company_name,
                                      "revision": revision.buyer_company_name})

    def test_buyer_company_cannot_be_changed_through_revision(self):
        response = APIClient().post(f"/api/quotes/{self.quote.pk}/revise/",
                                    {"revision_summary": "主体名称修订", "buyer_company_name": "NEW LEGAL BUYER"},
                                    format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["buyer_company_name"], "OLD BUYER")
        print("GAP_PARTY_REVISION_READONLY", response.data["buyer_company_name"])

    def test_same_saved_quote_reexport_uses_current_template_seller(self):
        config = quotation_templates["standard_en_no_discount"]
        workbook = load_workbook(PROJECT_ROOT / config.file)
        sheet = workbook[config.sheet]
        print("TEMPLATE_STATIC_HEADER", [(cell.coordinate, cell.value)
                                          for row in sheet.iter_rows(min_row=1, max_row=7)
                                          for cell in row if cell.value])
        # Modify only a new template copy in the isolated MEDIA_ROOT.
        target = next(cell.coordinate for row in sheet.iter_rows(min_row=1, max_row=7)
                      for cell in row if isinstance(cell.value, str) and "SUNJACK" in cell.value.upper())
        original = load_workbook(BytesIO(build_pi_export_payload(self.quote)))[config.sheet][target].value
        sheet[target] = "CHANGED TEMPLATE SELLER"
        copied = Path(settings.MEDIA_ROOT) / "audit-template-copy.xlsx"
        workbook.save(copied)
        with patch.dict(quotation_templates, {"standard_en_no_discount": replace(config, file=str(copied))}):
            changed = load_workbook(BytesIO(build_pi_export_payload(self.quote)))[config.sheet][target].value
        self.assertNotEqual(original, changed)
        self.assertEqual(changed, "CHANGED TEMPLATE SELLER")
        self.quote.refresh_from_db()
        print("GAP_SELLER_TEMPLATE_DRIFT", {"cell": target, "old": original, "new": changed,
                                            "quote": self.quote.quote_no})
