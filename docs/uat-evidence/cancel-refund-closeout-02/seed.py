import json
from datetime import date
import django
from django.conf import settings
from django.contrib.auth import get_user_model
django.setup()
from crm.models import Customer, Order, Product, Quote, SKU, Shipment, ShipmentItem
from crm.services.finance import record_transaction, writeoff_receivable
from crm.services.order_lifecycle import confirm_order
from test_support.isolated_runtime import verify_isolated_runtime
verify_isolated_runtime(settings=settings, database_must_exist=True)
customer = Customer.objects.create(code="A-CLOSE", name="合成取消退款验收客户")
product = Product.objects.create(code="A-CLOSE", name="合成验收灯具")
sku = SKU.objects.create(product=product, sku="A-CLOSE-SKU", unit="pcs")
other = SKU.objects.create(product=product, sku="A-CLOSE-ZERO", unit="pcs")
result = {}
for key in ("paid", "partial", "void", "correction"):
    quote = Quote.objects.create(quote_no="QT-CLOSE-"+key, customer=customer, quote_date=date.today(), currency="USD", deposit_ratio=0)
    quote.items.create(sku=sku, quantity=100, unit_price=10)
    order = Order.objects.create(quote=quote, order_no="SO-CLOSE-"+key, customer=customer, order_date=date.today(), currency="USD")
    item = order.items.create(sku=sku, quantity=100, unit_price=10)
    if key == "partial":
        order.items.create(sku=other, quantity=20, unit_price=10)
    order = confirm_order(order)
    receipt = record_transaction(dict(kind="customer_receipt", direction="income", order=order, amount="50" if key == "void" else "999" if key == "correction" else "1000", currency="USD"))
    if key == "correction":
        writeoff_receivable(receipt, order.payment_plans.get(), __import__("decimal").Decimal("1"), "合成授权抹零夹具", "a2-reduction", get_user_model().objects.get(username="codex"))
    if key == "partial":
        shipment = Shipment.objects.create(shipment_no="SHP-CLOSE", order=order, shipment_date=date.today(), status="confirmed")
        ShipmentItem.objects.create(shipment=shipment, order_item=item, sku=sku, quantity=40)
    result[key] = dict(order=order.pk, number=order.order_no, receipt=receipt.pk, receiptNo=receipt.transaction_no)
print(json.dumps(result))
