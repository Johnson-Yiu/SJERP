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
print('isolated short and long inherited category fixtures created')
