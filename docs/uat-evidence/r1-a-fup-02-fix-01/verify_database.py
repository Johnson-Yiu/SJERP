"""DATABASE_VERIFICATION: preserved snapshots, Decimal, no database writes."""
import json
from pathlib import Path
from decimal import Decimal as D
p=Path(__file__).resolve().parent
read=lambda n:json.loads((p/(n+'.json')).read_text(encoding='utf8'))
a,b,s,r,f=map(read,['before_complete','after_complete','settled','refunded','fixture_before_ui'])
for model in ['PaymentPlan','Transaction','Shipment','InventoryMovement','InventoryReservation']:assert a[model]==b[model],model
balance=lambda data:sum((D(x['planned_amount'])-D(x['settled_amount']) for x in data['PaymentPlan'] if x['order_id']==1 and x['status']=='open'),D('0'))
assert [balance(data) for data in [a,b,s,r]]==[D('160'),D('160'),D('0'),D('40')]
for data in [b,s,r]:assert next(x for x in data['Order'] if x['id']==1)['status']=='completed'
for model in ['Order','PaymentPlan','Transaction']:
 selector=lambda x:x['id']==7 if model=='Order' else x['order_id']==7
 assert [x for x in f[model] if selector(x)]==[x for x in r[model] if selector(x)]
assert not any(x['order_id']==7 for x in r['PaymentPlan'])
rows=[x for x in r['Transaction'] if x['order_id']==1]
assert sum((D(x['amount'])*(1 if x['direction']=='income' else -1) for x in rows),D('0'))==D('460')
assert sum((D(x['rmb_amount'])*(1 if x['direction']=='income' else -1) for x in rows),D('0'))==D('3266')
print('PASS: completion changes no financial/inventory rows; 160->0->40; completed unchanged; legacy no-plan record and plans/cash unchanged; USD460 net/CNY3266 reference only')
