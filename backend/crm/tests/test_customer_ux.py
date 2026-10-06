from datetime import date
from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient
from crm.models import Customer, Product, SKU, Quote, QuoteItem, Order, OrderItem

class CustomerUXTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = Customer.objects.create(code="UX-C1",name="UX Buyer",region="Europe",next_follow_up=date(2026,10,10))
        product = Product.objects.create(code="UX-P1",name="UX Light")
        sku = SKU.objects.create(product=product,sku="UX-S1")
        self.quote = Quote.objects.create(customer=self.customer,quote_no="UX-Q1",quote_date=date(2026,10,7))
        QuoteItem.objects.create(quote=self.quote,sku=sku,quantity=2,unit_price=3)
        self.order = Order.objects.create(customer=self.customer,order_no="UX-O1",order_date=date(2026,10,7),status="confirmed",exchange_rate=2)
        OrderItem.objects.create(order=self.order,sku=sku,quantity=2,unit_price=3)
    def context(self,entity,pk):
        response=self.client.get(f"/api/context/{entity}/{pk}/")
        self.assertEqual(response.status_code,200)
        return response.data
    def test_customer_hierarchy_and_metrics(self):
        data=self.context("customers",self.customer.id)
        self.assertEqual([s["key"] for s in data["sections"]],["followups","quotes","orders","contacts","purchases","cash"])
        self.assertEqual([m[0] for m in data["metrics"]],["累计销售额","订单","报价","下次跟进"])
        self.assertEqual(data["metrics"][0][1],Decimal("12"))
        self.assertEqual(data["metrics"][1][1],1)
        self.assertEqual(data["metrics"][3][1],date(2026,10,10))
        self.assertEqual([i[0] for i in data["info"]],["负责人","业务区域","来源","网站","地址","备注"])
        self.assertEqual(dict(data["info"])["业务区域"],"Europe")
    def test_unscheduled_customer(self):
        self.customer.next_follow_up=None; self.customer.save()
        self.assertEqual(self.context("customers",self.customer.id)["metrics"][3][1],"未安排")
    def test_quote_lines_first(self):
        data=self.context("quotes",self.quote.id)
        self.assertEqual([s["key"] for s in data["sections"]],["items","orders","customer"])
        self.assertEqual(len(data["sections"][0]["rows"]),1)
    def test_order_lines_first(self):
        data=self.context("orders",self.order.id)
        self.assertEqual([s["key"] for s in data["sections"]],["items","payments","inventory","quote","customer"])
        self.assertEqual(len(data["sections"][0]["rows"]),1)
    def test_sold_history_retains_formal_order_target(self):
        Order.objects.create(customer=self.customer,order_no="UX-DRAFT",order_date=date(2026,10,7))
        section=next(s for s in self.context("customers",self.customer.id)["sections"] if s["key"]=="purchases")
        self.assertEqual(section["title"],"成交商品记录")
        self.assertEqual(len(section["rows"]),1)
        self.assertEqual(section["rows"][0]["_target_entity"],"orders")
        self.assertEqual(section["rows"][0]["_target_id"],self.order.id)
