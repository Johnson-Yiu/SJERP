"""FIXTURE_SETUP: empty disposable DB only. Stock/history preparation is not UI acceptance."""
import os,sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
import django
django.setup()
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal as D
from crm.models import Customer,Supplier,Product,SKU,Order,PurchaseOrder,Transaction
from crm.services.order_lifecycle import confirm_order,complete_order,cancel_order
from crm.services.purchase_lifecycle import place_purchase_order
from crm.services.fulfillment import record_receipt,confirm_shipment
from crm.services.finance import record_transaction
assert Path(settings.DATABASES['default']['NAME']).name=='r1a-fup02-fix01-isolated.sqlite3'
assert not Customer.objects.exists() and not Transaction.objects.exists()
day=timezone.localdate()-timedelta(days=3)
c=Customer.objects.create(code='FUP02-C',name='FUP02 合成客户',country='Germany')
supplier=Supplier.objects.create(code='F2',name='FUP02 合成供应商')
sku=SKU.objects.create(sku='FUP02-S',product=Product.objects.create(code='FUP02-P',name='合成灯具'),unit='pcs')
p=PurchaseOrder.objects.create(purchase_no='FUP02-STOCK',supplier=supplier,order_date=day,currency='USD',exchange_rate=D('7.1'))
line=p.items.create(sku=sku,quantity=D('100'),unit_price=D('10'));place_purchase_order(p)
record_receipt(line,{'quantity':D('100'),'unit_cost':D('10'),'receipt_date':day})
def order(no,qty,price,confirm=True):
 o=Order.objects.create(order_no=no,customer=c,order_date=day,expected_ship_date=day,currency='USD',exchange_rate=D('7.1'))
 o.items.create(sku=sku,quantity=D(qty),unit_price=D(price))
 return confirm_order(o) if confirm else o
main=order('FUP02-500','10','50')
paid=order('FUP02-PAID-UNSHIPPED','2','250')
record_transaction({'order':paid,'kind':'customer_receipt','amount':D('500'),'currency':'USD','exchange_rate':D('7.1'),'notes':'FIXTURE_SETUP paid but unshipped'})
draft=order('FUP02-DRAFT','1','100',False)
cancelled=order('FUP02-CANCELLED','1','100',False);cancel_order(cancelled,'synthetic cancelled fixture')
history=order('FUP02-HISTORY','3','100')
confirm_shipment(history,{'shipment_date':day,'items':[{'order_item':history.items.get().pk,'quantity':D('3')}]})
history.refresh_from_db();complete_order(history)
record_transaction({'order':history,'kind':'customer_receipt','amount':D('100'),'currency':'USD','exchange_rate':D('7.1'),'notes':'FIXTURE_SETUP historical completed debt'})
zero=order('FUP02-ZERO','1','0')
legacy=Order.objects.create(order_no='FIX01-HISTORY-NO-PLANS',customer=c,order_date=day,currency='USD',exchange_rate=D('7.1'),status='completed')
legacy.items.create(sku=sku,quantity=D('2'),unit_price=D('250'))
result={'legacy_no_plans':legacy.pk,'main':main.pk,'paid_unshipped':paid.pk,'draft':draft.pk,'cancelled':cancelled.pk,'history':history.pk,'zero':zero.pk,'main_item':main.items.get().pk,'database':str(settings.DATABASES['default']['NAME']),'classification':'FIXTURE_SETUP'}
Path(__file__).with_name('fixture-ids.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(result,ensure_ascii=False))
