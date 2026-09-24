from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APIClient

from crm.models import ContractChangeRequest, Customer, Order, PaymentPlan, Product, PurchaseOrder, SKU, Supplier, Transaction
from crm.services.finance import allocate_advance, approve_contract_change, ensure_default_payment_plans, record_contract_payment, record_transaction, void_transaction


class PaymentPlanModelTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        customer = Customer.objects.create(code="C-FIN-MODEL", name="Finance Buyer")
        self.customer = customer
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
    def make_purchase_plan(self, amount=Decimal("100")):
        supplier = Supplier.objects.create(code=f"SUP-{Supplier.objects.count()}", name="Finance Supplier")
        purchase = PurchaseOrder.objects.create(
            purchase_no=f"PO-FIN-{PurchaseOrder.objects.count()}", supplier=supplier,
            order_date=self.order.order_date, status="ordered", currency="USD",
        )
        purchase.items.create(sku=self.order.items.first().sku, quantity=Decimal("10"), unit_price=Decimal("5"))
        plan = PaymentPlan.objects.create(purchase_order=purchase, direction="payable", currency="USD", planned_amount=amount)
        return purchase, plan, supplier

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

    def test_approved_order_change_appends_receivable_plan(self):
        change = ContractChangeRequest.objects.create(order=self.order, amount_delta=Decimal("20"), notes="客户追加")

        plan = approve_contract_change(change)

        change.refresh_from_db()
        self.assertEqual(change.status, "approved")
        self.assertEqual(plan.planned_amount, Decimal("20"))
        self.assertEqual(plan.direction, "receivable")

    def test_void_records_reason_timestamp_and_restores_payment_plan(self):
        plan = PaymentPlan.objects.create(order=self.order, direction="receivable", currency="USD", planned_amount=Decimal("100"))
        row = record_transaction({"plan": plan, "amount": Decimal("30"), "currency": "USD", "exchange_rate": Decimal("7"), "category": "客户收款"})

        void_transaction(row, "金额录入错误")

        row.refresh_from_db()
        plan.refresh_from_db()
        self.assertEqual(row.status, "cancelled")
        self.assertEqual(row.void_reason, "金额录入错误")
        self.assertIsNotNone(row.voided_at)
        self.assertEqual(plan.settled_amount, Decimal("0"))
        self.assertEqual(plan.status, "open")

    def test_supplier_payment_void_restores_payable_plan(self):
        _, plan, _ = self.make_purchase_plan()
        row = record_transaction({"plan": plan, "amount": Decimal("40"), "currency": "USD", "exchange_rate": Decimal("7"), "category": "供应商付款"})

        void_transaction(row, "供应商付款录错")

        plan.refresh_from_db()
        self.assertEqual(plan.settled_amount, Decimal("0"))
        self.assertEqual(plan.status, "open")

    def test_root_void_recursively_cancels_split_rows_and_restores_all_plans(self):
        root = record_contract_payment(self.order, {"amount": Decimal("150"), "currency": "USD", "exchange_rate": Decimal("7"), "category": "客户收款"})
        split_rows = list(Transaction.objects.exclude(pk=root.pk).order_by("pk"))
        plans = list(self.order.payment_plans.order_by("pk"))
        self.assertTrue(split_rows)
        self.assertTrue(all(plan.status == "settled" for plan in plans))

        void_transaction(root, "跨计划收款录错")

        self.assertTrue(all(row.status == "cancelled" for row in Transaction.objects.order_by("pk")))
        self.assertTrue(all(row.void_reason == "跨计划收款录错" and row.voided_at for row in Transaction.objects.order_by("pk")))
        for plan in plans:
            plan.refresh_from_db()
        self.assertTrue(all(plan.status == "open" and plan.settled_amount == 0 for plan in plans))

    def test_split_child_cannot_be_voided_directly(self):
        plan = PaymentPlan.objects.create(order=self.order, direction="receivable", currency="USD", planned_amount=Decimal("100"))
        root = record_transaction({"plan": plan, "amount": Decimal("120"), "currency": "USD", "exchange_rate": Decimal("7"), "category": "客户收款"})
        child = Transaction.objects.get(split_from=root)
        before_plan = PaymentPlan.objects.get(pk=plan.pk).settled_amount

        with self.assertRaisesMessage(ValidationError, "拆分流水必须通过原始流水统一作废。"):
            void_transaction(child, "不应直接作废")

        child.refresh_from_db()
        root.refresh_from_db()
        self.assertEqual(child.status, "confirmed")
        self.assertEqual(root.status, "confirmed")
        self.assertEqual(PaymentPlan.objects.get(pk=plan.pk).settled_amount, before_plan)

    def test_advance_allocation_void_deactivates_allocation_and_restores_plan(self):
        plan = PaymentPlan.objects.create(order=self.order, direction="receivable", currency="USD", planned_amount=Decimal("80"))
        advance = Transaction.objects.create(
            transaction_no="ADV-VOID-1", transaction_date=self.order.order_date, direction="income",
            kind="unallocated_advance", category="未分配预收预付", amount=Decimal("50"),
            rmb_amount=Decimal("350"), currency="USD", exchange_rate=Decimal("7"), customer=self.customer,
        )
        allocate_advance(advance, plan, Decimal("50"))

        void_transaction(advance, "预收款录错")

        advance.refresh_from_db()
        plan.refresh_from_db()
        self.assertEqual(advance.status, "cancelled")
        self.assertEqual(advance.allocated_amount, Decimal("0"))
        self.assertFalse(advance.allocations.get().is_active)
        self.assertEqual(plan.settled_amount, Decimal("0"))

    def test_standalone_unallocated_payment_void_restores_payable_plan(self):
        _, plan, supplier = self.make_purchase_plan()
        advance = Transaction.objects.create(
            transaction_no="ADV-VOID-2", transaction_date=self.order.order_date, direction="expense",
            kind="unallocated_payment", category="未分配预付款", amount=Decimal("50"),
            rmb_amount=Decimal("350"), currency="USD", exchange_rate=Decimal("7"), supplier=supplier,
        )
        allocate_advance(advance, plan, Decimal("50"))

        void_transaction(advance, "预付款录错")

        plan.refresh_from_db()
        self.assertEqual(plan.settled_amount, Decimal("0"))
        self.assertEqual(plan.status, "open")
        self.assertFalse(advance.allocations.get().is_active)

    def test_allocation_mismatch_rejects_void_without_changes(self):
        plan = PaymentPlan.objects.create(order=self.order, direction="receivable", currency="USD", planned_amount=Decimal("80"))
        advance = Transaction.objects.create(
            transaction_no="ADV-VOID-3", transaction_date=self.order.order_date, direction="income",
            kind="unallocated_advance", category="未分配预收预付", amount=Decimal("50"),
            rmb_amount=Decimal("350"), currency="USD", exchange_rate=Decimal("7"), customer=self.customer,
        )
        allocate_advance(advance, plan, Decimal("50"))
        advance.allocated_amount = Decimal("40")
        advance.save(update_fields=["allocated_amount"])

        with self.assertRaisesMessage(ValidationError, "缺少核销明细"):
            void_transaction(advance, "核销数据异常")

        advance.refresh_from_db()
        plan.refresh_from_db()
        self.assertEqual(advance.status, "confirmed")
        self.assertTrue(advance.allocations.get().is_active)
        self.assertEqual(plan.settled_amount, Decimal("50"))

    def test_insufficient_payment_plan_settlement_rejects_void_atomically(self):
        plan = PaymentPlan.objects.create(order=self.order, direction="receivable", currency="USD", planned_amount=Decimal("100"))
        row = record_transaction({"plan": plan, "amount": Decimal("30"), "currency": "USD", "exchange_rate": Decimal("7"), "category": "客户收款"})
        PaymentPlan.objects.filter(pk=plan.pk).update(settled_amount=Decimal("10"), status="open")

        with self.assertRaisesMessage(ValidationError, "已结金额不足"):
            void_transaction(row, "计划数据异常")

        row.refresh_from_db()
        plan.refresh_from_db()
        self.assertEqual(row.status, "confirmed")
        self.assertIsNone(row.voided_at)
        self.assertEqual(plan.settled_amount, Decimal("10"))

    def test_refund_void_does_not_change_payment_plans(self):
        plan = PaymentPlan.objects.create(order=self.order, direction="receivable", currency="USD", planned_amount=Decimal("100"))
        row = Transaction.objects.create(
            transaction_no="REF-VOID-1", transaction_date=self.order.order_date, direction="expense",
            kind="refund", category="客户退款", amount=Decimal("10"), rmb_amount=Decimal("70"),
            currency="USD", exchange_rate=Decimal("7"), customer=self.customer, order=self.order,
        )
        before = plan.settled_amount

        void_transaction(row, "退款流水录错")

        plan.refresh_from_db()
        row.refresh_from_db()
        self.assertEqual(plan.settled_amount, before)
        self.assertEqual(row.status, "cancelled")

    def test_void_transaction_api_requires_reason_and_records_metadata(self):
        plan = PaymentPlan.objects.create(order=self.order, direction="receivable", currency="USD", planned_amount=Decimal("100"))
        row = record_transaction({"plan": plan, "amount": Decimal("30"), "currency": "USD", "exchange_rate": Decimal("7"), "category": "客户收款"})
        url = f"/api/transactions/{row.pk}/void/"

        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        row.refresh_from_db()
        self.assertEqual(row.status, "confirmed")

        response = self.client.post(url, {"reason": "API 作废原因"}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        row.refresh_from_db()
        self.assertEqual(response.data["void_reason"], "API 作废原因")
        self.assertIsNotNone(response.data["voided_at"])

        response = self.client.post(url, {"reason": "重复作废"}, format="json")
        self.assertEqual(response.status_code, 400, response.data)
