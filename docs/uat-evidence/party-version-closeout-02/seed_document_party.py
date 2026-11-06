"""Create only synthetic documents through existing formal lifecycle services."""
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
from crm.models import Customer, Contact, Order, Product, PurchaseOrder, SKU, Supplier
from crm.services.order_lifecycle import confirm_order
from crm.services.purchase_lifecycle import place_purchase_order

verify_isolated_runtime(settings=settings, database_must_exist=True)
suffix = uuid4().hex[:8].upper()
customer = Customer.objects.create(code=f'DP{suffix}', name=f'Synthetic Buyer {suffix}', country='Germany', address='Synthetic buyer address')
Contact.objects.create(customer=customer, name='Synthetic Contact', email='contact@example.invalid', phone='12345', is_primary=True)
supplier = Supplier.objects.create(code='VP', name=f'Synthetic Supplier {suffix}', address='Synthetic supplier address', contact_name='Synthetic Vendor', phone='12345', email='vendor@example.invalid')
product = Product.objects.create(code=f'DP{suffix}', name='Synthetic Product')
sku = SKU.objects.create(product=product, sku=f'DP{suffix}', unit='pcs')
order = Order.objects.create(order_no=f'DPSO{suffix}', customer=customer, order_date=date.today(), currency='USD', exchange_rate='7.2')
order.items.create(sku=sku, quantity='2', unit_price='10')
order = confirm_order(order)
purchase = PurchaseOrder.objects.create(purchase_no=f'DPPO{suffix}', supplier=supplier, order=order,
    order_date=date.today(), currency='USD', exchange_rate='7.2', payment_terms_snapshot=[{'label': 'Synthetic balance', 'ratio': '1', 'due_basis': 'no_date', 'offset_days': 0}])
purchase.items.create(sku=sku, quantity='2', unit_price='4')
purchase = place_purchase_order(purchase)
users = get_user_model()
first = users.objects.create_user(username=f'doc-a-{suffix}', password='synthetic-only-password', is_staff=True)
second = users.objects.create_user(username=f'doc-b-{suffix}', password='synthetic-only-password', is_staff=True)
print(json.dumps({'order': order.pk, 'purchase': purchase.pk, 'first_username': first.username,
                  'second_username': second.username, 'first_id': first.pk, 'second_id': second.pk}))
