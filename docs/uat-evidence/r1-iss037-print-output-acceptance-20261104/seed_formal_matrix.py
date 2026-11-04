"""Create synthetic formal PI samples only inside the verified isolated runner."""
import base64
import contextlib
from datetime import date
import io
import json
import os
from pathlib import Path
import runpy
from shutil import copytree
from io import BytesIO
from openpyxl import load_workbook
from unittest.mock import patch

here = Path(__file__).resolve().parent
with contextlib.redirect_stdout(io.StringIO()):
    seeded = runpy.run_path(str(here.parent / 'r1-iss037-seller-template-freeze-20261103' / 'seed_browser.py'))

from django.core.files.base import ContentFile
from crm.models import Quote
from crm.quote_snapshots import create_quote_items
from rest_framework.test import APIClient

client = APIClient(HTTP_HOST='127.0.0.1')
sku = seeded['sku']
sku.image.save('synthetic.gif', ContentFile(base64.b64decode('R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw==')))
output = Path(os.environ['ISOLATED_TEST_ROOT']) / 'formal-print-evidence'
output.mkdir()
samples = []
for label, count in [('complete', 1), ('multipage', 30), ('optional-empty', 1)]:
    with patch('crm.quote_template_snapshot.PROJECT_ROOT', seeded['root']):
        quote = Quote.objects.create(
            quote_no=f"FORMAL-{label}-{seeded['suffix']}", customer=seeded['customer'],
            quote_date=date(2026, 11, 4), currency='USD',
            recipient_name='' if label == 'optional-empty' else 'Synthetic Recipient',
            buyer_address='Synthetic Buyer Address', buyer_email='buyer@example.invalid',
            buyer_phone='+00 111111')
    create_quote_items(quote, [dict(sku=sku, quantity=i + 1, unit_price='1.005',
        description=(f'Synthetic product row {i + 1}. ' + 'Long specification and installation details. ' * (12 if count > 1 else 1))) for i in range(count)])
    sent = client.post(f'/api/quotes/{quote.pk}/mark-sent/')
    if sent.status_code != 200:
        raise RuntimeError(f'Formal confirmation failed: {sent.status_code} {sent.content[:500]!r}')
    preview = client.get(f'/api/quotes/{quote.pk}/pi-data/')
    exported = client.get(f'/api/quotes/{quote.pk}/export/')
    if preview.status_code != 200 or exported.status_code != 200:
        raise RuntimeError('Saved PI/export failed')
    (output / f'{label}.json').write_text(json.dumps(preview.data, default=str, ensure_ascii=False, indent=2), encoding='utf-8')
    (output / f'{label}.xlsx').write_bytes(exported.content)
    (output / f'{label}.html').write_text(preview.data['print_html'], encoding='utf-8')
    quote.refresh_from_db()
    samples.append(dict(label=label, id=quote.pk, quote_no=quote.quote_no, status=quote.status, rows=count))
from crm.quote_template_snapshot import PRINT_TEMPLATE_PATH
for config in seeded['quotation_templates'].values():
    filename = seeded['root'] / config.file
    workbook = load_workbook(filename)
    workbook[config.sheet]['I3'] = 'Synthetic Changed Seller'
    workbook.save(filename)
changed_print = seeded['root'] / 'changed-print.html'
changed_print.write_text(PRINT_TEMPLATE_PATH.read_text(encoding='utf-8').replace('Proforma Invoice', 'Synthetic Changed Template'), encoding='utf-8')
with patch('crm.quote_template_snapshot.PROJECT_ROOT', seeded['root']), patch('crm.quote_template_snapshot.PRINT_TEMPLATE_PATH', changed_print):
    fresh = Quote.objects.create(quote_no=f"CHANGED-{seeded['suffix']}", customer=seeded['customer'], quote_date=date(2026, 11, 4))
    create_quote_items(fresh, [dict(sku=sku, quantity=1, unit_price=10)])
    changed = client.get(f'/api/quotes/{fresh.pk}/pi-data/')
    assert changed.status_code == 200
    assert changed.data['seller']['name'] == 'Synthetic Changed Seller'
    assert 'Synthetic Changed Template' in changed.data['print_html']
    for sample in samples:
        repeated = client.get(f"/api/quotes/{sample['id']}/pi-data/")
        exported = client.get(f"/api/quotes/{sample['id']}/export/")
        assert repeated.status_code == exported.status_code == 200
        original = json.loads((output / f"{sample['label']}.json").read_text(encoding='utf-8'))
        assert repeated.data['print_html'] == original['print_html']
        assert repeated.data['seller'] == original['seller']
        assert load_workbook(BytesIO(exported.content))['PI']['I3'].value == original['seller']['name']
        (output / f"{sample['label']}-after-current-template-change.xlsx").write_bytes(exported.content)
from django.conf import settings
copytree(settings.MEDIA_ROOT, output / 'media')
(output / 'samples.json').write_text(json.dumps(samples, indent=2), encoding='utf-8')
print(json.dumps(dict(samples=samples, output=str(output))))
