from pathlib import Path
import json, os
from django.conf import settings
from crm.models import Customer, Product, SKU
target = Path(os.environ['DIAG_RUN_DIR']).resolve()
assert Path(settings.DATABASES['default']['NAME']).resolve() == (target / 'synthetic.sqlite3').resolve()
customer = Customer.objects.create(code='R1-UX-QA-CUSTOMER', name='Synthetic quote buyer', country='Germany', address='Synthetic Test Address')
product = Product.objects.create(code='R1-UX-QA-PRODUCT', name='Synthetic Light')
sku = SKU.objects.create(sku='R1-UX-QA-SKU', product=product, sales_model='R1-QA-MODEL', unit='pcs', default_price='12.50')
fixture = {'customer': customer.pk, 'sku': sku.pk, 'synthetic_only': True}
(target / 'fixture.json').write_text(json.dumps(fixture, indent=2), encoding='utf-8')
print(json.dumps(fixture))
