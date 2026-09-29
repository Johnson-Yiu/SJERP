from datetime import date, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from crm.models import AdvanceAllocation, Customer, Order, PaymentPlan, Product, PurchaseOrder, SKU, Supplier, Transaction
from crm.services.finance import allocate_advance, record_contract_payment, record_transaction, void_transaction


class RefundConsistencyTests(TestCase):
    def setUp(self):
        self.day = date(2032, 2, 1)
        self.customer = Customer.objects.create(code="RG1C", name="Refund customer")
        self.supplier = Supplier.objects.create(code="RG", name="Refund supplier")
        product = Product.objects.create(code="RG1P", name="Refund product")
        self.sku = SKU.objects.create(product=product, sku="RG1-SKU")
        self.order = Order.objects.create(order_no="SO-RG1", customer=self.customer, order_date=self.day, status="confirmed", currency="USD")
        self.order.items.create(sku=self.sku, quantity=10, unit_price=10)
        self.purchase = PurchaseOrder.objects.create(purchase_no="PO-RG1", supplier=self.supplier, order_date=self.day, status="ordered", currency="USD")
        self.purchase.items.create(sku=self.sku, quantity=10, unit_price=10)

    def plans(self, contract, amounts):
        field = "order" if isinstance(contract, Order) else "purchase_order"
        direction = "receivable" if field == "order" else "payable"
        return [PaymentPlan.objects.create(
            **{field: contract}, direction=direction, currency="USD", planned_amount=amount,
            due_date=self.day + timedelta(days=index), notes=f"plan {index}",
        ) for index, amount in enumerate(amounts)]

    def payment(self, contract, amount):
        return record_contract_payment(contract, {
            "amount": amount, "currency": "USD", "exchange_rate": Decimal("7"), "category": "合同收付款",
        })

    def test_customer_refund_reopens_latest_settled_plan_and_void_restores_it(self):
        deposit, balance = self.plans(self.order, [Decimal("30"), Decimal("70")])
        self.payment(self.order, Decimal("100"))

        refund = record_transaction({
            "kind": "refund", "direction": "expense", "order": self.order,
            "amount": Decimal("20"), "currency": "USD", "exchange_rate": Decimal("7"), "category": "客户退款",
        })
        deposit.refresh_from_db()
        balance.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(self.order.paid_amount, Decimal("80"))
        self.assertEqual((deposit.settled_amount, deposit.status), (Decimal("30"), "settled"))
        self.assertEqual((balance.settled_amount, balance.remaining_amount, balance.status), (Decimal("50"), Decimal("20"), "open"))
        self.assertEqual((refund.kind, refund.plan_id), ("refund", balance.pk))

        void_transaction(refund, "退款录入错误")
        deposit.refresh_from_db()
        balance.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(self.order.paid_amount, Decimal("100"))
        self.assertEqual((deposit.status, balance.status), ("settled", "settled"))
        self.assertEqual((deposit.settled_amount, balance.settled_amount), (Decimal("30"), Decimal("70")))

    def test_refund_rejects_amount_above_current_paid_without_side_effects(self):
        plan, = self.plans(self.order, [Decimal("100")])
        self.payment(self.order, Decimal("50"))
        plan.refresh_from_db()
        before = (Transaction.objects.count(), plan.settled_amount)

        with self.assertRaisesMessage(ValidationError, "退款金额不能超过该订单当前已收金额。"):
            record_transaction({"kind": "refund", "direction": "expense", "order": self.order, "amount": 60, "currency": "USD", "exchange_rate": 7})

        plan.refresh_from_db()
        self.assertEqual((Transaction.objects.count(), plan.settled_amount), before)

    def test_refund_crossing_plans_uses_existing_split_history(self):
        deposit, balance = self.plans(self.order, [Decimal("30"), Decimal("70")])
        self.payment(self.order, Decimal("100"))

        root = record_transaction({"kind": "refund", "direction": "expense", "order": self.order, "amount": 80, "currency": "USD", "exchange_rate": 7})
        child = Transaction.objects.get(split_from=root)
        deposit.refresh_from_db()
        balance.refresh_from_db()
        self.assertEqual((root.amount, root.plan_id), (Decimal("70"), balance.pk))
        self.assertEqual((child.amount, child.plan_id), (Decimal("10"), deposit.pk))
        self.assertEqual((deposit.settled_amount, balance.settled_amount), (Decimal("20"), Decimal("0")))

    def test_paid_amount_uses_only_contract_payment_kinds(self):
        Transaction.objects.create(transaction_no="RG1-RECEIPT", transaction_date=self.day, direction="income", kind="customer_receipt", category="收款", amount=100, currency="USD", customer=self.customer, order=self.order)
        Transaction.objects.create(transaction_no="RG1-OTHER", transaction_date=self.day, direction="income", kind="other_income", category="其他收入", amount=20, currency="USD", customer=self.customer, order=self.order)
        Transaction.objects.create(transaction_no="RG1-PAYMENT", transaction_date=self.day, direction="expense", kind="supplier_payment", category="付款", amount=100, currency="USD", supplier=self.supplier, purchase_order=self.purchase)
        Transaction.objects.create(transaction_no="RG1-FEE", transaction_date=self.day, direction="expense", kind="bank_fee", category="手续费", amount=10, currency="USD", supplier=self.supplier, purchase_order=self.purchase)

        self.assertEqual(self.order.paid_amount, Decimal("100"))
        self.assertEqual(self.purchase.paid_amount, Decimal("100"))

    def test_supplier_refund_reopens_payable_and_excess_payment_is_unallocated_payment(self):
        plan, = self.plans(self.purchase, [Decimal("100")])
        self.payment(self.purchase, Decimal("100"))
        refund = record_transaction({
            "kind": "supplier_refund", "direction": "income", "purchase_order": self.purchase,
            "amount": 20, "currency": "USD", "exchange_rate": 7, "category": "供应商退款",
        })
        plan.refresh_from_db()
        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.paid_amount, Decimal("80"))
        self.assertEqual((plan.settled_amount, plan.remaining_amount, plan.status), (Decimal("80"), Decimal("20"), "open"))
        self.assertEqual(refund.kind, "supplier_refund")
        void_transaction(refund, "供应商退款录入错误")
        plan.refresh_from_db()
        self.purchase.refresh_from_db()
        self.assertEqual((self.purchase.paid_amount, plan.settled_amount, plan.status), (Decimal("100"), Decimal("100"), "settled"))

        other_purchase = PurchaseOrder.objects.create(purchase_no="PO-RG1-OVER", supplier=self.supplier, order_date=self.day, status="ordered", currency="USD")
        other_purchase.items.create(sku=self.sku, quantity=1, unit_price=1)
        other_plan, = self.plans(other_purchase, [Decimal("100")])
        root = self.payment(other_purchase, Decimal("120"))
        self.assertEqual(root.kind, "supplier_payment")
        self.assertTrue(Transaction.objects.filter(split_from__isnull=False, kind="unallocated_payment", amount=Decimal("20")).exists())
        other_plan.refresh_from_db()
        self.assertEqual(other_plan.status, "settled")

    def test_refund_against_advance_allocation_preserves_history_and_blocks_unsafe_advance_void(self):
        plan, = self.plans(self.order, [Decimal("100")])
        advance = record_transaction({
            "kind": "unallocated_advance", "direction": "income", "customer": self.customer,
            "amount": 80, "currency": "USD", "exchange_rate": 7, "category": "预收款",
        })
        allocate_advance(advance, plan, Decimal("80"))
        refund = record_transaction({
            "kind": "refund", "direction": "expense", "order": self.order,
            "amount": 20, "currency": "USD", "exchange_rate": 7, "category": "客户退款",
        })
        plan.refresh_from_db()
        self.assertEqual(plan.settled_amount, Decimal("60"))
        self.assertTrue(AdvanceAllocation.objects.get(advance=advance, plan=plan).is_active)

        with self.assertRaisesMessage(ValidationError, "收付款计划已结金额不足"):
            void_transaction(advance, "不能覆盖后续退款")

        refund.refresh_from_db()
        plan.refresh_from_db()
        self.assertEqual(refund.status, "confirmed")
        self.assertEqual(plan.settled_amount, Decimal("60"))
