from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from crm.models import (
    AccessRole,
    Customer,
    EmployeeProfile,
    InventoryMovement,
    OperationLog,
    Order,
    PaymentPlan,
    Position,
    Product,
    PurchaseCostAllocation,
    PurchaseOrder,
    RolePermission,
    SKU,
    Supplier,
    Transaction,
    OrganizationUnit,
)
from crm.services.purchase_costs import order_purchase_cost


RBAC_SETTINGS = {
    "APP_STAGE": "production",
    "DEBUG": False,
    "DEVELOPMENT_SUPERADMIN": False,
    "RBAC_ENFORCEMENT": True,
    "AUDIT_LOG_ENABLED": True,
}


@override_settings(**RBAC_SETTINGS, PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class SharedPurchaseCostPermissionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.unit = OrganizationUnit.objects.create(name="ISS-039 测试部", code="ISS039")
        self.position = Position.objects.create(unit=self.unit, name="测试员工", code="ISS039-STAFF")
        self.procurement_role = self.make_role("iss039-procurement")
        self.view_only_role = self.make_role("iss039-view-only")
        self.scoped_view_role = self.make_role("iss039-scoped-view")
        self.sales_role = self.make_role("iss039-sales")
        self.grant(self.procurement_role, "purchases", can_view=True, can_update=True)
        self.grant(self.procurement_role, "skus", can_view=True)
        self.grant(self.procurement_role, "suppliers", can_view=True)
        self.grant(self.view_only_role, "purchases", can_view=True)
        self.grant(self.scoped_view_role, "purchases", can_view=True)
        self.grant(self.scoped_view_role, "orders", can_view=True)
        self.grant(self.sales_role, "orders", can_view=True, can_update=True)
        self.grant(self.sales_role, "customers", can_view=True)

        self.procurement = self.make_user("iss039-procurement", [self.procurement_role], is_staff=True)
        self.viewer = self.make_user("iss039-viewer", [self.view_only_role])
        self.scoped_viewer = self.make_user("iss039-scoped-viewer", [self.scoped_view_role])
        self.sales_a = self.make_user("iss039-sales-a", [self.sales_role])
        self.sales_b = self.make_user("iss039-sales-b", [self.sales_role])
        self.no_purchase_write = self.make_user("iss039-no-write", [self.view_only_role])

        self.customer_a = Customer.objects.create(code="ISS039-CA", name="ISS039 客户 A", owner_profile=self.scoped_viewer.employee_profile)
        self.customer_b = Customer.objects.create(code="ISS039-CB", name="ISS039 客户 B", owner_profile=self.sales_b.employee_profile)
        product = Product.objects.create(code="ISS039-P", name="ISS039 商品")
        self.sku = SKU.objects.create(product=product, sku="ISS039-SKU", unit="件")
        self.order_a = Order.objects.create(order_no="ISS039-SO-A", customer=self.customer_a, order_date=date(2026, 10, 20), status="confirmed", currency="CNY", exchange_rate=1)
        self.order_b = Order.objects.create(order_no="ISS039-SO-B", customer=self.customer_b, order_date=date(2026, 10, 20), status="confirmed", currency="CNY", exchange_rate=1)
        self.order_a.items.create(sku=self.sku, quantity=3, unit_price=4000)
        self.order_b.items.create(sku=self.sku, quantity=2, unit_price=5000)
        self.supplier = Supplier.objects.create(code="ISS039-S", name="ISS039 供应商")
        self.purchase = PurchaseOrder.objects.create(
            purchase_no="ISS039-PO",
            supplier=self.supplier,
            order=None,
            order_date=date(2026, 10, 20),
            status="ordered",
            currency="CNY",
            exchange_rate=1,
        )
        self.item = self.purchase.items.create(sku=self.sku, quantity=10, unit_price=1000)
        self.url = f"/api/purchase-orders/{self.purchase.pk}/cost-allocation/"

    def make_role(self, code):
        return AccessRole.objects.create(name=code, code=code)

    def grant(self, role, module, **values):
        defaults = {"can_view": False, "can_create": False, "can_update": False, "can_delete": False, "can_export": False, "can_import": False}
        defaults.update(values)
        return RolePermission.objects.update_or_create(role=role, module=module, defaults=defaults)[0]

    def make_user(self, username, roles, *, is_staff=False):
        user = get_user_model().objects.create_user(username=username, password="iss039-password", is_staff=is_staff)
        EmployeeProfile.objects.create(user=user, display_name=username, unit=self.unit, position=self.position).roles.set(roles)
        return user

    def payload(self, *, version=None, expense=True):
        return {
            "version": self.purchase.cost_allocation_version if version is None else version,
            "allocations": [
                {"purchase_item": self.item.pk, "target_type": "order", "order": self.order_a.pk, "quantity": "3"},
                {"purchase_item": self.item.pk, "target_type": "order", "order": self.order_b.pk, "quantity": "2"},
                {"purchase_item": self.item.pk, "target_type": "inventory", "order": None, "quantity": "5"},
            ],
            "expenses": [{"name": "公共运费", "amount": "1000", "method": "amount"}] if expense else [],
        }

    def login(self, user):
        self.client.force_authenticate(user=user)

    def test_procurement_can_allocate_cross_sales_orders_without_sales_module(self):
        self.login(self.procurement)
        self.assertEqual(self.client.get("/api/orders/").status_code, 403)
        self.assertEqual(self.client.patch(f"/api/orders/{self.order_b.pk}/", {"notes": "越权"}, format="json").status_code, 403)

        candidates = self.client.get("/api/purchase-orders/cost-allocation-orders/")
        self.assertEqual(candidates.status_code, 200, candidates.data)
        self.assertEqual({row["order_no"] for row in candidates.data}, {self.order_a.order_no, self.order_b.order_no})
        self.assertTrue(all(set(row) == {"id", "order_no", "status", "status_display"} for row in candidates.data))
        self.assertNotIn(self.customer_a.name, repr(candidates.data))
        self.assertNotIn(self.customer_b.name, repr(candidates.data))

        response = self.client.post(self.url, self.payload(), format="json")
        self.assertEqual(response.status_code, 200, response.data)
        rows = {row["order"]: row for row in response.data["allocations"]}
        self.assertEqual(Decimal(str(rows[self.order_a.pk]["base_amount"])), Decimal("3000"))
        self.assertEqual(Decimal(str(rows[self.order_b.pk]["base_amount"])), Decimal("2000"))
        self.assertEqual(Decimal(str(rows[None]["base_amount"])), Decimal("5000"))
        self.assertEqual(Decimal(str(rows[self.order_a.pk]["additional_amount"])), Decimal("300"))
        self.assertEqual(Decimal(str(rows[self.order_b.pk]["additional_amount"])), Decimal("200"))
        self.assertEqual(Decimal(str(rows[None]["additional_amount"])), Decimal("500"))
        self.assertEqual(Decimal(str(response.data["additional_amount"])), Decimal("1000"))
        self.assertEqual(order_purchase_cost(self.order_a), (Decimal("3000"), Decimal("300")))
        self.assertEqual(order_purchase_cost(self.order_b), (Decimal("2000"), Decimal("200")))
        self.assertEqual(sum(order_purchase_cost(self.order_a)), Decimal("3300"))
        self.assertEqual(sum(order_purchase_cost(self.order_b)), Decimal("2200"))
        self.assertNotIn(self.customer_a.name, repr(response.data))
        self.assertNotIn(self.customer_b.name, repr(response.data))

    def test_cost_allocation_orders_are_minimal_and_sales_apis_remain_scoped(self):
        self.login(self.procurement)
        response = self.client.get(f"/api/purchase-orders/{self.purchase.pk}/cost-allocation/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertFalse(response.data["allocations"][0].get("sales_link_restricted", False))
        self.assertNotIn("customer_name", repr(response.data))

        self.login(self.viewer)
        self.assertEqual(self.client.post(self.url, self.payload(), format="json").status_code, 403)
        self.login(self.no_purchase_write)
        self.assertEqual(self.client.post(self.url, self.payload(), format="json").status_code, 403)
        self.assertEqual(PurchaseCostAllocation.objects.filter(purchase_item=self.item).count(), 1)

    def test_cost_allocation_reads_respect_procurement_and_sales_visibility(self):
        self.login(self.procurement)
        seeded = self.client.post(self.url, self.payload(expense=False), format="json")
        self.assertEqual(seeded.status_code, 200, seeded.data)
        before = list(self.item.cost_allocations.values_list("target_type", "order_id", "quantity"))

        # A read-only purchasing user may open the summary, but neither the
        # target lookup nor historical cross-scope order identifiers are
        # available to them.
        self.login(self.viewer)
        candidates = self.client.get("/api/purchase-orders/cost-allocation-orders/")
        self.assertEqual(candidates.status_code, 403)
        summary = self.client.get(self.url)
        self.assertEqual(summary.status_code, 200, summary.data)
        restricted = [row for row in summary.data["allocations"] if row["target_type"] == "order"]
        self.assertTrue(restricted)
        self.assertTrue(all(row["order"] is None and row["order_no"] == "" for row in restricted))
        self.assertTrue(all(row["sales_link_restricted"] for row in restricted))
        self.assertIn("销售订单（详情受限）", repr(summary.data))
        self.assertEqual(list(self.item.cost_allocations.values_list("target_type", "order_id", "quantity")), before)

        # C can see its own sales order, but the other allocation remains an
        # explicit restricted placeholder.  This does not grant customer or
        # ordinary sales-order data access.
        self.login(self.scoped_viewer)
        orders = self.client.get("/api/orders/")
        self.assertEqual(orders.status_code, 200, orders.data)
        self.assertEqual({row["order_no"] for row in orders.data["results"]}, {self.order_a.order_no})
        self.assertNotIn(self.customer_b.name, repr(orders.data))
        summary = self.client.get(self.url)
        self.assertEqual(summary.status_code, 200, summary.data)
        by_amount = {str(row["base_amount"]): row for row in summary.data["allocations"] if row["target_type"] == "order"}
        self.assertEqual(by_amount["3000.00"]["order"], self.order_a.pk)
        self.assertEqual(by_amount["3000.00"]["order_no"], self.order_a.order_no)
        self.assertIsNone(by_amount["2000.00"]["order"])
        self.assertEqual(by_amount["2000.00"]["order_no"], "")
        self.assertTrue(by_amount["2000.00"]["sales_link_restricted"])
        self.assertNotIn(self.order_b.order_no, repr(summary.data))
        self.assertNotIn(self.customer_a.name, repr(summary.data))
        self.assertNotIn(self.customer_b.name, repr(summary.data))

        # D and anonymous callers do not get a read-only summary through the
        # purchasing endpoint at all.
        self.login(self.sales_a)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.client.force_authenticate(user=None)
        self.assertIn(self.client.get(self.url).status_code, {401, 403})
        self.assertIn(self.client.get("/api/purchase-orders/cost-allocation-orders/").status_code, {401, 403})

        # Revoking purchasing update permission immediately removes target
        # lookup access; it never changes the persisted allocation rows.
        self.login(self.procurement)
        RolePermission.objects.filter(role=self.procurement_role, module="purchases").update(can_update=False)
        self.assertEqual(self.client.get("/api/purchase-orders/cost-allocation-orders/").status_code, 403)
        summary = self.client.get(self.url)
        self.assertEqual(summary.status_code, 200, summary.data)
        self.assertFalse(summary.data["can_edit"])
        self.assertTrue(all(row["order"] is None for row in summary.data["allocations"] if row["target_type"] == "order"))
        self.assertEqual(list(self.item.cost_allocations.values_list("target_type", "order_id", "quantity")), before)

    def test_public_expense_and_attribution_are_atomic_and_do_not_create_other_records(self):
        self.login(self.procurement)
        before = {
            "movements": InventoryMovement.objects.count(),
            "transactions": Transaction.objects.count(),
            "plans": PaymentPlan.objects.count(),
        }
        response = self.client.post(self.url, self.payload(), format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            {key: model.objects.count() for key, model in {
                "movements": InventoryMovement,
                "transactions": Transaction,
                "plans": PaymentPlan,
            }.items()},
            before,
        )
        self.assertEqual(sum((Decimal(str(row["additional_amount"])) for row in response.data["allocations"]), Decimal("0")), Decimal("1000"))

        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.additional_costs, [{"name": "公共运费", "amount": "1000.00", "method": "amount"}])

    def test_cancelled_target_and_stale_version_leave_all_state_and_audit_unchanged(self):
        self.login(self.procurement)
        self.order_b.status = "cancelled"
        self.order_b.save(update_fields=["status", "updated_at"])
        before_version = self.purchase.cost_allocation_version
        before_allocations = list(self.item.cost_allocations.values_list("target_type", "order_id", "quantity"))
        response = self.client.post(self.url, self.payload(), format="json")
        self.assertEqual(response.status_code, 400, response.data)
        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.cost_allocation_version, before_version)
        self.assertEqual(list(self.item.cost_allocations.values_list("target_type", "order_id", "quantity")), before_allocations)
        self.assertFalse(OperationLog.objects.filter(entity="crm.purchaseorder", object_id=str(self.purchase.pk)).exists())

    def test_audit_contains_before_after_and_is_redacted_for_procurement_only_operator(self):
        self.login(self.procurement)
        response = self.client.post(self.url, self.payload(), format="json")
        self.assertEqual(response.status_code, 200, response.data)
        logs = OperationLog.objects.filter(entity="crm.purchaseorder", object_id=str(self.purchase.pk), action_label="采购成本分配")
        self.assertEqual(logs.count(), 1)
        log = logs.get()
        self.assertEqual(log.operator_id, self.procurement.id)
        self.assertEqual(log.before_data["cost_allocation"]["allocations"][0]["target_type"], "inventory")
        self.assertEqual(log.after_data["cost_allocation"]["expenses"][0]["amount"], "1000.00")
        self.assertEqual(log.changed_fields, ["cost_allocation"])
        self.assertEqual(log.metadata, {"purchase_no": self.purchase.purchase_no})

        audit = self.client.get(f"/api/operation-logs/?entity=crm.purchaseorder&object_id={self.purchase.pk}")
        self.assertEqual(audit.status_code, 200, audit.data)
        rendered = repr(audit.data)
        self.assertNotIn(self.order_a.order_no, rendered)
        self.assertNotIn(self.order_b.order_no, rendered)
        self.assertEqual(audit.data["results"][0]["before_data"], {})
        self.assertEqual(audit.data["results"][0]["after_data"], {})
        self.assertEqual(audit.data["results"][0]["metadata"], {})
