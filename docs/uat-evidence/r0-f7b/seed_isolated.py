"""Disposable R0-F7B fixtures; refuses any other database or existing records."""
from django.conf import settings
from django.db import transaction
from crm.models import ProductCategory,CategoryAttribute,Product,ProductParameter,SKU,Supplier,SupplierSKU
if not str(settings.DATABASES['default']['NAME']).endswith('r0f7b-ux.sqlite3'):
    raise SystemExit('Refusing non-R0-F7B database')
if Product.objects.exists() or Supplier.objects.exists() or SKU.objects.exists():
    raise SystemExit('Refusing nonempty database')
with transaction.atomic():
    category=ProductCategory.objects.create(name='R0F7B 线性照明')
    power=CategoryAttribute.objects.create(category=category,name='功率',key='power',unit='W',include_in_sku=True,include_in_sales_model=True,required=True)
    voltage=CategoryAttribute.objects.create(category=category,name='电压',key='voltage',unit='V',include_in_sku=True,include_in_sales_model=True,required=True,sort_order=1)
    product=Product.objects.create(code='R0F7B-P01',name='R0F7B 商用线性灯具长名称多规格测试',name_en='R0F7B commercial linear light',category=category,sales_model_prefix='F7B')
    other=Product.objects.create(code='R0F7B-P02',name='R0F7B 独立产品',category=category,sales_model_prefix='F7C')
    suppliers=[Supplier.objects.create(name='R0F7B 长名称供应商·多来源采购测试有限公司',code='GA'),Supplier.objects.create(name='R0F7B 第二供应商',code='GB')]
    for supplier in suppliers:
        supplier.supply_categories.add(category)
    product.suppliers.add(*suppliers)
    existing=SKU.objects.create(product=product,sku='R0F7B-EXISTING',display_name_cn=product.name+'-10W-24V',sales_model='F7B-1024',specification='10W / 24V',parameter_values={f'{category.id}:power':'10',f'{category.id}:voltage':'24'},unit='pcs')
    SKU.objects.create(product=other,sku='R0F7B-INACTIVE',display_name_cn='R0F7B 已停用样本',sales_model='F7B-ARCHIVE',active=False,parameter_values={f'{category.id}:power':'5',f'{category.id}:voltage':'12'})
    for supplier in suppliers:
        SupplierSKU.objects.create(sku=existing,supplier=supplier,supplier_sku_code=f'{supplier.code}-01',supplier_model='长供应商型号-10W-24V',purchase_price='12.50',currency='USD',moq=10)
    for name,value,unit in [('功率','10','W'),('功率','20','W'),('电压','24','V'),('电压','48','V')]:
        ProductParameter.objects.create(product=product,group=value,name=name,value=value,unit=unit)
print('R0-F7B isolated fixtures ready')

from django.utils import timezone
from crm.models import PackagingTemplate,SKUPackagingProfile,SKUTradeUnit
SKU.objects.update(unit='m')
second=SKU.objects.create(product=product,sku='R0F7B-SECOND',display_name_cn='R0F7B 第二规格长名称-10W-48V',sales_model='F7B-1048',unit='m',parameter_values={f'{category.id}:power':'10',f'{category.id}:voltage':'48'},sales_model_abbreviations={})
pcs=SKU.objects.create(product=other,sku='R0F7B-PCS',display_name_cn='R0F7B PCS 单位灯具',sales_model='F7B-PCS',unit='pcs')
for index,policy in enumerate(['SAME_CARTON','REPACK','MANUAL']):
 template=PackagingTemplate.objects.create(name=('R0F7B 多SKU共用长名称包装模板·防护运输测试' if index==0 else 'R0F7B '+policy),supplier=suppliers[index%2],carton_length=50,carton_width=40,carton_height=30,carton_tare_weight='1.5',partial_carton_policy=policy,active=index!=2,description='长备注：适用合成SKU的运输包装，不改变基础单位。'*6)
 if index==0:
  for row,qty,weight in [(existing,20,'0.2'),(second,10,'0.3')]:
   SKUPackagingProfile.objects.create(sku=row,packaging_template=template,qty_per_carton_override=qty,unit_net_weight=weight,verified_at=timezone.now())
for factor in [5,10,50]:SKUTradeUnit.objects.create(sku=existing,name=f'{factor} 米/卷',unit='卷',factor=factor,is_default=factor==10)
for supplier in suppliers:SKUTradeUnit.objects.create(sku=existing,supplier=supplier,name='供应商专用10米卷',unit='卷',factor=10,allow_fraction=True)
SKUTradeUnit.objects.create(sku=pcs,name='100件/箱',unit='箱',factor=100)
print('R0-F7B isolated fixtures created')
