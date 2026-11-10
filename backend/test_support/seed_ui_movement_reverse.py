import os,json,pathlib
import django
django.setup()
from django.conf import settings
from test_support.isolated_runtime import verify_isolated_runtime
verify_isolated_runtime(settings=settings,database_must_exist=True)
from crm.models import Customer,Supplier,Product,ProductCategory,SKU,Order,OrderItem,PurchaseOrder,PurchaseOrderItem
from datetime import date
c1=Customer.objects.create(code='WS-C001',name='Workspace Alpha',country='US')
c2=Customer.objects.create(code='WS-C002',name='Workspace Beta',country='GB')
s=Supplier.objects.create(code='WS-S001',name='Workspace Supplier')
category=ProductCategory.objects.create(name='Workspace Category')
p=Product.objects.create(code='WS-P001',name='Workspace Light',category=category)
sku=SKU.objects.create(product=p,sku='WS-SKU001',unit='pcs',default_price='10',cost_price='4')
o=Order.objects.create(order_no='WS-SO001',customer=c1,order_date=date.today(),status='draft',currency='USD',exchange_rate='7.2')
OrderItem.objects.create(order=o,sku=sku,quantity='10',unit_price='10',cost_price='4')
po=PurchaseOrder.objects.create(purchase_no='WS-PO001',supplier=s,order_date=date.today(),status='draft',currency='USD',exchange_rate='7.2')
PurchaseOrderItem.objects.create(purchase_order=po,sku=sku,quantity='10',unit_price='4')
path=pathlib.Path(os.environ['WORKSPACE_EVIDENCE_DIR']);path.mkdir(parents=True,exist_ok=True)
(path/'fixture.json').write_text(json.dumps({'customers':[c1.pk,c2.pk],'order':o.pk,'purchase':po.pk,'supplier':s.pk,'sku':sku.pk}),encoding='utf-8')

from crm.models import InventoryMovement
InventoryMovement.objects.create(movement_no='WS-MOV001',movement_date=date.today(),type='adjust_in',sku=sku,quantity=10,unit_cost=2,warehouse='隔离仓',source_type='manual')
