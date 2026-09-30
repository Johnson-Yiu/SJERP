from datetime import date
from django.test import TestCase
from crm.context import _product_context
from crm.models import Customer, Product, SKU, Order, OrderItem


class ProductWorkspaceTests(TestCase):
    def test_sales_use_historical_model_and_unit_and_exclude_cancelled_orders(self):
        product = Product.objects.create(code="WORKSPACE", name="灯带", sales_model_prefix="COB")
        sku = SKU.objects.create(sku="WORKSPACE-SKU", product=product, sales_model="NEW", unit="pcs")
        customer = Customer.objects.create(code="WORKSPACE-C", name="Workspace customer")
        order = Order.objects.create(order_no="WORKSPACE-O", customer=customer, order_date=date.today(), currency="USD", status="confirmed")
        OrderItem.objects.create(order=order, sku=sku, quantity=2, unit_price=10, unit_snapshot="m", sales_model_snapshot="OLD")
        cancelled = Order.objects.create(order_no="WORKSPACE-X", customer=customer, order_date=date.today(), currency="USD", status="cancelled")
        OrderItem.objects.create(order=cancelled, sku=sku, quantity=100, unit_price=10)
        sections = {section["key"]: section for section in _product_context(product.pk)["sections"]}
        rows = sections["sales"]["rows"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["unit"], "m")
        self.assertEqual(rows[0]["sales_model"], "OLD")
        self.assertEqual(rows[0]["amount"], 20)
        self.assertEqual(rows[0]["_target_id"], order.pk)
