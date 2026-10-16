from pathlib import Path
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from crm.models import *
assert Path(settings.DATABASES['default']['NAME']).resolve() == (settings.BASE_DIR/'r0f9-ux.sqlite3').resolve()
assert not Product.objects.exists() and not Customer.objects.exists()
with transaction.atomic():
    source=settings.BASE_DIR.parent/'docs/uat-evidence'
    exec((source/'r0-f7b/seed_isolated.py').read_text(encoding='utf-8').replace('r0f7b-ux.sqlite3','r0f9-ux.sqlite3').replace('R0F7B','R0F9'))
    exec((source/'r0-f5/seed_isolated.py').read_text(encoding='utf-8').replace('R0F5','R0F9'))
    day=timezone.localdate()
    c=Customer.objects.order_by('id').first(); s=Supplier.objects.order_by('id').first(); sku=SKU.objects.order_by('id').first()
    q=Quote.objects.create(quote_no='R0F9-Q001',customer=c,quote_date=day,status='sent')
    q.items.create(sku=sku,quantity=20,unit_price=25)
    o=Order.objects.create(order_no='R0F9-O001',customer=c,quote=q,order_date=day,status='confirmed')
    o.items.create(sku=sku,quantity=20,unit_price=25)
    p=PurchaseOrder.objects.create(purchase_no='R0F9-P001',supplier=s,order=o,order_date=day,status='ordered')
    p.items.create(sku=sku,quantity=20,unit_price=12.5)
    PaymentPlan.objects.create(order=o,direction='receivable',due_date=day,planned_amount=500,currency='USD')
    PaymentPlan.objects.create(purchase_order=p,direction='payable',due_date=day,planned_amount=250,currency='USD')
    Transaction.objects.create(transaction_no='R0F9-T001',transaction_date=day,direction='income',category='其他收入',amount=20,currency='CNY',kind='other_income',notes='合成UI样本，不代表实际收款')
    InventoryMovement.objects.create(movement_no='R0F9-M001',movement_date=day,type='adjust_in',sku=sku,quantity=100,unit_cost=12.5,warehouse='合成验收仓',source_type='manual')
    h=HSCode.objects.create(code='9405429000',description='R0F9 商用照明灯具')
    product.hs_code=h; product.save()
    ProductCertificate.objects.create(product=product,name='R0F9 CE 合成证书',certificate_no='R0F9-CE-001',issuer='隔离测试机构',issued_date=day,notes='无真实文件，仅核查界面')
print('R0F9 isolated seed complete; no real accounts or production data')
