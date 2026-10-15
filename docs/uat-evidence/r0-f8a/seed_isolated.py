"""Only seed a dedicated empty R0-F8A SQLite database."""
from datetime import timedelta
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from crm.models import Product, ProductCertificate, HSCode
from pathlib import Path
assert settings.DATABASES['default']['ENGINE']=='django.db.backends.sqlite3'
assert Path(settings.DATABASES['default']['NAME']).name=='r0f8a-ux.sqlite3'
assert not Product.objects.exists() and not ProductCertificate.objects.exists() and not HSCode.objects.exists()
with transaction.atomic():
    codes=[HSCode.objects.create(code='8539510000',description='R0F8A LED光源与灯具长商品描述'+(' · 归类用途说明'*12),notes='R0F8A 合成备注 '*25),HSCode.objects.create(code='9405429000',description='R0F8A 其他灯具',active=False)]
    products=[]
    for n in range(1,37):
        products.append(Product.objects.create(code=f'R0F8A-P{n:02}',name=f'R0F8A 产品{n:02} · 商用线性照明长名称与复杂产品归类测试',name_en=f'R0F8A synthetic product {n}',sales_model_prefix=f'FA{n:02}',hs_code=codes[0] if n<=3 else codes[1] if n==4 else None))
    for n,days in enumerate([180,20,-10,None,0,60]):
        ProductCertificate.objects.create(product=products[0] if n<4 else products[1],name=f'R0F8A {n+1} CE RoHS 线性灯具安全与环保测试长证书名称',certificate_no=f'R0F8A-TEST-CERT-{n+1}-'+'ABC123'*9,issuer='R0F8A 合成检测机构·照明安全实验室',issued_date=timezone.localdate()-timedelta(days=200),expires_on=timezone.localdate()+timedelta(days=days) if days is not None else None,file_url='' if n==3 else 'http://127.0.0.1:8115/media/r0f8a-missing.pdf',notes='R0F8A 合成证书备注，仅用于隔离UI，不代表真实证书。'*8)
print('Seeded isolated R0-F8A: 36 products, 2 HS codes, 6 certificates')
