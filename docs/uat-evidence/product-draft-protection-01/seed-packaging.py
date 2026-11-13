import json
import django
django.setup()
from django.conf import settings
from test_support.isolated_runtime import verify_isolated_runtime
verify_isolated_runtime(settings=settings,database_must_exist=True)
from crm.models import Product, PackagingTemplate
p=Product.objects.create(code='C-PKG-P',name='合成包装选择验收产品')
name='合成长文本防震五层瓦楞纸箱（轨道灯专用）' * 5
PackagingTemplate.objects.create(code='C-PKG-LONG',name=name,carton_length=30,carton_width=20,carton_height=10)
print(json.dumps({'product':p.pk,'name':name}))
