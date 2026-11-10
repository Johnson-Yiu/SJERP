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

from crm.models import PackagingTemplate,SKUPackagingProfile
template=PackagingTemplate.objects.create(name='隔离测试包装',carton_length=50,carton_width=40,carton_height=30,carton_tare_weight='1.5',partial_carton_policy='SAME_CARTON',active=True)
SKUPackagingProfile.objects.create(sku=sku,packaging_template=template,qty_per_carton_override=10,unit_net_weight='0.2')
