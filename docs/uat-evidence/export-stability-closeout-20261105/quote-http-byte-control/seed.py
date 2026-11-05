from datetime import date
from decimal import Decimal
from pathlib import Path
import json
from django.conf import settings
from crm.models import Customer, Product, SKU, Quote
from crm.quote_snapshots import create_quote_items

expected = (Path(__file__).resolve().parent / 'synthetic.sqlite3').resolve()
assert Path(settings.DATABASES['default']['NAME']).resolve() == expected
customer = Customer.objects.create(code='QHTTP-CUSTOMER', name='Synthetic Quote Buyer', country='Germany', address='Synthetic Address')
product = Product.objects.create(code='QHTTP-PRODUCT', name='Synthetic Light')
sku = SKU.objects.create(product=product, sku='QHTTP-SKU', sales_model='QHTTP-MODEL', unit='pcs', default_price='12.50')
quote = Quote.objects.create(quote_no='QHTTP-20261105-001', customer=customer, buyer_company_name='Synthetic Quote Buyer', buyer_address='Synthetic Address', currency='USD', quote_date=date(2026, 11, 5), shipping_fee=Decimal('0'), discount=Decimal('0'))
create_quote_items(quote, [{'sku': sku, 'quantity': Decimal('2'), 'unit_price': Decimal('12.50'), 'description': 'Synthetic light'}])
fixture = {'synthetic_only': True, 'database': str(expected), 'quote_id': quote.pk, 'quote_no': quote.quote_no, 'model': 'QHTTP-MODEL', 'quantity': 2, 'unit_price': 12.5, 'amount': 25}
(Path(__file__).resolve().parent / 'fixture.json').write_text(json.dumps(fixture, indent=2), encoding='utf-8')
print(json.dumps(fixture, indent=2))
