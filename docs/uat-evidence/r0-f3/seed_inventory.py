from datetime import date
from decimal import Decimal
from crm.models import Product, SKU, Customer, Supplier, Order, PurchaseOrder, InventoryMovement
from crm.services.fulfillment import record_receipt, confirm_shipment, reverse_manual_inventory_movement, allocate_order, sku_metrics
from django.conf import settings
assert str(settings.DATABASES['default']['NAME']).endswith('r0f3-ux.sqlite3')
assert not SKU.objects.exists()
day=date(2026,10,14)
product=Product.objects.create(code='F3',name='库存独立验收灯带长名称及不同交易规格展示')
skus=[SKU.objects.create(product=product,sku=f'F3-SKU-{i:03}',unit='m' if i%2 else 'pcs',specification=f'独立验收规格 {i}') for i in range(1,53)]
customer=Customer.objects.create(code='F3-C',name='库存独立验收客户')
supplier=Supplier.objects.create(code='F3',name='库存独立验收供应商')
for sku in skus[1:]:
 InventoryMovement.objects.create(movement_no=f'F3-MANUAL-{sku.id}',movement_date=day,type='adjust_in',sku=sku,quantity=100,unit_cost=2,warehouse='验收仓',source_type='manual')
for sku,quantity in [(skus[1],30),(skus[2],100)]:
 order=Order.objects.create(order_no=f'F3-RESERVE-{sku.id}',customer=customer,order_date=day,status='confirmed')
 order.items.create(sku=sku,quantity=quantity,unit_price=5)
 allocate_order(order)
order=Order.objects.create(order_no='F3-RECEIPT-SHIP',customer=customer,order_date=day,status='confirmed')
item=order.items.create(sku=skus[3],quantity=10,unit_price=5)
purchase=PurchaseOrder.objects.create(purchase_no='F3-PURCHASE',supplier=supplier,order=order,order_date=day,status='ordered')
pitem=purchase.items.create(sku=skus[3],quantity=20,unit_price=2)
record_receipt(pitem,{'receipt_date':day,'quantity':Decimal('20'),'unit_cost':Decimal('2')})
confirm_shipment(order,{'shipment_date':day,'items':[{'order_item':item.id,'quantity':Decimal('5')}]})
movement=InventoryMovement.objects.create(movement_no='F3-REVERSE',movement_date=day,type='adjust_in',sku=skus[4],quantity=10,unit_cost=2,source_type='manual')
reverse_manual_inventory_movement(movement,'隔离验收冲销')
for sku in skus[:5]: print(sku.sku,sku_metrics(sku))
