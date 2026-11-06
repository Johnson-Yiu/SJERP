import json
import os
from datetime import date
from uuid import uuid4
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'test_support.isolated_settings')
django.setup()
from django.conf import settings
from django.contrib.auth import get_user_model
from test_support.isolated_runtime import verify_isolated_runtime
from crm.models import Customer, Order, PurchaseOrder, Quote, Supplier

verify_isolated_runtime(settings=settings, database_must_exist=True)
suffix = uuid4().hex[:8].upper()
customer = Customer.objects.create(code=f'UI{suffix}', name='Synthetic buyer', country='Germany')
supplier = Supplier.objects.create(code=f'U{suffix[:5]}', name='Synthetic seller')
quote = Quote.objects.create(quote_no=f'UIQ{suffix}', customer=customer, quote_date=date.today())
order = Order.objects.create(order_no=f'UIO{suffix}', customer=customer, order_date=date.today())
purchase = PurchaseOrder.objects.create(purchase_no=f'UIP{suffix}', supplier=supplier, order_date=date.today())
user = get_user_model().objects.create_user(username=f'ui-{suffix}', password='synthetic-only-password', is_staff=True)
print(json.dumps({'quote': quote.pk, 'order': order.pk, 'purchase': purchase.pk, 'username': user.username}))
