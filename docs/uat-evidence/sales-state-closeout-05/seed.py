"""Seed isolated S5 sales list cases."""
import json
from datetime import date

import django

django.setup()
from django.conf import settings
from test_support.isolated_runtime import verify_isolated_runtime

verify_isolated_runtime(settings=settings, database_must_exist=True)

from crm.models import Customer, InventoryMovement, Order, OrderItem, Product, Quote, SKU

customer = Customer.objects.create(code="S5-C001", name="S5 合成商业展厅照明采购及设施维护服务有限公司")
product = Product.objects.create(code="S5-P001", name="S5 合成商业展厅轨道灯")
sku = SKU.objects.create(product=product, sku="S5-SKU-001", unit="pcs")
orders = {}
identifiers = {}
for status in ("draft", "confirmed", "production", "shipped", "completed", "cancelled"):
    number = f"S5-SO-{status.upper()}-LONG-REFERENCE"
    order = Order.objects.create(
        order_no=number, customer=customer, order_date=date.today(),
        status=status, currency="CNY", exchange_rate=1,
    )
    OrderItem.objects.create(order=order, sku=sku, quantity=2, unit_price=30)
    OrderItem.objects.create(order=order, sku=sku, quantity=3, unit_price=25)
    orders[status] = number
    identifiers[status] = order.pk
quote = Quote.objects.create(
    quote_no="S5-QUO-DETAIL-LONG-REFERENCE", customer=customer, quote_date=date.today(),
    buyer_company_name=customer.name, notes="S5 合成报价条款备注",
)
previous_quote = Quote.objects.create(
    quote_no="S5-QUO-PREVIOUS", customer=customer, quote_date=date.today(),
    buyer_company_name=customer.name, notes="S5 上一报价独立备注",
)
InventoryMovement.objects.create(
    movement_no="S5-STOCK-001", movement_date=date.today(), type="other_in",
    sku=sku, quantity=100, warehouse="默认仓",
)
confirm_orders = []
for index in range(6):
    draft = Order.objects.create(
        order_no=f"S5-CONFIRM-{index + 1}", customer=customer, quote=quote,
        order_date=date.today(), currency="CNY", exchange_rate=1,
    )
    OrderItem.objects.create(order=draft, sku=sku, quantity=2, unit_price=30)
    confirm_orders.append(draft.pk)
print(json.dumps({
    "orders": orders, "identifiers": identifiers, "quote": quote.pk,
    "previousQuote": previous_quote.pk, "confirmOrders": confirm_orders,
}))
