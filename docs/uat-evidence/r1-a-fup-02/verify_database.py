"""Reproducible DATABASE_VERIFICATION over preserved UAT snapshots; no DB writes."""
import json
from pathlib import Path
from decimal import Decimal as D
p=Path(__file__).resolve().parent
read=lambda name:json.loads((p/(name+'.json')).read_text(encoding='utf8'))
a,b,s,r,j,f,final=map(read,['database_before_complete','database_after_complete','database_settled','database_refunded','database_after_rejections','database_fixture','database_final'])
for model in ['PaymentPlan','Transaction','Shipment','InventoryMovement','InventoryReservation']:assert a[model]==b[model],model
assert r==j==final
balance=lambda data:sum((D(x['planned_amount'])-D(x['settled_amount']) for x in data['PaymentPlan'] if x['order_id']==1 and x['status']=='open'),D('0'))
assert [balance(data) for data in [a,b,s,r]]==[D('160'),D('160'),D('0'),D('40')]
for data in [b,s,r]:assert next(x for x in data['Order'] if x['id']==1)['status']=='completed'
assert next(x for x in r['Order'] if x['id']==2)['status']=='confirmed'
for model in ['Order','PaymentPlan','Transaction']:
 selector=lambda x:x['id']==5 if model=='Order' else x['order_id']==5
 assert [x for x in f[model] if selector(x)]==[x for x in r[model] if selector(x)]
rows=[x for x in r['Transaction'] if x['order_id']==1]
assert sum((D(x['amount'])*(1 if x['direction']=='income' else -1) for x in rows),D('0'))==D('460')
assert sum((D(x['rmb_amount'])*(1 if x['direction']=='income' else -1) for x in rows),D('0'))==D('3266')
print('PASS: exact financial rows unchanged on complete; rejected writes unchanged; historical records unchanged; 160->0->40 balances; USD460 net / CNY3266 reference; final read-only flow unchanged')
