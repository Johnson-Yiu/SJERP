"""Synthetic quote, users and sanitized template bytes for one isolated run."""
import json
import os
from datetime import date
from pathlib import Path
from shutil import copy2
from uuid import uuid4
import django
from openpyxl import load_workbook
from openpyxl.packaging.core import DocumentProperties
from openpyxl.packaging.custom import CustomPropertyList

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'test_support.isolated_settings')
django.setup()
from django.conf import settings
from django.contrib.auth import get_user_model
from crm.models import Customer, Product, Quote, SKU
from crm.quote_snapshots import create_quote_items
from crm.quote_template_snapshot import PROJECT_ROOT
from crm.quotation_template_config import quotation_templates
from test_support.isolated_runtime import verify_isolated_runtime

verify_isolated_runtime(settings=settings, database_must_exist=True)
if os.environ.get('ISOLATED_PLAYWRIGHT_TEST_FILE') != 'party-replacement-quote-real.spec.js':
    raise RuntimeError('Only the dedicated isolated replacement browser test may use this seed.')
source_root = Path(__file__).resolve().parents[3]
for config in quotation_templates.values():
    target = PROJECT_ROOT / config.file
    target.parent.mkdir(parents=True, exist_ok=True)
    copy2(source_root / config.file, target)
    book = load_workbook(target)
    book.properties = DocumentProperties(creator='Synthetic test', lastModifiedBy='Synthetic test')
    book.custom_doc_props = CustomPropertyList()
    for sheet in book.worksheets:
        sheet._images = []
    sheet = book[config.sheet]
    for row, value in enumerate(('Synthetic Seller', 'Synthetic Contact', 'Synthetic Address', 'synthetic@example.invalid', '+00 000000'), start=3):
        sheet[f'I{row}'] = value
    first = config.lower_block.rows['bank_header'] + 1
    for row in range(first, first + 9):
        sheet[f'C{row}'] = f'SYNTHETIC-{row}'
    sheet[f'A{first + 9}'] = 'Synthetic notice'
    book.save(target)
    book.close()
suffix = uuid4().hex[:8].upper()
customer = Customer.objects.create(code=f'RQ{suffix}', name=f'Synthetic Original {suffix}', country='Germany')
target = Customer.objects.create(code=f'RT{suffix}', name=f'Synthetic Replacement {suffix}', country='France')
product = Product.objects.create(code=f'RP{suffix}', name='Synthetic Product')
sku = SKU.objects.create(product=product, sku=f'RS{suffix}')
quote = Quote.objects.create(quote_no=f'RQ{suffix}', customer=customer, quote_date=date(2026, 11, 5), buyer_tax_id='')
create_quote_items(quote, [{'sku': sku, 'quantity': 1, 'unit_price': 10}])
Quote.objects.filter(pk=quote.pk).update(status='sent')
users = get_user_model()
first = users.objects.create_user(username=f'rq-a-{suffix}', password='synthetic-only-password', is_staff=True)
second = users.objects.create_user(username=f'rq-b-{suffix}', password='synthetic-only-password', is_staff=True)
print(json.dumps({'quote': quote.pk, 'target': target.pk, 'sku': sku.pk, 'first_username': first.username, 'second_username': second.username}))
