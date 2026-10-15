"""Run only against a fresh r0f6-ux.sqlite3; all records are disposable."""
from django.conf import settings
from crm.models import ProductCategory, CategoryAttribute, Product, ProductParameter, Supplier, SKU, SupplierSKU

if not str(settings.DATABASES['default']['NAME']).endswith('r0f6-ux.sqlite3'):
    raise SystemExit('Refusing non-R0-F6 database')
if Product.objects.exists() or ProductCategory.objects.exists() or Supplier.objects.exists():
    raise SystemExit('Refusing nonempty database')
root = ProductCategory.objects.create(name='R0F6 照明产品')
child = ProductCategory.objects.create(name='R0F6 商业照明', parent=root)
leaf = ProductCategory.objects.create(name='R0F6 超长分类名称·室内商用线性照明与装饰灯具', parent=child)
extra = ProductCategory.objects.create(name='R0F6 配件与控制系统', sort_order=1)
CategoryAttribute.objects.create(category=root, name='功率', key='power', include_in_sku=True, required=True)
CategoryAttribute.objects.create(category=leaf, name='安装方式', key='mounting')
first = Supplier.objects.create(name='R0F6 多供应来源测试供应商·长名称有限公司', code='FA')
second = Supplier.objects.create(name='R0F6 第二供应商', code='FB')
product = Product.objects.create(code='R0F6-001', name='R0F6 长名称产品·商业照明线性灯具与多规格主档', name_en='R0F6 Commercial linear lighting long English name', sales_model_prefix='F6A', category=leaf, description='隔离测试：'+ '长描述用于检查换行与滚动。'*30)
product.additional_categories.add(extra)
product.suppliers.add(first, second)
Product.objects.create(code='R0F6-002', name='R0F6 开发中产品', sales_model_prefix='F6B', category=extra, status='development')
for index, power in enumerate(['10W', '20W'], 1):
    sku = SKU.objects.create(product=product, sku=f'R0F6-SKU-{index}', display_name_cn=f'R0F6 线性灯 {power}', sales_model=f'F6A{index}', parameter_values={'power':power}, specification=f'{power} / 3000K')
    for supplier in [first, second]:
        SupplierSKU.objects.create(sku=sku, supplier=supplier, supplier_sku_code=f'F6-{index}')
for index, (name, value, unit) in enumerate([('功率','10 / 20','W'),('色温','3000 / 4000','K'),('长参数名称·灯体材料与安装规格','铝合金灯体 / 吊装与嵌入安装','')]):
    ProductParameter.objects.create(product=product, group='基础规格', name=name, value=value, unit=unit, sort_order=index)
print('R0-F6 isolated fixtures ready')
