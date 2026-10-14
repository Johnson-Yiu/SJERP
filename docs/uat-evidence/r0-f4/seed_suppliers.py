from datetime import date
from decimal import Decimal
from django.conf import settings
from crm.models import Supplier, SupplierSKU, Product, ProductCategory, SKU, PurchaseOrder
from crm.payment_terms import default_payment_terms
assert str(settings.DATABASES['default']['NAME']).endswith('r0f4-ux.sqlite3')
assert not Supplier.objects.exists()
root=ProductCategory.objects.create(name='商业照明')
child=ProductCategory.objects.create(name='灯带',parent=root)
other=ProductCategory.objects.create(name='户外照明')
product=Product.objects.create(code='F4-P',name='F4 供应商独立验收照明产品',category=child)
sku=SKU.objects.create(product=product,sku='F4-SKU-SAME',unit='m',display_name_cn='F4 同一内部 SKU 的不同供应来源')
suppliers=[]
for i in range(32):
 code='Q'+chr(65+i) if i<26 else 'R'+chr(65+i-26)
 rules=default_payment_terms() if i%2==0 else []
 if rules: rules[0]['ratio']='0.5';rules[1]['ratio']='0.5'
 supplier=Supplier.objects.create(name=f'F4-{i:02} 独立验收供应商长名称及灯带规格资料',code=code,main_products='灯带、照明及户外产品',contact_name='验收联系人',phone='13800000000',email='qa@example.test',store_url='https://example.test/shop',payment_terms='普通文字备注 30%预付款、70%尾款，不代表实际执行比例。',payment_terms_config=rules,notes='完整备注用于多行和重开验收。'*20)
 supplier.supply_categories.add(child if i%2==0 else other)
 suppliers.append(supplier)
for i,supplier in enumerate(suppliers[:2]):
 product.suppliers.add(supplier)
 SupplierSKU.objects.create(supplier=supplier,sku=sku,supplier_model=f'F4-MODEL-{i}',supplier_sku_code=f'{supplier.code}-F4-01',purchase_price=Decimal('12.50'),currency='CNY',moq=Decimal('10'),lead_time_days=7,is_preferred=i==0)
po=PurchaseOrder.objects.create(purchase_no='F4-PO-EXISTING',supplier=suppliers[0],order_date=date(2026,10,14),status='draft',currency='CNY',exchange_rate=1,payment_terms_snapshot=suppliers[0].payment_terms_config)
po.items.create(sku=sku,quantity=10,unit_price=Decimal('12.50'))
print('F4 isolated suppliers:',Supplier.objects.count(),'sources:',SupplierSKU.objects.count(),'purchase:',po.id)
