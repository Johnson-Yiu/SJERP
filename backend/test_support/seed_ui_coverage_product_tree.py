"""Synthetic descendants based on the existing R0-F6 category fixture; isolated only."""
import django
django.setup()
from django.conf import settings
from test_support.isolated_runtime import verify_isolated_runtime
from crm.models import ProductCategory, CategoryAttribute

verify_isolated_runtime(settings=settings, database_must_exist=True)
if ProductCategory.objects.exists():
    raise SystemExit('Refusing nonempty category fixture')
short = ProductCategory.objects.create(name='合成照明')
ProductCategory.objects.create(name='短来源子分类', parent=short)
CategoryAttribute.objects.create(category=short, name='短来源功率', key='short_power', include_in_sku=True)
long = ProductCategory.objects.create(name='室内商业线性照明与装饰灯具系统分类')
ProductCategory.objects.create(name='长来源子分类', parent=long)
CategoryAttribute.objects.create(category=long, name='长来源功率', key='long_power', include_in_sku=True)
level1 = ProductCategory.objects.create(name='合成商用建筑室内专业照明产品一级')
level2 = ProductCategory.objects.create(name='合成办公室及展厅线性装饰照明二级', parent=level1)
level3 = ProductCategory.objects.create(name='合成嵌入式吊装式组合灯具系列三级', parent=level2)
ProductCategory.objects.create(name='合成可调色温高显色灯具型号四级', parent=level3)
print('isolated short and long inherited category fixtures created')
