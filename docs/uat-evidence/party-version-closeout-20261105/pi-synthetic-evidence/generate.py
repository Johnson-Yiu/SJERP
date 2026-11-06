"""Generate synthetic PI evidence from sanitized template copies in memory only."""
import hashlib
import json
import os
import sys
import tempfile
from copy import deepcopy
from datetime import date
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'backend'))
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['APP_STAGE'] = 'development'
os.environ['DEVELOPMENT_SUPERADMIN'] = '1'
os.environ['RBAC_ENFORCEMENT'] = '0'

import django
django.setup()
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client, RequestFactory
from openpyxl import load_workbook
from openpyxl.cell.cell import MergedCell
from openpyxl.packaging.core import DocumentProperties
from openpyxl.packaging.custom import CustomPropertyList
from openpyxl.worksheet.header_footer import HeaderFooter
from rest_framework.test import APIClient
from crm.models import Customer, Product, Quote, SKU
from crm.party_document_details import unknown_details
from crm.party_document_details_models import PartyDocumentDetailsStorage
from crm.party_version import apply_approved_quote_change, approve, baseline, propose
from crm.quote_snapshots import create_quote_items
from crm.quotation_template_config import quotation_templates
from crm import quote_template_snapshot

assert sys.version_info[:2] == (3, 12), sys.version
assert settings.DATABASES['default']['NAME'] == ':memory:'
settings.PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
settings.ALLOWED_HOSTS = ['testserver']
call_command('migrate', verbosity=0, interactive=False)

seller_values = ('SYNTHETIC SELLER', 'SYNTHETIC SALES CONTACT', 'SYNTHETIC SELLER ADDRESS',
                 'seller@example.invalid', '+00 000 111')
captured = []
with tempfile.TemporaryDirectory(prefix='sunjack-pi-synthetic-') as scratch:
    scratch = Path(scratch)
    settings.MEDIA_ROOT = scratch / 'media'
    quote_template_snapshot.PROJECT_ROOT = scratch
    sensitive_values = set()
    for template_id, config in quotation_templates.items():
        source = ROOT / config.file
        book = load_workbook(source)
        sheet = book[config.sheet]
        for row in range(3, 8):
            value = sheet[f'I{row}'].value
            if isinstance(value, str) and len(value.strip()) >= 8:
                sensitive_values.add(value.strip())
        bank_first = config.lower_block.rows['bank_header'] + 1
        for row in range(bank_first, bank_first + 9):
            value = sheet[f'C{row}'].value
            if isinstance(value, str) and len(value.strip()) >= 8:
                sensitive_values.add(value.strip())
        for other in list(book.worksheets):
            if other.title != config.sheet:
                book.remove(other)
                continue
            other._images.clear()
            other._charts.clear()
            other.HeaderFooter = HeaderFooter()
            for cells in other.iter_rows():
                for cell in cells:
                    if not isinstance(cell, MergedCell):
                        cell.value = None
                        cell.comment = None
                        cell.hyperlink = None
        book.defined_names.clear()
        book._external_links.clear()
        book.properties = DocumentProperties(creator='SYNTHETIC', lastModifiedBy='SYNTHETIC')
        book.custom_doc_props = CustomPropertyList()
        for row, value in enumerate(seller_values, 3):
            sheet[f'I{row}'] = value
        for row, label in enumerate(('Buyer name', 'Recipient', 'Address', 'Tax ID', 'Email', 'Phone'), 3):
            sheet[f'A{row}'] = label
        for offset in range(9):
            sheet[f'A{bank_first + offset}'] = f'SYNTHETIC BANK FIELD {offset + 1}'
            sheet[f'C{bank_first + offset}'] = f'SYNTHETIC BANK VALUE {offset + 1}'
        sheet[f'A{bank_first + 9}'] = 'SYNTHETIC BANK NOTICE'
        target = scratch / config.file
        target.parent.mkdir(parents=True, exist_ok=True)
        book.save(target)
        book.close()

    users = []
    for label in ('maker', 'reviewer', 'operator'):
        user = get_user_model().objects.create_user(username='synthetic-' + label, password='synthetic-test-only')
        client = Client()
        client.force_login(user)
        request = RequestFactory().post('/')
        request.user = user
        request.session = client.session
        users.append(request)
    api = APIClient()
    api.force_authenticate(users[0].user)

    for suffix, discount, template_id in (
        ('no-discount', '0.00', 'standard_en_no_discount'),
        ('with-discount', '5.00', 'standard_en_with_discount'),
    ):
        customer = Customer.objects.create(code='SYN-' + suffix, name='SYNTHETIC CUSTOMER ' + suffix, country='SYNTHETIC COUNTRY')
        product = Product.objects.create(code='SYN-P-' + suffix, name='SYNTHETIC PRODUCT')
        sku = SKU.objects.create(product=product, sku='SYN-SKU-' + suffix, sales_model='SYNTHETIC MODEL ' + suffix)
        quote = Quote.objects.create(quote_no='SYN-PI-' + suffix, customer=customer, quote_date=date(2026, 11, 6),
            status='draft', buyer_company_name='SYNTHETIC OLD SNAPSHOT', recipient_name='SYNTHETIC OLD RECIPIENT',
            buyer_address='SYNTHETIC OLD ADDRESS', buyer_tax_id='', currency='USD', discount=Decimal(discount))
        create_quote_items(quote, [{'sku': sku, 'quantity': Decimal('2'), 'unit_price': Decimal('20'), 'description': 'SYNTHETIC ITEM'}])
        details = unknown_details()
        details['seller'].update(dict(zip(('name', 'contact', 'address', 'email', 'phone'), seller_values)))
        details['buyer'].update(name='SYNTHETIC APPROVED BUYER', recipient='SYNTHETIC APPROVED RECIPIENT',
                                address='SYNTHETIC ADDRESS BEFORE', tax_id='', email='buyer@example.invalid', phone='+00 000 222')
        PartyDocumentDetailsStorage.objects.create(quote=quote, details=details)
        quote.status = 'sent'
        quote.save(update_fields=['status'])
        basis = baseline(request=users[0], target_type='quote', target_id=quote.pk)
        proposal = deepcopy(basis['snapshot'])
        proposal['party_details']['buyer']['address'] = 'SYNTHETIC APPROVED ADDRESS'
        request = propose(request=users[0], target_type='quote', target_id=quote.pk,
            expected_base_fingerprint=basis['fingerprint'], proposed_snapshot=proposal, change_type='correction',
            reason='SYNTHETIC CORRECTION', evidence='SYNTHETIC EVIDENCE', source_trust='unverified')
        approve(request=users[1], request_id=request.pk, expected_content_fingerprint=request.content_fingerprint, note='SYNTHETIC REVIEW')
        application = apply_approved_quote_change(request=users[2], request_id=request.pk)
        revision = Quote.objects.get(pk=application.result_quote_id)
        revision.status = 'sent'
        revision.save(update_fields=['status'])
        customer.name = 'SYNTHETIC MASTER CHANGED AFTER APPROVAL ' + suffix
        customer.address = 'SYNTHETIC MASTER ADDRESS CHANGED'
        customer.save()
        preview = api.get(f'/api/quotes/{revision.pk}/pi-data/')
        workbook_response = api.get(f'/api/quotes/{revision.pk}/export/')
        assert preview.status_code == 200, (suffix, preview.status_code, getattr(preview, 'data', None))
        assert workbook_response.status_code == 200, (suffix, workbook_response.status_code)
        data = preview.json()
        assert data['buyer'] == {'company_name': 'SYNTHETIC APPROVED BUYER', 'name': 'SYNTHETIC APPROVED RECIPIENT',
            'address': 'SYNTHETIC APPROVED ADDRESS', 'tax_id': '', 'email': 'buyer@example.invalid', 'phone': '+00 000 222'}
        assert 'SYNTHETIC MASTER CHANGED' not in json.dumps(data)
        blob = workbook_response.content
        book = load_workbook(BytesIO(blob))
        sheet = book['PI']
        expected = ['SYNTHETIC APPROVED BUYER', 'SYNTHETIC APPROVED RECIPIENT', 'SYNTHETIC APPROVED ADDRESS', None, 'buyer@example.invalid', '+00 000 222']
        actual = [sheet[f'B{row}'].value for row in range(3, 9)]
        assert actual == expected, (suffix, actual)
        snapshot = quote_template_snapshot.resolve_quote_template(revision, template_id)
        assert data['template_sha256'] == snapshot['sha256']
        assert sheet['I3'].value == seller_values[0]
        bank_row = snapshot['config']['lower_block']['rows']['bank_header'] + 1
        assert sheet[f'C{bank_row}'].value == 'SYNTHETIC BANK VALUE 1'
        book.close()
        with ZipFile(BytesIO(blob)) as zipped:
            xml_text = '\n'.join(zipped.read(name).decode('utf-8', 'ignore') for name in zipped.namelist() if name.endswith(('.xml', '.rels')))
        for value in sensitive_values:
            assert value not in xml_text and value not in json.dumps(data, ensure_ascii=False), 'Original seller/bank text detected'
        captured.append((suffix, blob, data, {'template_id': template_id, 'status': revision.status,
            'approved_correction': True, 'customer_master_changed_after_approval': True, 'buyer_cells_B3_B8': actual,
            'seller_I3': seller_values[0], 'bank_first_value': 'SYNTHETIC BANK VALUE 1',
            'template_sha256': snapshot['sha256'], 'xlsx_sha256': hashlib.sha256(blob).hexdigest(),
            'pi_status': preview.status_code, 'xlsx_status': workbook_response.status_code}))

output = Path(__file__).resolve().parent
for suffix, blob, data, checks in captured:
    (output / f'{suffix}.xlsx').write_bytes(blob)
    (output / f'{suffix}.pi.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (output / f'{suffix}.reconciliation.json').write_text(json.dumps(checks, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'python': sys.version, 'database': 'in-memory SQLite', 'samples': len(captured), 'status': 'PASS'}, ensure_ascii=False))
