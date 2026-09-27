from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APIClient

from crm.models import AdvanceAllocation, ContractChangeRequest, Customer, Order, PaymentPlan, Product, PurchaseOrder, SKU, Supplier, Transaction
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

    def test_root_void_rejects_second_call_without_changing_void_history(self):
        plan = PaymentPlan.objects.create(order=self.order, direction="receivable", currency="USD", planned_amount=Decimal("100"))
        root = record_transaction({"plan": plan, "amount": Decimal("120"), "currency": "USD", "exchange_rate": Decimal("7"), "category": "客户收款"})
        child = Transaction.objects.get(split_from=root)
        void_transaction(root, "第一次作废")

        before_rows = list(Transaction.objects.order_by("pk").values_list("pk", "status", "allocated_amount", "void_reason", "voided_at"))
        plan.refresh_from_db()
        before_plan = (plan.status, plan.settled_amount, plan.remaining_amount)
        before_counts = (Transaction.objects.count(), AdvanceAllocation.objects.count())

        with self.assertRaisesMessage(ValidationError, "只有已确认流水可以作废。"):
            void_transaction(root, "第二次作废")

        plan.refresh_from_db()
        self.assertEqual(list(Transaction.objects.order_by("pk").values_list("pk", "status", "allocated_amount", "void_reason", "voided_at")), before_rows)
        self.assertEqual((plan.status, plan.settled_amount, plan.remaining_amount), before_plan)
        self.assertEqual((Transaction.objects.count(), AdvanceAllocation.objects.count()), before_counts)
        self.assertEqual(Transaction.objects.get(pk=child.pk).status, "cancelled")

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

    def test_void_root_restores_cross_order_advance_allocation_and_split_history(self):
        original_plan = PaymentPlan.objects.create(
            order=self.order,
            direction="receivable",
            currency="USD",
            planned_amount=Decimal("100"),
        )
        second_order = Order.objects.create(
            order_no="SO-FIN-SECOND",
            customer=self.customer,
            order_date=date(2026, 8, 23),
            currency="USD",
        )
        second_plan = PaymentPlan.objects.create(
            order=second_order,
            direction="receivable",
            currency="USD",
            planned_amount=Decimal("80"),
        )

        root = record_transaction({
            "plan": original_plan,
            "amount": Decimal("120"),
            "currency": "USD",
            "exchange_rate": Decimal("7"),
            "category": "客户收款",
        })
        advance = Transaction.objects.get(split_from=root, kind="unallocated_advance")
        allocate_advance(advance, second_plan, Decimal("20"))
        allocation = AdvanceAllocation.objects.get(advance=advance, plan=second_plan)

        void_transaction(root, "跨订单预收款录错")

        root.refresh_from_db()
        advance.refresh_from_db()
        original_plan.refresh_from_db()
        second_plan.refresh_from_db()
        allocation.refresh_from_db()
        rows = list(Transaction.objects.order_by("pk"))
        self.assertEqual(root.status, "cancelled")
        self.assertTrue(all(row.status == "cancelled" for row in rows))
        self.assertFalse(allocation.is_active)
        self.assertEqual(original_plan.settled_amount, Decimal("0"))
        self.assertEqual(original_plan.status, "open")
        self.assertEqual(second_plan.settled_amount, Decimal("0"))
        self.assertEqual(second_plan.status, "open")
        self.assertEqual(advance.allocated_amount, Decimal("0"))
        self.assertTrue(all(row.void_reason == "跨订单预收款录错" and row.voided_at for row in rows))

    def test_split_child_cannot_be_voided_directly(self):
        plan = PaymentPlan.objects.create(order=self.order, direction="receivable", currency="USD", planned_amount=Decimal("100"))
        root = record_transaction({"plan": plan, "amount": Decimal("120"), "currency": "USD", "exchange_rate": Decimal("7"), "category": "客户收款"})
        child = Transaction.objects.get(split_from=root)
        before_plan = PaymentPlan.objects.get(pk=plan.pk).settled_amount
        before_counts = (Transaction.objects.count(), AdvanceAllocation.objects.count())

        with self.assertRaisesMessage(ValidationError, "拆分流水必须通过原始流水统一作废。"):
            void_transaction(child, "不应直接作废")

        child.refresh_from_db()
        root.refresh_from_db()
        self.assertEqual(child.status, "confirmed")
        self.assertEqual(root.status, "confirmed")
        self.assertEqual(PaymentPlan.objects.get(pk=plan.pk).settled_amount, before_plan)
        self.assertEqual((Transaction.objects.count(), AdvanceAllocation.objects.count()), before_counts)

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
        plan.refresh_from_db()
        before_rows = list(Transaction.objects.order_by("pk").values_list("pk", "status", "allocated_amount", "void_reason", "voided_at"))
        before_counts = (Transaction.objects.count(), AdvanceAllocation.objects.count())
        before_advance = (advance.status, advance.allocated_amount)
        before_plan = (plan.status, plan.settled_amount)

        with self.assertRaisesMessage(ValidationError, "缺少核销明细"):
            void_transaction(advance, "核销数据异常")

        advance.refresh_from_db()
        plan.refresh_from_db()
        self.assertEqual(advance.status, "confirmed")
        self.assertTrue(advance.allocations.get().is_active)
        self.assertEqual(plan.settled_amount, Decimal("50"))
        self.assertEqual(list(Transaction.objects.order_by("pk").values_list("pk", "status", "allocated_amount", "void_reason", "voided_at")), before_rows)
        self.assertEqual((Transaction.objects.count(), AdvanceAllocation.objects.count()), before_counts)
        self.assertEqual((advance.status, advance.allocated_amount), before_advance)
        self.assertEqual((plan.status, plan.settled_amount), before_plan)

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

    def test_void_rollback_underflow_is_atomic_across_root_and_split_child(self):
        plan = PaymentPlan.objects.create(order=self.order, direction="receivable", currency="USD", planned_amount=Decimal("100"))
        root = record_transaction({"plan": plan, "amount": Decimal("120"), "currency": "USD", "exchange_rate": Decimal("7"), "category": "客户收款"})
        child = Transaction.objects.get(split_from=root)
        PaymentPlan.objects.filter(pk=plan.pk).update(settled_amount=Decimal("50"), status="open")
        before = {
            "rows": list(Transaction.objects.order_by("pk").values_list("pk", "status", "allocated_amount", "void_reason", "voided_at")),
            "plan": PaymentPlan.objects.get(pk=plan.pk).settled_amount,
            "counts": (Transaction.objects.count(), AdvanceAllocation.objects.count()),
        }

        with self.assertRaisesMessage(ValidationError, "收付款计划已结金额不足"):
            void_transaction(root, "回滚下溢")

        self.assertEqual(list(Transaction.objects.order_by("pk").values_list("pk", "status", "allocated_amount", "void_reason", "voided_at")), before["rows"])
        self.assertEqual(PaymentPlan.objects.get(pk=plan.pk).settled_amount, before["plan"])
        self.assertEqual((Transaction.objects.count(), AdvanceAllocation.objects.count()), before["counts"])
        self.assertEqual(Transaction.objects.get(pk=child.pk).status, "confirmed")

    def test_record_transaction_rejects_wrong_currency_without_side_effects(self):
        usd_plan = PaymentPlan.objects.create(order=self.order, direction="receivable", currency="USD", planned_amount=Decimal("100"))
        cny_order = Order.objects.create(order_no="SO-FIN-CNY", customer=self.customer, order_date=self.order.order_date, currency="CNY")
        cny_plan = PaymentPlan.objects.create(order=cny_order, direction="receivable", currency="CNY", planned_amount=Decimal("100"))
        before = (Transaction.objects.count(), usd_plan.settled_amount, cny_plan.settled_amount)

        with self.assertRaisesMessage(ValidationError, "实际收付款币种必须与计划原币一致。"):
            record_transaction({"plan": usd_plan, "amount": Decimal("10"), "currency": "EUR", "exchange_rate": Decimal("7"), "category": "客户收款"})
        with self.assertRaisesMessage(ValidationError, "人民币流水汇率必须为 1。"):
            record_transaction({"plan": cny_plan, "amount": Decimal("10"), "currency": "CNY", "exchange_rate": Decimal("2"), "category": "客户收款"})

        usd_plan.refresh_from_db()
        cny_plan.refresh_from_db()
        self.assertEqual((Transaction.objects.count(), usd_plan.settled_amount, cny_plan.settled_amount), before)

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
