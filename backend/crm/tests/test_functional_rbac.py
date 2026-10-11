from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from crm.models import AccessRole, Customer, EmployeeProfile, OrganizationUnit, Position, Product, RolePermission, SKU
from crm.permissions import effective_permission_matrix


RBAC_SETTINGS = {
    "APP_STAGE": "production",
    "DEBUG": False,
    "DEVELOPMENT_SUPERADMIN": False,
    "RBAC_ENFORCEMENT": True,
}


@override_settings(**RBAC_SETTINGS)
class FunctionalRBACApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.unit = OrganizationUnit.objects.create(name="UAT", code="RBAC-UAT")
        self.position = Position.objects.create(unit=self.unit, name="测试", code="RBAC-UAT-STAFF")
        self.customer = Customer.objects.create(name="RBAC Customer", code="RBAC-C1")
        self.role = AccessRole.objects.create(name="只读角色", code="rbac-readonly")

    def make_user(self, username="rbac-user", roles=None, active=True, superuser=False):
        User = get_user_model()
        user = User.objects.create_user(username=username, password="test-password", is_superuser=superuser, is_staff=superuser)
        if not superuser:
            profile = EmployeeProfile.objects.create(user=user, display_name=username, unit=self.unit, position=self.position, active=active)
            if roles:
                profile.roles.set(roles)
        return user

    def grant(self, role, module, **values):
        defaults = {"can_view": False, "can_create": False, "can_update": False, "can_delete": False, "can_export": False, "can_import": False}
        defaults.update(values)
        return RolePermission.objects.update_or_create(role=role, module=module, defaults=defaults)[0]

    def auth(self, user):
        self.client.force_authenticate(user=user)

    def test_anonymous_business_api_is_denied(self):
        self.assertEqual(self.client.get("/api/customers/").status_code, 403)

    @override_settings(APP_STAGE="production", DEBUG=False, DEVELOPMENT_SUPERADMIN=False, RBAC_ENFORCEMENT=False)
    def test_unconfigured_non_development_environment_does_not_trust_anonymous(self):
        anonymous = APIClient()
        self.assertEqual(anonymous.get("/api/customers/").status_code, 403)
        operator = anonymous.get("/api/session/current-operator/")
        self.assertFalse(operator.data["has_all_permissions"])
        self.assertFalse(operator.data["permissions"]["customers"]["view"])

    def test_view_permission_does_not_grant_create(self):
        self.grant(self.role, "customers", can_view=True)
        self.auth(self.make_user(roles=[self.role]))
        self.assertEqual(self.client.get("/api/customers/").status_code, 200)
        self.assertEqual(self.client.post("/api/customers/", {}).status_code, 403)

    def test_new_role_permission_rows_default_to_no_access(self):
        row = RolePermission.objects.create(role=self.role, module="customers")
        self.assertFalse(row.can_view)
        self.assertFalse(row.can_create)
        self.assertFalse(row.can_update)
        self.assertFalse(row.can_delete)
        self.assertFalse(row.can_export)
        self.assertFalse(row.can_import)

    def test_update_and_delete_are_checked_separately(self):
        self.grant(self.role, "customers", can_view=True, can_create=True)
        self.auth(self.make_user(roles=[self.role]))
        self.assertEqual(self.client.patch(f"/api/customers/{self.customer.pk}/", {"name": "Changed"}, format="json").status_code, 403)
        self.assertEqual(self.client.delete(f"/api/customers/{self.customer.pk}/").status_code, 403)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.name, "RBAC Customer")

    def test_quote_export_and_import_actions_use_special_permissions(self):
        self.grant(self.role, "quotes", can_view=True, can_update=True, can_export=False)
        self.grant(self.role, "imports", can_view=True, can_import=False)
        self.auth(self.make_user(roles=[self.role]))
        self.assertEqual(self.client.get("/api/quotes/999/export/").status_code, 403)
        self.assertEqual(self.client.post("/api/import/csv/preview/").status_code, 403)
        self.assertEqual(self.client.post("/api/import/csv/execute/").status_code, 403)

    def test_report_csv_export_requires_export_permission(self):
        self.grant(self.role, "reports", can_view=True, can_export=False)
        self.auth(self.make_user(roles=[self.role]))
        self.assertEqual(self.client.get("/api/reports/data/?source=sales").status_code, 200)
        self.assertEqual(self.client.get("/api/reports/data/?source=sales&export=csv").status_code, 403)

    def test_permissions_are_union_of_active_roles(self):
        second = AccessRole.objects.create(name="创建角色", code="rbac-create")
        self.grant(self.role, "customers", can_view=True)
        self.grant(second, "customers", can_create=True)
        user = self.make_user(roles=[self.role, second])
        permissions = effective_permission_matrix(user)
        self.assertTrue(permissions["customers"]["view"])
        self.assertTrue(permissions["customers"]["create"])
        self.assertFalse(permissions["customers"]["delete"])

    def test_inactive_employee_profile_gets_no_business_access(self):
        self.grant(self.role, "customers", can_view=True, can_create=True, can_update=True, can_delete=True)
        user = self.make_user(roles=[self.role], active=False)
        self.auth(user)
        self.assertEqual(self.client.get("/api/customers/").status_code, 403)
        self.assertFalse(effective_permission_matrix(user)["customers"]["view"])

    def test_superadmin_effectively_gets_every_module_and_action(self):
        superadmin = AccessRole.objects.get(code="superadmin")
        user = self.make_user(roles=[superadmin])
        matrix = effective_permission_matrix(user)
        self.assertEqual(len(matrix), len(RolePermission.MODULE_CHOICES))
        self.assertTrue(all(all(actions.values()) for actions in matrix.values()))

    def test_context_endpoint_cannot_bypass_primary_module_view_permission(self):
        self.auth(self.make_user(roles=[self.role]))
        self.assertEqual(self.client.get(f"/api/context/customers/{self.customer.pk}/").status_code, 403)

    def test_context_hides_related_sections_without_their_module_view_permission(self):
        self.grant(self.role, "customers", can_view=True)
        self.auth(self.make_user(roles=[self.role]))
        response = self.client.get(f"/api/context/customers/{self.customer.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["sections"], [])

    def test_purchase_finance_and_sku_apis_are_module_checked(self):
        self.grant(self.role, "customers", can_view=True)
        self.auth(self.make_user(roles=[self.role]))
        for path in ("/api/purchase-orders/", "/api/payment-plans/", "/api/skus/"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 403)

    def test_inventory_workbench_apis_use_inventory_permission_and_minimal_sku_data(self):
        product = Product.objects.create(code="RBAC-P1", name="RBAC Product")
        sku = SKU.objects.create(product=product, sku="RBAC-S1", cost_price=Decimal("4.50"))
        self.grant(self.role, "inventory", can_view=True)
        self.auth(self.make_user(roles=[self.role]))

        inventory_rows = self.client.get("/api/skus/inventory-list/")
        self.assertEqual(inventory_rows.status_code, 200, inventory_rows.data)
        row = inventory_rows.data["results"][0]
        self.assertEqual(row["id"], sku.id)
        self.assertNotIn("cost_price", row)
        self.assertEqual(self.client.get(f"/api/skus/{sku.pk}/inventory-detail/").status_code, 200)

    def test_permission_matrix_write_is_admin_only_and_admin_can_save(self):
        self.grant(self.role, "permissions", can_view=True, can_update=True)
        ordinary = self.make_user(username="rbac-ordinary", roles=[self.role])
        self.client.force_authenticate(user=ordinary)
        url = f"/api/access-roles/{self.role.pk}/permission-matrix/"
        body = {"permissions": [{"module": "customers", "can_view": True}]}
        self.assertEqual(self.client.post(url, body, format="json").status_code, 403)

        admin_role = AccessRole.objects.get(code="admin")
        admin = self.make_user(username="rbac-admin", roles=[admin_role])
        self.client.force_authenticate(user=admin)
        self.assertEqual(self.client.post(url, body, format="json").status_code, 200)

    def test_current_operator_returns_complete_matrix_contract(self):
        self.grant(self.role, "customers", can_view=True)
        self.auth(self.make_user(roles=[self.role]))
        response = self.client.get("/api/session/current-operator/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["rbac_enforcement"])
        self.assertFalse(response.data["has_all_permissions"])
        self.assertFalse(response.data["can_manage_permissions"])
        self.assertTrue(response.data["permissions"]["customers"]["view"])
        self.assertEqual(set(response.data["permissions"]["customers"]), {"view", "create", "update", "delete", "export", "import"})


@override_settings(APP_STAGE="development", DEBUG=True, DEVELOPMENT_SUPERADMIN=True, RBAC_ENFORCEMENT=False)
class DevelopmentAccessCompatibilityTests(TestCase):
    def test_rbac_disabled_preserves_legacy_development_access(self):
        self.assertEqual(APIClient().get("/api/customers/").status_code, 200)
        response = APIClient().get("/api/session/current-operator/")
        self.assertTrue(response.data["has_all_permissions"])
        self.assertTrue(response.data["permissions"]["customers"]["delete"])
