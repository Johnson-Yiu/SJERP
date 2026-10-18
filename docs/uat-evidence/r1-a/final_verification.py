"""Read-only final DB and real HTTP observations. No updates or balance repair."""
import json
from pathlib import Path
from decimal import Decimal as D
from urllib.request import urlopen
from django.conf import settings
from crm.models import Order, PurchaseOrder, Transaction, GoodsReceipt, InventoryMovement, SKU, Shipment
from crm.services.fulfillment import sku_metrics, order_item_metrics
assert Path(settings.DATABASES['default']['NAME']).name == 'r1a-isolated.sqlite3'
out=settings.BASE_DIR.parent/'docs/uat-evidence/r1-a'
o=Order.objects.get(order_no='R1A-USD500')
p=PurchaseOrder.objects.get(purchase_no='PO-2026-00001')
assert o.status=='completed' and o.paid_amount==D('340') and o.outstanding_amount==D('160')
assert p.order_id is None and p.total_amount==D('265') and p.paid_amount==D('265')
assert sum((plan.remaining_amount for plan in p.payment_plans.all()),D('0'))==0
for tx in Transaction.objects.all(): assert tx.rmb_amount==(tx.amount*tx.exchange_rate).quantize(D('0.0001'))
assert Transaction.objects.get(notes='R1A post-fix Chrome').amount==D('2.34')
assert len(Transaction.objects.get(notes='R1A post-fix Chrome').transaction_no)==36
for receipt in GoodsReceipt.objects.filter(reversal_inventory_movement__isnull=False):
    assert receipt.inventory_movement.quantity==receipt.reversal_inventory_movement.quantity
    assert receipt.inventory_movement.unit_cost==receipt.reversal_inventory_movement.unit_cost
assert sku_metrics(SKU.objects.get(sku='R1A-EXISTING'))=={'actual_quantity':D('20'),'reserved_quantity':D('20'),'available_quantity':D('0'),'in_transit_quantity':D('0')}
assert sku_metrics(SKU.objects.get(sku='R1A-PCS'))['actual_quantity']==0
assert sku_metrics(SKU.objects.get(sku='R1A-SECOND'))['actual_quantity']==D('5')
data={'type':'DATABASE_VERIFICATION','database':str(settings.DATABASES['default']['NAME']),
      'orders':list(Order.objects.values()),'order_metrics':{str(i.pk):order_item_metrics(i) for order in Order.objects.all() for i in order.items.all()},
      'purchases':list(PurchaseOrder.objects.values()),'purchase_items':list(p.items.values()),'plans':list(o.payment_plans.values())+list(p.payment_plans.values()),
      'transactions':list(Transaction.objects.values()),'receipts':list(GoodsReceipt.objects.values()),
      'movements':list(InventoryMovement.objects.values()),'shipments':list(Shipment.objects.values()),
      'inventory':{s.sku:sku_metrics(s) for s in SKU.objects.all()}}
(out/'database-final.json').write_text(json.dumps(data,default=str,ensure_ascii=False,indent=2),encoding='utf-8')
paths=['orders/1/','orders/1/workbench/','customers/1/insights/','context/customers/1/','payment-plans/?direction=receivable&status=open&overdue=1','finance-dashboard/','reports/data/?source=sales&date_from=2026-10-01&date_to=2026-10-31','reports/data/?source=cash&date_from=2026-10-01&date_to=2026-10-31','skus/1/inventory-detail/']
results=[]
from urllib.error import HTTPError
for path in paths:
    try:
        with urlopen('http://127.0.0.1:8126/api/'+path) as response:
            results.append({'type':'REAL_API_OBSERVATION','method':'GET','path':'/api/'+path,'status':response.status,'body':json.load(response,parse_float=D)})
    except HTTPError as error:
        results.append({'type':'REAL_API_OBSERVATION','path':'/api/'+path,'status':error.code,'body':error.read().decode()})
(out/'http-final.json').write_text(json.dumps(results,default=str,ensure_ascii=False,indent=2),encoding='utf-8')
print('DATABASE_VERIFICATION Decimal passed; HTTP statuses:',[(r['path'],r['status']) for r in results])

