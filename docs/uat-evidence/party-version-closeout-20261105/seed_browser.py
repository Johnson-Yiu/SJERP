"""Create synthetic buyer and seller snapshots inside the isolated runner only."""
import json
import os
from datetime import date
from pathlib import Path
from shutil import copy2
from unittest.mock import patch
from uuid import uuid4

import django
from openpyxl import load_workbook
from openpyxl.packaging.core import DocumentProperties
from openpyxl.packaging.custom import CustomPropertyList

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "test_support.isolated_settings")
django.setup()
from django.conf import settings
from crm.models import Customer, Product, Quote, SKU
from crm.quote_snapshots import create_quote_items
from crm.quote_template_snapshot import PROJECT_ROOT
from crm.quotation_template_config import quotation_templates
from test_support.isolated_runtime import verify_isolated_runtime

verify_isolated_runtime(settings=settings, database_must_exist=True)
suffix = uuid4().hex[:8].upper()
customer = Customer.objects.create(code=f"PVS-{suffix}", name=f"Synthetic Buyer {suffix}", country="Germany")
product = Product.objects.create(code=f"PVS-{suffix}", name="Synthetic Product")
sku = SKU.objects.create(product=product, sku=f"PVS-{suffix}", sales_model=f"PVS-{suffix}")
root = Path(os.environ["ISOLATED_TEST_ROOT"]) / f"synthetic-templates-{suffix}"
for config in quotation_templates.values():
    target = root / config.file
    target.parent.mkdir(parents=True, exist_ok=True)
    copy2(PROJECT_ROOT / config.file, target)
    workbook = load_workbook(target)
    workbook.properties = DocumentProperties(creator="Synthetic test", lastModifiedBy="Synthetic test")
    workbook.custom_doc_props = CustomPropertyList()
    for worksheet in workbook.worksheets:
        worksheet._images = []
    sheet = workbook[config.sheet]
    for row, value in enumerate(("Synthetic Seller", "Synthetic Contact", "Synthetic Address", "synthetic@example.invalid", "+00 000000"), start=3):
        sheet[f"I{row}"] = value
    first = config.lower_block.rows["bank_header"] + 1
    for row in range(first, first + 9):
        sheet[f"C{row}"] = f"SYNTHETIC-{row}"
    sheet[f"A{first + 9}"] = "Synthetic notice"
    workbook.save(target)
with patch("crm.quote_template_snapshot.PROJECT_ROOT", root):
    quote = Quote.objects.create(quote_no=f"PVS-{suffix}", customer=customer,
                                 quote_date=date(2026, 11, 5), buyer_tax_id="00123-SYNTHETIC")
create_quote_items(quote, [{"sku": sku, "quantity": 1, "unit_price": 10}])
print(json.dumps({"id": quote.pk, "quote_no": quote.quote_no}))
