"""Disposable UI fixture; refuses any database outside the isolation runner."""
import json
import os
from datetime import date
from pathlib import Path
import django
django.setup()
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from test_support.isolated_runtime import verify_isolated_runtime
from crm.models import Customer, Contact, FollowUp, ProductCategory, Product, SKU, Supplier, Order, PurchaseOrder
from crm.services.purchase_lifecycle import place_purchase_order

verify_isolated_runtime(settings=settings, database_must_exist=True)
suffix = os.environ['ISOLATED_TEST_RUN_ID'][:8].upper()
with transaction.atomic():
    customer = Customer.objects.create(code=f'UX{suffix}', name=f'合成办公客户 {suffix}', country='DE', status='customer')
    contact = Contact.objects.create(customer=customer, name='合成联系人', email='office@example.invalid', is_primary=True)
    FollowUp.objects.create(customer=customer, contact=contact, followed_at=timezone.now(), subject='合成办公跟进', content='仅用于隔离工作区验收', next_follow_up_mode='keep')
    category = ProductCategory.objects.create(name=f'合成照明分类 {suffix}')
    product = Product.objects.create(code=f'UXP{suffix}', name='合成长名称灯带及安装规格展示' * 4, category=category)
    sku = SKU.objects.create(product=product, sku=f'UXSKU{suffix}', sales_model='LONG-SYNTHETIC-MODEL-' * 5, display_name_cn='合成柔性灯带完整规格及包装名称' * 4, unit='pcs')
    supplier = Supplier.objects.create(code='UX', name=f'合成办公供应商 {suffix}')
    order = Order.objects.create(order_no=f'UXSO{suffix}', customer=customer, order_date=date.today(), currency='CNY', exchange_rate='1', status='confirmed')
    order.items.create(sku=sku, quantity='10', unit_price='12.50')
    purchase = PurchaseOrder.objects.create(purchase_no=f'UXPO{suffix}', supplier=supplier, order=order, order_date=date.today(), currency='CNY', exchange_rate='1', payment_terms_snapshot=[{'label':'协商尾款','ratio':'1','due_basis':'no_date','offset_days':0}])
    item = purchase.items.create(sku=sku, quantity='10', unit_price='2')
    place_purchase_order(purchase)
result = {'customer':customer.pk,'contact':contact.pk,'product':product.pk,'sku':sku.pk,'order':order.pk,'purchase':purchase.pk,'purchase_item':item.pk,'suffix':suffix,'database':str(settings.DATABASES['default']['NAME']),'media':str(settings.MEDIA_ROOT),'identity':'existing development identity; not an authenticated audit operator'}
print(json.dumps(result,ensure_ascii=False))
