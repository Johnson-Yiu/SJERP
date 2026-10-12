from datetime import date
from decimal import Decimal
from django.test import TestCase, override_settings
from crm.models import PurchaseOrder, PurchaseOrderItem, RolePermission, Transaction
from crm.serializers import PurchaseOrderSerializer
from crm.tests import test_finance_data_scope as finance_fixture


@override_settings(**finance_fixture.RBAC_SETTINGS, PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class SupplierContextScopeTests(TestCase):
    make_employee = finance_fixture.FinanceDataScopeTests.make_employee

    def setUp(self):
        finance_fixture.FinanceDataScopeTests.setUp(self)
        self.same_department_purchase = self.make_purchase("FOCUSED-SAME", self.orders[1])
        self.own_purchase = self.make_purchase("FOCUSED-OWN", self.orders[0])
        Transaction.objects.create(transaction_no="FOCUSED-PAID", supplier=self.supplier, purchase_order=self.purchase, plan=self.purchase_plan, direction="expense", kind="supplier_payment", amount=20, currency="CNY", exchange_rate=1, transaction_date=date(2026, 10, 12))
        self.purchase_plan.settled_amount = 20
        self.purchase_plan.save()

    def make_purchase(self, number, order):
        purchase = PurchaseOrder.objects.create(purchase_no=number, supplier=self.supplier, order=order, order_date=date(2026, 10, 12), status="ordered", currency="CNY", exchange_rate=1)
        PurchaseOrderItem.objects.create(purchase_order=purchase, sku=self.sku, quantity=1, unit_price=100)
        return purchase

    def deny(self, scope, module):
        RolePermission.objects.filter(role=self.roles[scope], module=module).update(can_view=False)

    def context(self, entity, pk):
        response = self.client.get(f"/api/context/{entity}/{pk}/")
        self.assertEqual(response.status_code, 200, response.data)
        return response.data

    def purchases(self, context):
        return next(section["rows"] for section in context["sections"] if section["key"] == "purchases")

    def assert_sales_hidden(self, row):
        self.assertIsNone(row["order"])
        self.assertEqual(row["order_no"], "")
        self.assertEqual(row["related_orders"], [])

    def assert_finance_hidden(self, row):
        self.assertEqual(row["payment_plans"], [])
        self.assertNotIn("paid_amount", row)
        self.assertNotIn("unpaid_amount", row)

    def test_supplier_view_without_finance_cannot_read_nested_plans_or_paid_metrics(self):
        self.deny("self", "finance")
        context = self.context("suppliers", self.supplier.pk)
        for row in self.purchases(context):
            self.assert_finance_hidden(row)
        self.assertNotIn("已付采购款（人民币）", [metric[0] for metric in context["metrics"]])
        self.assertIn("正式采购金额（人民币）", [metric[0] for metric in context["metrics"]])
        for entity in ("purchase-orders",):
            context = self.context(entity, self.purchase.pk)
            self.assertFalse({"已付款", "待付款"} & {metric[0] for metric in context["metrics"]})

    def test_purchase_view_without_orders_masks_nested_sales_ids_and_allocation_relations(self):
        self.deny("self", "orders")
        context = self.context("suppliers", self.supplier.pk)
        for row in self.purchases(context):
            self.assert_sales_hidden(row)
        response = self.client.get(f"/api/purchase-orders/{self.own_purchase.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assert_sales_hidden(response.data)
        context = self.context("purchase-orders", self.own_purchase.pk)
        self.assertNotIn("orders", [section["entity"] for section in context["sections"]])
        self.assertNotIn(self.orders[0].order_no, str(context))

    def test_self_cannot_read_other_salesperson_order_even_in_same_department(self):
        rows = {row["id"]: row for row in self.purchases(self.context("suppliers", self.supplier.pk))}
        self.assert_sales_hidden(rows[self.same_department_purchase.pk])
        self.assertEqual(rows[self.own_purchase.pk]["order"], self.orders[0].pk)
        self.assertEqual(rows[self.own_purchase.pk]["related_orders"], [{"id": self.orders[0].pk, "order_no": self.orders[0].order_no}])
        self.assertNotIn(self.orders[1].order_no, str(self.context("purchase-orders", self.same_department_purchase.pk)))

    def test_department_scope_keeps_shared_cross_department_purchase_but_masks_its_sales(self):
        self.client.force_authenticate(self.manager.user)
        rows = {row["id"]: row for row in self.purchases(self.context("suppliers", self.supplier.pk))}
        self.assert_sales_hidden(rows[self.purchase.pk])
        self.assertEqual(rows[self.same_department_purchase.pk]["order"], self.orders[1].pk)
        self.assertEqual(rows[self.purchase.pk]["purchase_no"], self.purchase.purchase_no)
        self.assertNotIn(self.orders[3].order_no, str(self.context("purchase-orders", self.purchase.pk)))

    def test_all_scope_cannot_bypass_finance_module(self):
        self.client.force_authenticate(self.all_user.user)
        self.deny("all", "finance")
        for row in self.purchases(self.context("suppliers", self.supplier.pk)):
            self.assert_finance_hidden(row)
        self.assertNotIn("已付采购款（人民币）", str(self.context("suppliers", self.supplier.pk)))
        response = self.client.get(f"/api/purchase-orders/{self.purchase.pk}/")
        self.assert_finance_hidden(response.data)
        self.assertEqual(response.data["order"], self.orders[3].pk)

    def test_all_authorized_can_view_normal_purchase_finance_and_sales(self):
        self.client.force_authenticate(self.all_user.user)
        context = self.context("suppliers", self.supplier.pk)
        rows = {row["id"]: row for row in self.purchases(context)}
        row = rows[self.purchase.pk]
        self.assertEqual(row["order"], self.orders[3].pk)
        self.assertEqual(row["payment_plans"][0]["id"], self.purchase_plan.pk)
        self.assertEqual(Decimal(row["paid_amount"]), 20)
        self.assertEqual(Decimal(row["unpaid_amount"]), 80)
        metrics = {metric[0]: metric[1] for metric in context["metrics"]}
        self.assertEqual(metrics["已付采购款（人民币）"], 20)
        self.assertEqual(metrics["正式采购金额（人民币）"], 300)

    def test_supplier_only_cannot_read_procurement_counts_or_metrics(self):
        self.deny("self", "purchases")
        context = self.context("suppliers", self.supplier.pk)
        self.assertNotIn("purchase-orders", [section["entity"] for section in context["sections"]])
        self.assertFalse({"采购单记录", "正式采购金额（人民币）"} & {metric[0] for metric in context["metrics"]})
        response = self.client.get(f"/api/suppliers/{self.supplier.pk}/")
        self.assertNotIn("purchase_count", response.data)

    def test_missing_serializer_identity_fails_closed_when_rbac_enabled(self):
        row = PurchaseOrderSerializer(self.purchase).data
        self.assert_sales_hidden(row)
        self.assert_finance_hidden(row)

    def test_user_context_is_not_ignored_by_nested_serializer(self):
        self.deny("self", "finance")
        row = PurchaseOrderSerializer(self.purchase, context={"user": self.employee_a.user}).data
        self.assert_sales_hidden(row)
        self.assert_finance_hidden(row)

    def test_fulfillment_nested_shared_purchase_uses_current_identity(self):
        item = self.purchase.items.first()
        existing = item.cost_allocations.get()
        existing.quantity = Decimal("0.5")
        existing.save(update_fields=["quantity"])
        item.cost_allocations.create(target_type="order", order=self.orders[0], quantity=Decimal("0.5"))
        self.deny("self", "finance")
        response = self.client.get(f"/api/orders/{self.orders[0].pk}/fulfillment/")
        self.assertEqual(response.status_code, 200, response.data)
        row = next(row for row in response.data["purchase_orders"] if row["id"] == self.purchase.pk)
        self.assert_sales_hidden({**row, "related_orders": [related for related in row["related_orders"] if related["id"] != self.orders[0].pk]})
        self.assert_finance_hidden(row)
        self.assertNotIn(self.orders[3].order_no, str(response.data))

    def test_transaction_module_is_required_for_paid_summary(self):
        self.deny("self", "transactions")
        context = self.context("suppliers", self.supplier.pk)
        self.assertNotIn("transactions", [section["entity"] for section in context["sections"]])
        self.assertNotIn("已付采购款（人民币）", str(context))
        row = next(row for row in self.purchases(context) if row["id"] == self.purchase.pk)
        self.assertNotIn("paid_amount", row)
        self.assertTrue(row["payment_plans"])
