import json
import django
django.setup()
from django.conf import settings
from test_support.isolated_runtime import verify_isolated_runtime
verify_isolated_runtime(settings=settings, database_must_exist=True)
from crm.models import Product, SKU, Supplier
product = Product.objects.create(code='C-P001', name='C 合成轨道灯产品')
skus = [SKU.objects.create(product=product, sku=f'C-SKU-{i}', unit='pcs') for i in [1,2]]
supplier = Supplier.objects.create(code='CC', name='C 合成照明供应商')
print(json.dumps({'product':product.pk,'skus':[s.pk for s in skus],'supplier':supplier.pk}))
