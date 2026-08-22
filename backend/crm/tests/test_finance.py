from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from crm.models import Customer, Order, PaymentPlan, Product, SKU


class PaymentPlanModelTests(TestCase):
    def setUp(self):
        customer = Customer.objects.create(code="C-FIN-MODEL", name="Finance Buyer")
        product = Product.objects.create(code="P-FIN-MODEL", name="Finance Light")
        sku = SKU.objects.create(product=product, sku="SKU-FIN-MODEL")
        self.order = Order.objects.create(
            order_no="SO-FIN-MODEL",
            customer=customer,
            order_date=date(2026, 8, 22),
            currency="USD",
        )
        self.order.items.create(sku=sku, quantity=Decimal("10"), unit_price=Decimal("10"))

    def test_plan_requires_exactly_one_contract(self):
        plan = PaymentPlan(
            direction="receivable",
            currency="USD",
            planned_amount=Decimal("100"),
        )

        with self.assertRaises(ValidationError):
            plan.full_clean()

    def test_plan_with_order_is_valid(self):
        plan = PaymentPlan(
            order=self.order,
            direction="receivable",
            currency="USD",
            planned_amount=Decimal("100"),
        )

        plan.full_clean()
