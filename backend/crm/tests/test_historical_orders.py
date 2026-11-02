from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from crm.models import AccessRole, Customer, EmployeeProfile, GoodsReceipt, InventoryMovement, InventoryReservation, Order, OrderItem, OrganizationUnit, PaymentPlan, Position, Product, ProductCategory, PurchaseCostAllocation, PurchaseOrder, Shipment, SKU, Supplier, Transaction, RolePermission
from crm.services.finance import record_transaction


class HistoricalOrderIsolationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = Customer.objects.create(code="HIST-C", name="历史客户", country="中国")
        self.supplier = Supplier.objects.create(code="HS", name="历史供应商", country="中国")
        self.sku = SKU.objects.create(
            sku="HIST-SKU",
            product=Product.objects.create(code="HIST-P", name="历史灯具"),
            unit="pcs",
            cost_price=0,
        )

    def sales_payload(self):
        return {
            "customer": self.customer.pk,
            "order_date": "2019-06-15",
            "currency": "CNY",
            "exchange_rate": "1",
            "items": [{"sku": self.sku.pk, "quantity": "12", "unit_price": "80"}],
        }

    def purchase_payload(self):
        return {
            "supplier": self.supplier.pk,
            "order_date": "2019-05-20",
            "currency": "CNY",
            "exchange_rate": "1",
            "items": [{"sku": self.sku.pk, "quantity": "20", "unit_price": "30"}],
        }

    def test_historical_sales_entry_preserves_date_and_creates_no_formal_side_effects(self):
        response = self.client.post("/api/orders/historical/", self.sales_payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        order = self._get_order(response.data["id"])
        self.assertTrue(order.historical_only)
        self.assertEqual(order.status, "historical")
        self.assertEqual(order.order_date, date(2019, 6, 15))
        self.assertEqual(order.total_amount, Decimal("960"))
        self.assertFalse(PaymentPlan.objects.filter(order=order).exists())
        self.assertFalse(InventoryReservation.objects.filter(order_item__order=order).exists())
        self.assertFalse(Transaction.objects.filter(order=order).exists())
        self.assertFalse(Shipment.objects.filter(order=order).exists())
        self.assertFalse(InventoryMovement.objects.filter(order=order).exists())
        self.assertEqual(self.client.get("/api/orders/").data["count"], 0)
        self.assertEqual(self.client.get("/api/orders/", {"status": "historical"}).data["count"], 1)
        self.assertEqual(self.client.post(f"/api/orders/{order.pk}/confirm/", {}, format="json").status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.client.post(f"/api/orders/{order.pk}/generate-purchase-drafts/", {"groups": []}, format="json").status_code, status.HTTP_400_BAD_REQUEST)

    def test_historical_purchase_entry_preserves_date_and_blocks_place_and_payment(self):
        response = self.client.post("/api/purchase-orders/historical/", self.purchase_payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        purchase = PurchaseOrder.objects.get(pk=response.data["id"])
        self.assertTrue(purchase.historical_only)
        self.assertEqual(purchase.status, "historical")
        self.assertEqual(purchase.order_date, date(2019, 5, 20))
        self.assertFalse(PaymentPlan.objects.filter(purchase_order=purchase).exists())
        self.assertFalse(Transaction.objects.filter(purchase_order=purchase).exists())
        self.assertFalse(GoodsReceipt.objects.filter(purchase_item__purchase_order=purchase).exists())
        self.assertFalse(InventoryMovement.objects.filter(reference=purchase.purchase_no).exists())
        self.assertFalse(PurchaseCostAllocation.objects.filter(purchase_item__purchase_order=purchase).exists())
        self.assertEqual(self.client.get("/api/purchase-orders/").data["count"], 0)
        self.assertEqual(self.client.get("/api/purchase-orders/", {"status": "historical"}).data["count"], 1)
        self.assertEqual(self.client.post(f"/api/purchase-orders/{purchase.pk}/place/", {}, format="json").status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.client.post(f"/api/purchase-orders/{purchase.pk}/pay/", {"amount": "1", "transaction_date": "2019-05-20"}, format="json").status_code, status.HTTP_400_BAD_REQUEST)

    def test_historical_mode_cannot_be_smuggled_through_formal_create_endpoints(self):
        self.assertEqual(self.client.post("/api/orders/", {**self.sales_payload(), "is_historical": True}, format="json").status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.client.post("/api/purchase-orders/", {**self.purchase_payload(), "status": "historical"}, format="json").status_code, status.HTTP_400_BAD_REQUEST)

    def test_formal_reports_exclude_history_and_separate_analysis_includes_it(self):
        history_response = self.client.post("/api/orders/historical/", self.sales_payload(), format="json")
        self.assertEqual(history_response.status_code, status.HTTP_201_CREATED, history_response.data)
        formal = self._get_order(self.client.post("/api/orders/", {
            **self.sales_payload(), "order_date": "2026-06-15", "items": [{"sku": self.sku.pk, "quantity": "2", "unit_price": "80"}],
        }, format="json").data["id"])
        formal.status = "confirmed"
        formal.save(update_fields=["status"])
        report = self.client.get("/api/reports/data/", {"source": "sales", "group_by": "customer", "date_from": "2019-01-01", "date_to": "2026-12-31"})
        self.assertEqual(report.status_code, status.HTTP_200_OK, report.data)
        self.assertEqual(report.data["totals"]["count"], 1)
        historical = self.client.get("/api/reports/historical/", {"date_from": "2019-01-01", "date_to": "2019-12-31"})
        self.assertEqual(historical.status_code, status.HTTP_200_OK, historical.data)
        self.assertEqual(historical.data["sales"]["order_count"], 1)
        self.assertEqual(historical.data["sales"]["amount_rmb"], Decimal("960"))
        self.assertFalse(historical.data["profit"]["available"])

    def test_historical_order_never_inherits_current_sku_cost(self):
        self.sku.cost_price = Decimal("99.50")
        self.sku.save(update_fields=["cost_price"])
        response = self.client.post("/api/orders/historical/", self.sales_payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        item = OrderItem.objects.get(order_id=response.data["id"])
        self.assertEqual(item.cost_price, Decimal("0"))
        self.assertFalse(Transaction.objects.filter(order_id=response.data["id"]).exists())

    def test_all_transaction_kinds_reject_historical_contract_references(self):
        sales = self.client.post("/api/orders/historical/", self.sales_payload(), format="json")
        purchase = self.client.post("/api/purchase-orders/historical/", self.purchase_payload(), format="json")
        self.assertEqual(sales.status_code, status.HTTP_201_CREATED, sales.data)
        self.assertEqual(purchase.status_code, status.HTTP_201_CREATED, purchase.data)
        order = Order.objects.get(pk=sales.data["id"])
        purchase_order = PurchaseOrder.objects.get(pk=purchase.data["id"])
        before = Transaction.objects.count()
        for kind, direction, contract_key, contract_id in (
            ("other", "expense", "order", order.pk),
            ("other_income", "income", "order", order.pk),
            ("other", "expense", "purchase_order", purchase_order.pk),
            ("other_income", "income", "purchase_order", purchase_order.pk),
        ):
            response = self.client.post("/api/transactions/", {
                "kind": kind, "direction": direction, "category": "历史隔离回归",
                "amount": "10", "currency": "CNY", "exchange_rate": "1",
                "transaction_date": "2026-10-22", contract_key: contract_id,
            }, format="json")
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
            self.assertIn("历史订单", str(response.data))
        plan = PaymentPlan.objects.create(order=order, direction="receivable", currency="CNY", planned_amount=Decimal("10"))
        response = self.client.post("/api/transactions/", {
            "kind": "other", "direction": "expense", "category": "历史计划隔离",
            "amount": "10", "currency": "CNY", "exchange_rate": "1",
            "transaction_date": "2026-10-22", "plan": plan.pk,
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertEqual(Transaction.objects.count(), before)
        with self.assertRaises(ValidationError):
            record_transaction({
                "order": order, "kind": "other_income", "direction": "income",
                "category": "服务层历史隔离", "amount": Decimal("10"),
                "currency": "CNY", "exchange_rate": Decimal("1"),
            })
        independent = self.client.post("/api/transactions/", {
            "kind": "other", "direction": "expense", "category": "独立登记",
            "amount": "10", "currency": "CNY", "exchange_rate": "1",
            "transaction_date": "2026-10-22",
        }, format="json")
        self.assertEqual(independent.status_code, status.HTTP_201_CREATED, independent.data)

    def _get_order(self, pk):
        from crm.models import Order
        return Order.objects.get(pk=pk)


RBAC_SETTINGS = {
    "APP_STAGE": "production", "DEBUG": False,
    "DEVELOPMENT_SUPERADMIN": False, "RBAC_ENFORCEMENT": True,
}


@override_settings(**RBAC_SETTINGS, PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class HistoricalAnalysisPermissionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.unit = OrganizationUnit.objects.create(name="历史分析测试部", code="HIST-ANALYSIS-UNIT")
        self.position = Position.objects.create(unit=self.unit, name="历史分析", code="HIST-ANALYSIS-POS")
        self.role = AccessRole.objects.create(name="历史分析角色", code="hist-analysis", default_data_scope="all")
        self.user = get_user_model().objects.create_user(username="hist-analysis-user", password="test")
        profile = EmployeeProfile.objects.create(user=self.user, display_name="历史分析测试员", unit=self.unit, position=self.position)
        profile.roles.add(self.role)
        for module in ("orders", "purchases"):
            RolePermission.objects.create(role=self.role, module=module, can_view=True)
        self.customer = Customer.objects.create(code="HIST-P-C", name="受限历史客户", country="中国")
        self.supplier = Supplier.objects.create(code="HP", name="受限历史供应商", country="德国")
        category = ProductCategory.objects.create(name="历史分类")
        product = Product.objects.create(code="HIST-P-P", name="历史产品", category=category)
        self.sku = SKU.objects.create(sku="HIST-P-SKU", product=product, display_name_cn="历史产品 SKU")
        self.order = Order.objects.create(order_no="HIST-P-SO", customer=self.customer, order_date=date(2020, 1, 2), status="historical", historical_only=True, currency="CNY", exchange_rate=1)
        OrderItem.objects.create(order=self.order, sku=self.sku, quantity=3, unit_price=100, cost_price=0, display_name_snapshot="历史产品快照")
        self.purchase = PurchaseOrder.objects.create(purchase_no="HIST-P-PO", supplier=self.supplier, order_date=date(2020, 1, 3), status="historical", historical_only=True, currency="CNY", exchange_rate=1)
        self.purchase.items.create(sku=self.sku, quantity=4, unit_price=30, display_name_snapshot="历史产品采购快照")

    def grant(self, module, **values):
        RolePermission.objects.update_or_create(role=self.role, module=module, defaults=values)

    def test_aggregate_is_available_without_identity_dimensions_but_sku_data_is_hidden(self):
        self.client.force_authenticate(self.user)
        response = self.client.get("/api/reports/historical/", {"date_from": "2020-01-01", "date_to": "2020-12-31"})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["sales"]["order_count"], 1)
        self.assertEqual(response.data["sales"]["by_customer"], [])
        self.assertEqual(response.data["sales"]["by_sku"], [])
        self.assertEqual(response.data["purchase"]["by_supplier"], [])
        self.grant("skus", can_view=True)
        response = self.client.get("/api/reports/historical/", {"date_from": "2020-01-01", "date_to": "2020-12-31"})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["sales"]["by_sku"][0]["id"], self.sku.pk)
        self.grant("customers", can_view=True)
        response = self.client.get("/api/reports/historical/", {"date_from": "2020-01-01", "date_to": "2020-12-31"})
        self.assertEqual(response.data["sales"]["by_customer"][0]["id"], self.customer.pk)
        self.assertEqual(response.data["purchase"]["by_supplier"], [])

    def test_anonymous_and_unprivileged_history_analysis_are_denied(self):
        self.assertEqual(APIClient().get("/api/reports/historical/").status_code, status.HTTP_403_FORBIDDEN)
        self.client.force_authenticate(self.user)
        RolePermission.objects.filter(role=self.role, module__in=("orders", "purchases")).update(can_view=False)
        self.assertEqual(self.client.get("/api/reports/historical/").status_code, status.HTTP_403_FORBIDDEN)

    def test_history_analysis_does_not_require_general_reports_permission(self):
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.get("/api/reports/historical/").status_code, status.HTTP_200_OK)
