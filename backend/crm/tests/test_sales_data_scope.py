import csv
import io
from datetime import date
from decimal import Decimal
from importlib import import_module

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from crm.models import (
    AccessRole, Contact, Customer, EmployeeProfile, FollowUp, Order, OrderItem,
    OrganizationUnit, Position, Product, Quote, RolePermission, SKU, Shipment,
    Supplier, SupplierSKU,
)
from crm.sales_scope import (
    allowed_employee_ids,
    allowed_unit_ids,
    effective_data_scope,
    scope_customer_queryset,
)

bind_unambiguous_legacy_owners = import_module(
    "crm.migrations.0076_customer_owner_profile"
).bind_unambiguous_legacy_owners


RBAC_SETTINGS = {
    "APP_STAGE": "production", "DEBUG": False,
    "DEVELOPMENT_SUPERADMIN": False, "RBAC_ENFORCEMENT": True,
}
MODULES = ("customers", "contacts", "followups", "quotes", "orders", "dashboard", "reports", "imports", "products", "skus", "suppliers", "inventory")


@override_settings(**RBAC_SETTINGS)
class SalesDataScopeTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.company = OrganizationUnit.objects.create(name="公司", code="SCOPE-ROOT", type="company")
        self.sales = OrganizationUnit.objects.create(name="销售部", code="SCOPE-SALES", parent=self.company)
        self.team = OrganizationUnit.objects.create(name="华东组", code="SCOPE-TEAM", type="team", parent=self.sales)
        self.other_unit = OrganizationUnit.objects.create(name="采购部", code="SCOPE-OTHER", parent=self.company)
        self.positions = {
            unit.pk: Position.objects.create(unit=unit, name="销售", code=f"SCOPE-P-{unit.pk}")
            for unit in (self.sales, self.team, self.other_unit)
        }
        self.roles = {
            scope: AccessRole.objects.create(name=scope, code=f"scope-{scope}", default_data_scope=scope)
            for scope in ("self", "department", "department_tree", "all")
        }
        for role in self.roles.values():
            for module in MODULES:
                RolePermission.objects.create(
                    role=role, module=module, can_view=True, can_create=True,
                    can_update=True, can_delete=True, can_export=True, can_import=True,
                )
        self.employee_a = self.make_employee("scope-a", self.sales, [self.roles["self"]])
        self.employee_b = self.make_employee("scope-b", self.sales, [self.roles["self"]])
        self.employee_team = self.make_employee("scope-team", self.team, [self.roles["self"]])
        self.employee_c = self.make_employee("scope-c", self.other_unit, [self.roles["self"]])
        self.manager = self.make_employee("scope-manager", self.sales, [self.roles["department"]])
        self.tree_manager = self.make_employee("scope-tree", self.sales, [self.roles["department_tree"]])
        self.all_user = self.make_employee("scope-all", self.sales, [self.roles["all"]])
        self.customer_a = Customer.objects.create(code="SCOPE-CA", name="客户 A", owner="销售 A", owner_profile=self.employee_a)
        self.customer_b = Customer.objects.create(code="SCOPE-CB", name="客户 B", owner="销售 B", owner_profile=self.employee_b)
        self.customer_team = Customer.objects.create(code="SCOPE-CT", name="团队客户", owner_profile=self.employee_team)
        self.customer_c = Customer.objects.create(code="SCOPE-CC", name="客户 C", owner_profile=self.employee_c)
        self.customer_unassigned = Customer.objects.create(code="SCOPE-CN", name="未归属客户", owner="旧负责人")

    def make_employee(self, username, unit, roles, override="inherit"):
        user = get_user_model().objects.create_user(username=username, password="temporary-test-password")
        profile = EmployeeProfile.objects.create(
            user=user, display_name=username, unit=unit, position=self.positions[unit.pk],
            data_scope_override=override,
        )
        profile.roles.set(roles)
        return profile

    def login(self, profile):
        self.client.force_authenticate(user=profile.user)

    def scoped_ids(self, profile):
        self.login(profile)
        return {row["id"] for row in self.client.get("/api/customers/").data["results"]}

    def make_quote(self, customer, quote_no):
        return Quote.objects.create(quote_no=quote_no, customer=customer, quote_date=date(2026, 10, 1))

    def make_order(self, customer, order_no, quote=None, status="confirmed"):
        product = Product.objects.create(code=f"P-{order_no}", name=f"产品 {order_no}")
        sku = SKU.objects.create(product=product, sku=f"SKU-{order_no}")
        order = Order.objects.create(
            order_no=order_no, customer=customer, quote=quote, order_date=date.today(),
            status=status, exchange_rate=Decimal("1"),
        )
        OrderItem.objects.create(order=order, sku=sku, quantity=1, unit_price=100, cost_price=20)
        return order, sku

    def make_supplier_source(self, sku, code):
        supplier = Supplier.objects.create(name=f"Supplier {code}", code=code)
        return SupplierSKU.objects.create(
            supplier=supplier, sku=sku, supplier_sku_code=f"{code}-SKU",
            purchase_price=Decimal("3.20"), currency="USD",
        )

    def test_effective_scope_uses_widest_active_role_and_override(self):
        extra = self.make_employee("scope-multi", self.sales, [self.roles["self"], self.roles["department"]])
        self.assertEqual(effective_data_scope(extra.user), "department")
        extra.roles.add(self.roles["all"])
        self.assertEqual(effective_data_scope(extra.user), "all")
        extra.data_scope_override = "self"
        extra.save(update_fields=["data_scope_override", "updated_at"])
        self.assertEqual(effective_data_scope(extra.user), "self")
        self.assertEqual(effective_data_scope(get_user_model().objects.create_user("no-profile")), "none")

    def test_self_department_tree_and_all_customer_lists(self):
        self.assertEqual(self.scoped_ids(self.employee_a), {self.customer_a.id})
        self.assertEqual(self.scoped_ids(self.manager), {self.customer_a.id, self.customer_b.id})
        self.assertEqual(self.scoped_ids(self.tree_manager), {self.customer_a.id, self.customer_b.id, self.customer_team.id})
        self.assertEqual(
            self.scoped_ids(self.all_user),
            {self.customer_a.id, self.customer_b.id, self.customer_team.id, self.customer_c.id, self.customer_unassigned.id},
        )
        self.assertEqual(set(allowed_unit_ids(self.tree_manager.user)), {self.sales.id, self.team.id})
        self.assertEqual(set(allowed_employee_ids(self.manager.user)), {
            self.employee_a.id, self.employee_b.id, self.manager.id, self.tree_manager.id, self.all_user.id,
        })

    def test_related_lists_details_and_context_inherit_customer_scope(self):
        contact = Contact.objects.create(customer=self.customer_c, name="客户 C 联系人")
        follow_up = FollowUp.objects.create(customer=self.customer_c, followed_at=timezone.now(), content="C 客户沟通")
        quote = self.make_quote(self.customer_c, "SCOPE-Q-C")
        order, _sku = self.make_order(self.customer_c, "SCOPE-O-C", quote)
        shipment = Shipment.objects.create(shipment_no="SCOPE-SHIP-C", order=order, shipment_date=date.today())
        self.login(self.employee_a)
        for path in ("/api/contacts/", "/api/follow-ups/", "/api/quotes/", "/api/orders/"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data["results"], [])
        for path in (
            f"/api/contacts/{contact.pk}/", f"/api/follow-ups/{follow_up.pk}/",
            f"/api/quotes/{quote.pk}/", f"/api/orders/{order.pk}/",
            f"/api/quotes/{quote.pk}/export/", f"/api/quotes/{quote.pk}/order-draft/",
            f"/api/orders/{order.pk}/packing-plan/", f"/api/orders/{order.pk}/procurement-plan/",
            f"/api/shipments/{shipment.pk}/",
            f"/api/context/customers/{self.customer_c.pk}/", f"/api/context/contacts/{contact.pk}/",
            f"/api/context/follow-ups/{follow_up.pk}/", f"/api/context/quotes/{quote.pk}/",
            f"/api/context/orders/{order.pk}/",
        ):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 404)
        post_cases = [
            (f"/api/quotes/{quote.pk}/revise/", {"revision_summary": "越权修订"}),
            (f"/api/quotes/{quote.pk}/mark-sent/", {}),
            (f"/api/quotes/{quote.pk}/accept/", {}),
            (f"/api/quotes/{quote.pk}/reject/", {}),
            (f"/api/orders/{order.pk}/confirm/", {}),
            (f"/api/orders/{order.pk}/start-production/", {}),
            (f"/api/orders/{order.pk}/complete/", {}),
            (f"/api/orders/{order.pk}/cancel/", {"reason": "越权取消"}),
            (f"/api/orders/{order.pk}/ship/", {"shipment_date": date.today().isoformat(), "items": [{"order_item": order.items.first().pk, "quantity": "1"}]}),
            (f"/api/orders/{order.pk}/packing-plan/", {}),
            (f"/api/shipments/{shipment.pk}/reverse/", {"reason": "越权冲销"}),
        ]
        for path, body in post_cases:
            with self.subTest(path=path):
                self.assertEqual(self.client.post(path, body, format="json").status_code, 404)

    def test_updates_and_quote_revisions_cannot_move_business_across_scope(self):
        quote = self.make_quote(self.customer_a, "SCOPE-Q-A-UPDATE")
        contact = Contact.objects.create(customer=self.customer_a, name="客户 A 联系人")
        follow_up = FollowUp.objects.create(customer=self.customer_a, followed_at=timezone.now(), type="call", content="A 客户沟通")
        order, sku = self.make_order(self.customer_a, "SCOPE-O-A-UPDATE", quote, status="draft")
        self.login(self.employee_a)

        self.assertEqual(self.client.patch(f"/api/contacts/{contact.pk}/", {"customer": self.customer_c.pk}, format="json").status_code, 403)
        self.assertEqual(self.client.patch(f"/api/follow-ups/{follow_up.pk}/", {"customer": self.customer_c.pk}, format="json").status_code, 403)
        self.assertEqual(self.client.patch(f"/api/orders/{order.pk}/", {"customer": self.customer_c.pk}, format="json").status_code, 403)
        revision = self.client.post(f"/api/quotes/{quote.pk}/revise/", {
            "revision_summary": "更换客户", "customer": self.customer_c.pk,
        }, format="json")
        self.assertEqual(revision.status_code, 403, revision.data)
        order.refresh_from_db(); contact.refresh_from_db(); follow_up.refresh_from_db()
        self.assertEqual(order.customer_id, self.customer_a.id)
        self.assertEqual(contact.customer_id, self.customer_a.id)
        self.assertEqual(follow_up.customer_id, self.customer_a.id)
        self.assertFalse(Quote.objects.filter(parent_quote=quote).exists())

    def test_create_and_update_associations_reject_out_of_scope_customers(self):
        self.login(self.employee_a)
        self.assertEqual(self.client.post("/api/contacts/", {"customer": self.customer_c.pk, "name": "越权联系人"}, format="json").status_code, 403)
        self.assertEqual(self.client.post("/api/follow-ups/", {
            "customer": self.customer_c.pk, "followed_at": timezone.now().isoformat(), "type": "call", "content": "越权跟进",
        }, format="json").status_code, 403)
        quote_response = self.client.post("/api/quotes/", {
            "customer": self.customer_c.pk, "quote_date": "2026-10-01", "items": [],
        }, format="json")
        self.assertEqual(quote_response.status_code, 403, quote_response.data)
        product = Product.objects.create(code="SCOPE-P-POST", name="测试产品")
        sku = SKU.objects.create(product=product, sku="SCOPE-S-POST")
        self.assertEqual(self.client.post("/api/orders/", {
            "customer": self.customer_c.pk, "order_date": "2026-10-01",
            "items": [{"sku": sku.pk, "quantity": "1", "unit_price": "1", "cost_price": "0"}],
        }, format="json").status_code, 403)
        self.assertFalse(Contact.objects.filter(name="越权联系人").exists())
        self.assertFalse(FollowUp.objects.filter(content="越权跟进").exists())
        self.assertFalse(Quote.objects.filter(customer=self.customer_c, quote_no__startswith="SJ").exists())

    def test_order_with_out_of_scope_source_quote_is_rejected(self):
        quote = self.make_quote(self.customer_c, "SCOPE-Q-SOURCE")
        product = Product.objects.create(code="SCOPE-P-SOURCE", name="测试产品")
        sku = SKU.objects.create(product=product, sku="SCOPE-S-SOURCE")
        self.login(self.employee_a)
        response = self.client.post("/api/orders/", {
            "customer": self.customer_a.pk, "quote": quote.pk, "order_date": "2026-10-01",
            "items": [{"sku": sku.pk, "quantity": "1", "unit_price": "1", "cost_price": "0"}],
        }, format="json")
        self.assertEqual(response.status_code, 403, response.data)
        self.assertFalse(Order.objects.filter(quote=quote).exists())

    def test_supplier_allocation_denies_other_employee_get_and_post_without_disclosure(self):
        order, sku = self.make_order(self.customer_b, "SCOPE-O-B-ALLOC")
        item = order.items.get()
        source = self.make_supplier_source(sku, "SCOPE-ALLOC-B")
        url = f"/api/orders/{order.pk}/items/{item.pk}/supplier-allocation/"
        self.login(self.employee_a)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
        self.assertNotIn(order.order_no, response.content.decode())
        self.assertNotIn(sku.sku, response.content.decode())
        self.assertNotIn(source.supplier.name, response.content.decode())

        response = self.client.post(url, {"supplier_sku": source.pk}, format="json")
        self.assertEqual(response.status_code, 404)
        self.assertNotIn(order.order_no, response.content.decode())
        item.refresh_from_db()
        self.assertIsNone(item.supplier_sku_id)
        self.assertEqual(item.supplier_name_snapshot, "")

    def test_supplier_allocation_allows_own_and_department_orders(self):
        own_order, own_sku = self.make_order(self.customer_a, "SCOPE-O-A-ALLOC")
        own_item = own_order.items.get()
        own_source = self.make_supplier_source(own_sku, "SCOPE-ALLOC-A")
        own_url = f"/api/orders/{own_order.pk}/items/{own_item.pk}/supplier-allocation/"

        self.login(self.employee_a)
        self.assertEqual(self.client.get(own_url).status_code, 200)
        response = self.client.post(own_url, {"supplier_sku": own_source.pk}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        own_item.refresh_from_db()
        self.assertEqual(own_item.supplier_sku_id, own_source.pk)

        peer_order, peer_sku = self.make_order(self.customer_b, "SCOPE-O-B-MANAGER-ALLOC")
        peer_item = peer_order.items.get()
        peer_source = self.make_supplier_source(peer_sku, "SCOPE-ALLOC-M")
        peer_url = f"/api/orders/{peer_order.pk}/items/{peer_item.pk}/supplier-allocation/"
        self.login(self.manager)
        self.assertEqual(self.client.get(peer_url).status_code, 200)
        response = self.client.post(peer_url, {"supplier_sku": peer_source.pk}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        peer_item.refresh_from_db()
        self.assertEqual(peer_item.supplier_sku_id, peer_source.pk)

    def test_product_customer_action_respects_sales_data_scope(self):
        product = Product.objects.create(code="SCOPE-P-CUSTOMERS", name="客户范围产品")
        sku = SKU.objects.create(product=product, sku="SCOPE-S-CUSTOMERS")
        for customer, order_no in ((self.customer_a, "SCOPE-O-CUSTOMER-A"), (self.customer_b, "SCOPE-O-CUSTOMER-B")):
            order = Order.objects.create(order_no=order_no, customer=customer, order_date=date.today(), status="confirmed", exchange_rate=1)
            OrderItem.objects.create(order=order, sku=sku, quantity=1, unit_price=100)

        self.login(self.employee_a)
        response = self.client.get(f"/api/products/{product.pk}/customers/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["order__customer__id"] for row in response.data], [self.customer_a.pk])

        self.login(self.manager)
        response = self.client.get(f"/api/products/{product.pk}/customers/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual({row["order__customer__id"] for row in response.data}, {self.customer_a.pk, self.customer_b.pk})

    def test_dashboard_active_customer_count_respects_sales_data_scope(self):
        Customer.objects.filter(pk__in=[self.customer_a.pk, self.customer_b.pk, self.customer_c.pk]).update(status="customer")

        self.login(self.employee_a)
        response = self.client.get("/api/dashboard/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["summary"]["active_customers"], 1)

        self.login(self.manager)
        response = self.client.get("/api/dashboard/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["summary"]["active_customers"], 2)

    def test_owner_options_and_customer_owner_updates_follow_scope(self):
        self.login(self.employee_a)
        owner_options = self.client.get("/api/customers/owner-options/")
        self.assertEqual([row["id"] for row in owner_options.data], [self.employee_a.id])
        response = self.client.patch(f"/api/customers/{self.customer_a.pk}/", {"owner_profile": self.employee_b.pk}, format="json")
        self.assertEqual(response.status_code, 403)
        self.customer_a.refresh_from_db()
        self.assertEqual(self.customer_a.owner_profile_id, self.employee_a.id)

        self.login(self.manager)
        manager_options = self.client.get("/api/customers/owner-options/")
        self.assertEqual({row["id"] for row in manager_options.data}, {
            self.employee_a.id, self.employee_b.id, self.manager.id, self.tree_manager.id, self.all_user.id,
        })
        allowed = self.client.patch(f"/api/customers/{self.customer_a.pk}/", {"owner_profile": self.employee_b.pk}, format="json")
        self.assertEqual(allowed.status_code, 200, allowed.data)
        self.assertEqual(allowed.data["owner"], self.employee_b.display_name)
        self.assertEqual(self.client.patch(f"/api/customers/{self.customer_a.pk}/", {"owner_profile": self.employee_c.pk}, format="json").status_code, 403)

        self.login(self.tree_manager)
        child_assignment = self.client.patch(
            f"/api/customers/{self.customer_a.pk}/", {"owner_profile": self.employee_team.pk}, format="json",
        )
        self.assertEqual(child_assignment.status_code, 200, child_assignment.data)
        self.assertEqual(child_assignment.data["owner_profile"], self.employee_team.pk)

        self.login(self.all_user)
        global_assignment = self.client.patch(
            f"/api/customers/{self.customer_c.pk}/", {"owner_profile": self.employee_a.pk}, format="json",
        )
        self.assertEqual(global_assignment.status_code, 200, global_assignment.data)
        self.assertEqual(global_assignment.data["owner_profile"], self.employee_a.pk)

    def test_new_customer_defaults_to_current_employee(self):
        self.login(self.employee_a)
        response = self.client.post("/api/customers/", {
            "name": "新客户默认负责人", "contacts": [{"name": "联系人", "is_primary": True}],
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        created = Customer.objects.get(pk=response.data["id"])
        self.assertEqual(created.owner_profile_id, self.employee_a.id)
        self.assertEqual(created.owner, self.employee_a.display_name)

    def test_dashboard_and_sales_reports_use_the_same_customer_scope(self):
        self.make_order(self.customer_a, "SCOPE-O-A")
        self.make_order(self.customer_b, "SCOPE-O-B")
        self.make_order(self.customer_c, "SCOPE-O-C-SALES")
        self.login(self.employee_a)
        dashboard = self.client.get("/api/dashboard/")
        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(dashboard.data["summary"]["orders_ytd"], 1)
        self.assertEqual([row["customer_name"] for row in dashboard.data["recent_orders"]], ["客户 A"])
        report = self.client.get("/api/reports/data/", {
            "source": "sales", "group_by": "customer", "date_from": date.today().replace(day=1).isoformat(),
            "date_to": date.today().isoformat(),
        })
        self.assertEqual(report.status_code, 200, report.data)
        self.assertEqual([row["label"] for row in report.data["rows"]], ["客户 A"])
        exported = self.client.get("/api/reports/data/?source=sales&group_by=customer&export=csv&date_from=" + date.today().replace(day=1).isoformat() + "&date_to=" + date.today().isoformat())
        self.assertEqual(exported.status_code, 200)
        self.assertNotIn("客户 C", exported.content.decode("utf-8-sig"))

        self.login(self.manager)
        department_dashboard = self.client.get("/api/dashboard/")
        self.assertEqual(department_dashboard.data["summary"]["orders_ytd"], 2)
        self.assertEqual({row["customer_name"] for row in department_dashboard.data["recent_orders"]}, {"客户 A", "客户 B"})
        department_report = self.client.get("/api/reports/data/", {
            "source": "sales", "group_by": "customer", "date_from": date.today().replace(day=1).isoformat(),
            "date_to": date.today().isoformat(),
        })
        self.assertEqual({row["label"] for row in department_report.data["rows"]}, {"客户 A", "客户 B"})

        self.login(self.all_user)
        global_dashboard = self.client.get("/api/dashboard/")
        self.assertEqual(global_dashboard.data["summary"]["orders_ytd"], 3)
        self.assertEqual({row["customer_name"] for row in global_dashboard.data["recent_orders"]}, {"客户 A", "客户 B", "客户 C"})
        global_report = self.client.get("/api/reports/data/", {
            "source": "sales", "group_by": "customer", "date_from": date.today().replace(day=1).isoformat(),
            "date_to": date.today().isoformat(),
        })
        self.assertEqual({row["label"] for row in global_report.data["rows"]}, {"客户 A", "客户 B", "客户 C"})

    def test_shared_product_and_sku_contexts_only_include_scoped_sales(self):
        order, sku = self.make_order(self.customer_c, "SCOPE-O-CONTEXT")
        self.login(self.employee_a)
        product_context = self.client.get(f"/api/context/products/{sku.product_id}/")
        self.assertEqual(product_context.status_code, 200)
        sales = next(section for section in product_context.data["sections"] if section["key"] == "sales")
        self.assertEqual(sales["rows"], [])
        self.assertNotEqual(product_context.data["entity"], "customers")
        sku_context = self.client.get(f"/api/context/skus/{sku.pk}/")
        self.assertEqual(sku_context.status_code, 200)
        orders = next(section for section in sku_context.data["sections"] if section["key"] == "orders")
        self.assertEqual(orders["rows"], [])

    def test_customer_import_rejects_out_of_scope_code_and_defaults_new_owner(self):
        self.login(self.employee_a)
        output = io.StringIO(newline="")
        writer = csv.writer(output)
        writer.writerow(["code", "name"])
        writer.writerow([self.customer_c.code, "不应覆盖"])
        content = output.getvalue().encode("utf-8")
        preview = self.client.post("/api/import/csv/preview/", {
            "entity": "customers", "file": SimpleUploadedFile("out-of-scope.csv", content),
        }, format="multipart")
        self.assertEqual(preview.status_code, 200)
        self.assertIn("该客户不在当前账号的数据范围内。", preview.data["errors"][0]["message"])
        self.assertNotIn("preview_token", preview.data)
        self.customer_c.refresh_from_db()
        self.assertEqual(self.customer_c.name, "客户 C")

        output = io.StringIO(newline="")
        writer = csv.writer(output)
        writer.writerow(["code", "name"])
        writer.writerow(["SCOPE-IMPORT-NEW", "导入新客户"])
        content = output.getvalue().encode("utf-8")
        preview = self.client.post("/api/import/csv/preview/", {
            "entity": "customers", "file": SimpleUploadedFile("new-customer.csv", content),
        }, format="multipart")
        self.assertEqual(preview.data["errors"], [])
        result = self.client.post("/api/import/csv/execute/", {
            "entity": "customers", "preview_token": preview.data["preview_token"],
            "file": SimpleUploadedFile("new-customer.csv", content),
        }, format="multipart")
        self.assertEqual(result.status_code, 200, result.data)
        self.assertEqual(Customer.objects.get(code="SCOPE-IMPORT-NEW").owner_profile_id, self.employee_a.id)

    def test_current_operator_exposes_server_computed_scope(self):
        self.login(self.manager)
        response = self.client.get("/api/session/current-operator/")
        self.assertEqual(response.data["data_scope"], "department")
        self.assertEqual(response.data["data_scope_display"], "本部门")
        self.assertEqual(response.data["employee_profile_id"], self.manager.pk)
        self.assertEqual(response.data["unit_id"], self.sales.pk)
        self.assertEqual(response.data["unit_name"], self.sales.name)


@override_settings(**RBAC_SETTINGS)
class LegacyCustomerOwnerMigrationTests(TestCase):
    def test_only_unique_legacy_owner_matches_are_bound(self):
        root = OrganizationUnit.objects.create(name="迁移公司", code="MIG-SCOPE-ROOT")
        unit = OrganizationUnit.objects.create(name="迁移销售", code="MIG-SCOPE-UNIT", parent=root)
        position = Position.objects.create(unit=unit, name="销售", code="MIG-SCOPE-POS")
        user_a = get_user_model().objects.create_user(username="legacy-a")
        profile_a = EmployeeProfile.objects.create(user=user_a, display_name="历史负责人", unit=unit, position=position)
        user_b = get_user_model().objects.create_user(username="legacy-b")
        EmployeeProfile.objects.create(user=user_b, display_name="历史负责人", unit=unit, position=position)
        unique = Customer.objects.create(code="MIG-UNIQUE", name="唯一匹配", owner="legacy-a")
        ambiguous = Customer.objects.create(code="MIG-AMBIGUOUS", name="姓名重复", owner="历史负责人")
        unknown = Customer.objects.create(code="MIG-UNKNOWN", name="无法匹配", owner="未知姓名")

        bind_unambiguous_legacy_owners(apps, None)

        unique.refresh_from_db(); ambiguous.refresh_from_db(); unknown.refresh_from_db()
        self.assertEqual(unique.owner_profile_id, profile_a.pk)
        self.assertIsNone(ambiguous.owner_profile_id)
        self.assertIsNone(unknown.owner_profile_id)

    def test_unmatched_legacy_owner_is_hidden_from_sales_but_visible_to_all_scope(self):
        root = OrganizationUnit.objects.create(name="范围公司", code="MIG-SCOPE-ROOT-2")
        unit = OrganizationUnit.objects.create(name="范围销售", code="MIG-SCOPE-UNIT-2", parent=root)
        position = Position.objects.create(unit=unit, name="销售", code="MIG-SCOPE-POS-2")
        self_role = AccessRole.objects.create(name="范围本人", code="mig-scope-self", default_data_scope="self")
        all_role = AccessRole.objects.create(name="范围全部", code="mig-scope-all", default_data_scope="all")
        self_profile = EmployeeProfile.objects.create(
            user=get_user_model().objects.create_user(username="mig-scope-self"),
            display_name="本人销售", unit=unit, position=position,
        )
        self_profile.roles.add(self_role)
        all_profile = EmployeeProfile.objects.create(
            user=get_user_model().objects.create_user(username="mig-scope-all"),
            display_name="全量销售", unit=unit, position=position,
        )
        all_profile.roles.add(all_role)
        unassigned = Customer.objects.create(code="MIG-UNASSIGNED", name="未匹配历史客户", owner="无法唯一匹配")

        self.assertFalse(scope_customer_queryset(Customer.objects.all(), self_profile.user).filter(pk=unassigned.pk).exists())
        self.assertTrue(scope_customer_queryset(Customer.objects.all(), all_profile.user).filter(pk=unassigned.pk).exists())

