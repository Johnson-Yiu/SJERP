"""Disposable R0-F7A fixtures; refuses any other database or existing records."""
from django.conf import settings
from django.db import transaction
from crm.models import ProductCategory,CategoryAttribute,Product,ProductParameter,SKU,Supplier,SupplierSKU
if not str(settings.DATABASES['default']['NAME']).endswith('r0f7a-ux.sqlite3'):
    raise SystemExit('Refusing non-R0-F7A database')
if Product.objects.exists() or Supplier.objects.exists() or SKU.objects.exists():
    raise SystemExit('Refusing nonempty database')
with transaction.atomic():
    category=ProductCategory.objects.create(name='R0F7A 线性照明')
    power=CategoryAttribute.objects.create(category=category,name='功率',key='power',unit='W',include_in_sku=True,include_in_sales_model=True,required=True)
    voltage=CategoryAttribute.objects.create(category=category,name='电压',key='voltage',unit='V',include_in_sku=True,include_in_sales_model=True,required=True,sort_order=1)
    product=Product.objects.create(code='R0F7A-P01',name='R0F7A 商用线性灯具长名称多规格测试',name_en='R0F7A commercial linear light',category=category,sales_model_prefix='F7A')
    other=Product.objects.create(code='R0F7A-P02',name='R0F7A 独立产品',category=category,sales_model_prefix='F7B')
    suppliers=[Supplier.objects.create(name='R0F7A 长名称供应商·多来源采购测试有限公司',code='GA'),Supplier.objects.create(name='R0F7A 第二供应商',code='GB')]
    for supplier in suppliers:
        supplier.supply_categories.add(category)
    product.suppliers.add(*suppliers)
    existing=SKU.objects.create(product=product,sku='R0F7A-EXISTING',display_name_cn=product.name+'-10W-24V',sales_model='F7A-1024',specification='10W / 24V',parameter_values={f'{category.id}:power':'10',f'{category.id}:voltage':'24'},unit='pcs')
    SKU.objects.create(product=other,sku='R0F7A-INACTIVE',display_name_cn='R0F7A 已停用样本',sales_model='F7B-ARCHIVE',active=False,parameter_values={f'{category.id}:power':'5',f'{category.id}:voltage':'12'})
    for supplier in suppliers:
        SupplierSKU.objects.create(sku=existing,supplier=supplier,supplier_sku_code=f'{supplier.code}-01',supplier_model='长供应商型号-10W-24V',purchase_price='12.50',currency='USD',moq=10)
    for name,value,unit in [('功率','10','W'),('功率','20','W'),('电压','24','V'),('电压','48','V')]:
        ProductParameter.objects.create(product=product,group=value,name=name,value=value,unit=unit)
print('R0-F7A isolated fixtures ready')
