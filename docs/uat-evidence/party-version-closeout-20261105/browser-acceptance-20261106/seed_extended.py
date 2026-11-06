import json, os
from datetime import date
from decimal import Decimal
from uuid import uuid4
os.environ.setdefault('DJANGO_SETTINGS_MODULE','test_support.isolated_settings')
import django
django.setup()
from django.conf import settings
from django.contrib.auth import get_user_model
from test_support.isolated_runtime import verify_isolated_runtime
from crm.models import Customer, Contact, Order, Product, PurchaseOrder, SKU, Supplier
from crm.party_document_details import unknown_details
from crm.party_document_details_models import PartyDocumentDetailsStorage
from crm.services.order_lifecycle import confirm_order
from crm.services.purchase_lifecycle import place_purchase_order
from crm.services.finance import record_contract_payment
from crm.services.fulfillment import record_receipt, confirm_shipment
verify_isolated_runtime(settings=settings, database_must_exist=True)
s = uuid4().hex[:8].upper()
c = Customer.objects.create(code=f'EC{s}',name=f'Synthetic Buyer {s}',country='Germany',address='Synthetic old buyer')
Contact.objects.create(customer=c,name='Synthetic Contact',email='contact@example.invalid',phone='12345',is_primary=True)
v = Supplier.objects.create(code=f'E{s[:5]}',name=f'Synthetic Seller {s}',address='Synthetic old seller')
tc = Customer.objects.create(code=f'ET{s}',name=f'Synthetic Target Buyer {s}',country='France')
tv = Supplier.objects.create(code=f'F{s[:5]}',name=f'Synthetic Target Seller {s}')
product = Product.objects.create(code=f'EP{s}',name='Synthetic Product')
sku = SKU.objects.create(product=product,sku=f'ES{s}',unit='pcs')
order = Order.objects.create(order_no=f'EO{s}',customer=c,order_date=date.today(),currency='USD',exchange_rate='7.2')
order.items.create(sku=sku,quantity='2',unit_price='10')
purchase = PurchaseOrder.objects.create(purchase_no=f'EP{s}',supplier=v,order=order,order_date=date.today(),currency='USD',exchange_rate='7.2',payment_terms_snapshot=[{'label':'Synthetic balance','ratio':'1','due_basis':'no_date','offset_days':0}])
purchase.items.create(sku=sku,quantity='2',unit_price='4')
for obj,kind,side in [(order,'order','buyer'),(purchase,'purchase_order','seller')]:
    details=unknown_details(); details[side]['name']=c.name if kind=='order' else v.name; details[side]['billing_address']='Synthetic original billing'
    PartyDocumentDetailsStorage.objects.create(**{kind:obj},details=details)
order=confirm_order(order); purchase=place_purchase_order(purchase)
record_receipt(purchase.items.first(), {'quantity':Decimal('1'),'receipt_date':date.today(),'unit_cost':Decimal('4')})
confirm_shipment(order, {'shipment_date':date.today(),'items':[{'order_item':order.items.first().pk,'quantity':Decimal('1')}]})
for obj in (order,purchase): record_contract_payment(obj,{'amount':Decimal('2'),'currency':'USD','exchange_rate':Decimal('7.2'),'category':'Synthetic payment'})
users=get_user_model(); a=users.objects.create_user(username=f'ea-{s}',password='synthetic-only-password',is_staff=True); b=users.objects.create_user(username=f'eb-{s}',password='synthetic-only-password',is_staff=True)
print(json.dumps({'order':order.pk,'purchase':purchase.pk,'sku':sku.pk,'replacement_customer':tc.pk,'replacement_supplier':tv.pk,'first_username':a.username,'second_username':b.username,'first_id':a.pk,'second_id':b.pk}))
