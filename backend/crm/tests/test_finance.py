from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from crm.models import Customer, Order, PaymentPlan, Product, SKU, Transaction
from crm.services.finance import allocate_advance, ensure_default_payment_plans, record_transaction


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


class FinanceServiceTests(PaymentPlanModelTests):
    def test_excess_receipt_creates_unallocated_advance(self):
        plan = PaymentPlan.objects.create(
            order=self.order,
            direction="receivable",
            currency="USD",
            planned_amount=Decimal("100"),
        )

        receipt = record_transaction({
            "plan": plan,
            "amount": Decimal("120"),
            "currency": "USD",
            "exchange_rate": Decimal("7.2"),
            "category": "客户收款",
        })

        plan.refresh_from_db()
        self.assertEqual(receipt.amount, Decimal("100"))
        self.assertEqual(plan.status, "settled")
        self.assertTrue(Transaction.objects.filter(kind="unallocated_advance", amount=Decimal("20")).exists())

    def test_default_plan_uses_deposit_and_balance(self):
        plans = ensure_default_payment_plans(self.order)

        self.assertEqual([row.planned_amount for row in plans], [Decimal("30.00"), Decimal("70.00")])

    def test_unallocated_advance_can_be_allocated_to_same_customer_plan(self):
        advance = Transaction.objects.create(
            transaction_no="ADV-FIN-001", transaction_date=date(2026, 8, 22), direction="income",
            kind="unallocated_advance", category="未分配预收预付", amount=Decimal("50"),
            rmb_amount=Decimal("360"), currency="USD", exchange_rate=Decimal("7.2"), customer=self.order.customer,
        )
        plan = PaymentPlan.objects.create(order=self.order, direction="receivable", currency="USD", planned_amount=Decimal("100"))

        allocate_advance(advance, plan, Decimal("50"))

        advance.refresh_from_db()
        plan.refresh_from_db()
        self.assertEqual(advance.allocated_amount, Decimal("50"))
        self.assertEqual(plan.settled_amount, Decimal("50"))
