import json
from datetime import date
import django
from django.conf import settings
django.setup()

from crm.models import Customer, Order, Product, Quote, SKU
from crm.services.finance import record_transaction
from crm.services.order_lifecycle import confirm_order
from test_support.isolated_runtime import verify_isolated_runtime

verify_isolated_runtime(settings=settings, database_must_exist=True)
customer = Customer.objects.create(code="B-CANCEL", name="合成取消退款客户")
product = Product.objects.create(code="B-CANCEL", name="合成灯具")
sku = SKU.objects.create(product=product, sku="B-CANCEL-SKU", unit="pcs")
quote = Quote.objects.create(quote_no="QT-CANCEL-B", customer=customer, quote_date=date.today(), currency="CNY", deposit_ratio=0)
quote.items.create(sku=sku, quantity=10, unit_price=100)
order = Order.objects.create(quote=quote, order_no="SO-CANCEL-B", customer=customer, order_date=date.today(), currency="CNY")
order.items.create(sku=sku, quantity=10, unit_price=100)
order = confirm_order(order)
receipt = record_transaction(dict(kind="customer_receipt", direction="income", order=order,
                                  amount="1000", currency="CNY"))
print(json.dumps(dict(order=order.pk, number=order.order_no, receipt=receipt.pk, receiptNo=receipt.transaction_no)))
