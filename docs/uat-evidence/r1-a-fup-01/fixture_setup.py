"""FIXTURE_SETUP only. Run with the FUP-01 isolated DATABASE_URL after migrations."""
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'backend'))
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
django.setup()
from django.conf import settings
from crm.models import Customer, Order, Product, SKU, Transaction
from datetime import date
assert Path(settings.DATABASES['default']['NAME']).name == 'r1a-fup01-isolated.sqlite3'
assert not Customer.objects.exists() and not Transaction.objects.exists(), 'Only initialize an empty disposable DB'
c=Customer.objects.create(code='FUP01-C',name='FUP01 合成客户')
s=SKU.objects.create(sku='FUP01-S',product=Product.objects.create(code='FUP01-P',name='合成灯具'))
o=Order.objects.create(order_no='FUP01-ORDER',customer=c,order_date=date(2026,10,18),expected_ship_date=date(2026,10,18),currency='USD',exchange_rate='7.123456',status='confirmed')
o.items.create(sku=s,quantity='1',unit_price='500')

