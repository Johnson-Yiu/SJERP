from decimal import Decimal
from datetime import date
import csv
import io
import tempfile
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.request import Request
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate

from crm.models import AccessRole, Customer, EmployeeProfile, FollowUp, FollowUpAttachment, HSCode, Order, OrderItem, OrganizationUnit, Position, Product, ProductCategory, ProductCertificate, ProductParameter, RolePermission, SKU, Supplier, SupplierCapability
from crm.permissions import ModuleActionPermission, action_for_request, effective_permission_matrix


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
        self.grant(self.role, "orders", can_view=True)
        self.auth(self.make_user(roles=[self.role]))
        self.assertEqual(self.client.get("/api/reports/data/?source=sales").status_code, 200)
        self.assertEqual(self.client.get("/api/reports/data/?source=sales&export=csv").status_code, 403)

    def test_get_export_query_uses_export_permission_before_safe_method_view(self):
        self.grant(self.role, "reports", can_view=True, can_export=False)
        user = self.make_user(roles=[self.role])
        raw = APIRequestFactory().get("/api/reports/data/?source=sales&export=csv")
        force_authenticate(raw, user=user)
        request = Request(raw)
        view = SimpleNamespace(action=None, permission_module=None, permission_public=False)
        self.assertEqual(action_for_request(request, view), "export")
        self.assertFalse(ModuleActionPermission().has_permission(request, view))

    def test_report_source_and_csv_share_module_scope_and_totals(self):
        self.grant(self.role, "reports", can_view=True, can_export=True)
        user = self.make_user(roles=[self.role])
        profile = EmployeeProfile.objects.get(user=user)
        self.grant(self.role, "customers", can_view=True)
        self.grant(self.role, "orders", can_view=True)
        self.customer.owner_profile = profile
        self.customer.save(update_fields=["owner_profile"])
        product = Product.objects.create(code="RBAC-RPT-P1", name="RBAC Report Product")
        sku = SKU.objects.create(product=product, sku="RBAC-RPT-S1")
        day = date.today()
        order = Order.objects.create(order_no="RBAC-RPT-O1", customer=self.customer, order_date=day, status="confirmed", currency="CNY", exchange_rate=1)
        OrderItem.objects.create(order=order, sku=sku, quantity=2, unit_price=Decimal("12.50"))
        self.auth(user)

        params = {"source": "sales", "group_by": "customer", "date_from": day.isoformat(), "date_to": day.isoformat()}
        report = self.client.get("/api/reports/data/", params)
        self.assertEqual(report.status_code, 200, report.data)
        self.assertEqual(Decimal(str(report.data["totals"]["amount"])), Decimal("25.00"))
        exported = self.client.get("/api/reports/data/", {**params, "export": "csv"})
        self.assertEqual(exported.status_code, 200)
        rows = list(csv.reader(io.StringIO(exported.content.decode("utf-8-sig"))))
        total_row = next(row for row in rows if row and row[0] == "合计（单据去重）")
        self.assertEqual(Decimal(total_row[1]), Decimal(str(report.data["totals"]["amount"])))

    def test_report_view_does_not_grant_sales_source_module_access(self):
        self.grant(self.role, "reports", can_view=True, can_export=True)
        self.auth(self.make_user(roles=[self.role]))
        self.assertEqual(self.client.get("/api/reports/data/?source=sales").status_code, 403)

    def test_report_dimension_requires_its_source_module_permission(self):
        self.grant(self.role, "reports", can_view=True, can_export=True)
        self.grant(self.role, "orders", can_view=True)
        self.auth(self.make_user(roles=[self.role]))
        params = {"source": "sales", "group_by": "customer", "date_from": date.today().isoformat(), "date_to": date.today().isoformat()}
        self.assertEqual(self.client.get("/api/reports/data/", params).status_code, 403)
        self.assertEqual(self.client.get("/api/reports/data/", {**params, "export": "csv"}).status_code, 403)

    def test_unmapped_authenticated_api_fails_closed_in_rbac_mode(self):
        user = self.make_user(roles=[self.role])
        raw = APIRequestFactory().get("/api/not-in-the-permission-matrix/")
        force_authenticate(raw, user=user)
        request = Request(raw)
        view = SimpleNamespace(action=None, permission_module=None, permission_public=False)
        self.assertFalse(ModuleActionPermission().has_permission(request, view))

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

    def test_order_response_masks_customer_and_sku_relations_without_module_permissions(self):
        user = self.make_user(roles=[self.role])
        profile = EmployeeProfile.objects.get(user=user)
        self.customer.owner_profile = profile
        self.customer.save(update_fields=["owner_profile"])
        product = Product.objects.create(code="RBAC-MASK-P1", name="Private product name")
        sku = SKU.objects.create(product=product, sku="RBAC-MASK-S1")
        order = Order.objects.create(order_no="RBAC-MASK-O1", customer=self.customer, order_date=date.today(), status="draft", currency="CNY", exchange_rate=1)
        OrderItem.objects.create(order=order, sku=sku, quantity=1, unit_price=10)
        self.grant(self.role, "orders", can_view=True)
        self.auth(user)

        response = self.client.get(f"/api/orders/{order.pk}/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIsNone(response.data["customer"])
        self.assertEqual(response.data["customer_name"], "")
        self.assertIsNone(response.data["items"][0]["sku"])
        self.assertEqual(response.data["items"][0]["sku_code"], "")
        self.assertNotIn("Private product name", repr(response.data))

    def test_customer_nested_contacts_require_contacts_create(self):
        self.grant(self.role, "customers", can_create=True)
        self.grant(self.role, "contacts", can_create=False)
        self.auth(self.make_user(roles=[self.role]))
        response = self.client.post("/api/customers/", {
            "name": "Nested contact boundary",
            "contacts": [{"name": "Should not be created", "is_primary": True}],
        }, format="json")
        self.assertEqual(response.status_code, 403, response.data)
        self.assertFalse(Customer.objects.filter(name="Nested contact boundary").exists())

    def test_media_url_requires_record_module_and_customer_scope(self):
        media_root = tempfile.TemporaryDirectory()
        self.addClassCleanup(media_root.cleanup)
        with override_settings(MEDIA_ROOT=media_root.name):
            owner = self.make_user(username="media-owner", roles=[self.role])
            profile = EmployeeProfile.objects.get(user=owner)
            self.customer.owner_profile = profile
            self.customer.save(update_fields=["owner_profile"])
            follow_up = FollowUp.objects.create(customer=self.customer, followed_at="2026-10-12T09:00:00Z", content="private attachment")
            attachment = FollowUpAttachment.objects.create(
                follow_up=follow_up,
                file=SimpleUploadedFile("private.txt", b"private bytes", content_type="text/plain"),
                name="private.txt", content_type="text/plain", size=13,
            )
            url = f"/api/media/{attachment.file.name}"
            self.grant(self.role, "followups", can_view=True)

            self.assertEqual(self.client.get(url).status_code, 403)
            self.auth(owner)
            allowed = self.client.get(url)
            self.assertEqual(allowed.status_code, 200)
            self.assertEqual(b"".join(allowed.streaming_content), b"private bytes")
            self.addClassCleanup(allowed.close)

            outsider = self.make_user(username="media-outsider", roles=[self.role])
            self.auth(outsider)
            self.assertEqual(self.client.get(url).status_code, 404)

            self.grant(self.role, "followups", can_view=False)
            self.auth(owner)
            self.assertEqual(self.client.get(url).status_code, 404)

    def test_context_hides_related_sections_without_their_module_view_permission(self):
        self.grant(self.role, "customers", can_view=True)
        user = self.make_user(roles=[self.role])
        profile = EmployeeProfile.objects.get(user=user)
        self.customer.owner_profile = profile
        self.customer.owner = profile.display_name
        self.customer.save(update_fields=["owner_profile", "owner"])
        self.auth(user)
        response = self.client.get(f"/api/context/customers/{self.customer.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["sections"], [])

    def test_context_redacts_cross_module_snapshots_and_product_classification(self):
        self.grant(self.role, "customers", can_view=True)
        self.grant(self.role, "orders", can_view=True)
        user = self.make_user(roles=[self.role])
        profile = EmployeeProfile.objects.get(user=user)
        self.customer.owner_profile = profile
        self.customer.save(update_fields=["owner_profile"])
        product = Product.objects.create(code="RBAC-CTX-P1", name="Hidden product context", category=ProductCategory.objects.create(name="Hidden category context"), hs_code=HSCode.objects.create(code="99887766"))
        sku = SKU.objects.create(product=product, sku="HIDDEN-SKU-CTX", display_name_cn="Hidden SKU context")
        order = Order.objects.create(order_no="RBAC-CTX-O1", customer=self.customer, order_date=date.today(), currency="CNY", exchange_rate=1)
        OrderItem.objects.create(order=order, sku=sku, quantity=1, unit_price=10)
        self.auth(user)

        customer_context = self.client.get(f"/api/context/customers/{self.customer.pk}/")
        self.assertEqual(customer_context.status_code, 200, customer_context.data)
        self.assertNotIn("HIDDEN-SKU-CTX", repr(customer_context.data))
        self.assertNotIn("Hidden product context", repr(customer_context.data))
        product_context = self.client.get(f"/api/context/products/{product.pk}/")
        self.assertEqual(product_context.status_code, 403)

        self.grant(self.role, "products", can_view=True)
        product_context = self.client.get(f"/api/context/products/{product.pk}/")
        self.assertEqual(product_context.status_code, 200, product_context.data)
        self.assertNotIn("Hidden category context", repr(product_context.data))
        self.assertNotIn("99887766", repr(product_context.data))

    def test_purchase_finance_and_sku_apis_are_module_checked(self):
        self.grant(self.role, "customers", can_view=True)
        self.auth(self.make_user(roles=[self.role]))
        for path in ("/api/purchase-orders/", "/api/payment-plans/", "/api/skus/"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 403)

    def test_finance_related_filters_require_the_linked_module_permission(self):
        user = self.make_user(roles=[self.role])
        self.grant(self.role, "transactions", can_view=True)
        self.auth(user)
        for field, value in (("customer", self.customer.pk), ("order", 123), ("supplier", 123), ("purchase_order", 123)):
            with self.subTest(field=field):
                self.assertEqual(self.client.get(f"/api/transactions/?{field}={value}").status_code, 403)

    def test_supplier_capability_hides_product_identifier_without_product_permission(self):
        product = Product.objects.create(code="RBAC-CAP-P1", name="Private capability product")
        supplier = Supplier.objects.create(name="Shared capability supplier", code="RBAC-CAP-S1")
        capability = SupplierCapability.objects.create(product=product, supplier=supplier, name="Capability")
        self.grant(self.role, "suppliers", can_view=True)
        self.auth(self.make_user(roles=[self.role]))
        response = self.client.get("/api/supplier-capabilities/")
        self.assertEqual(response.status_code, 200, response.data)
        row = next(item for item in response.data["results"] if item["id"] == capability.pk)
        self.assertIsNone(row["product"])
        self.assertNotIn("Private capability product", repr(response.data))

    def test_parameter_and_certificate_search_do_not_query_hidden_product_names(self):
        product = Product.objects.create(code="RBAC-PARAM-P1", name="Private parameter product")
        parameter = ProductParameter.objects.create(product=product, name="Length", value="12 cm")
        certificate = ProductCertificate.objects.create(product=product, name="Safety test", certificate_no="CERT-1")
        self.grant(self.role, "parameters", can_view=True)
        self.grant(self.role, "certificates", can_view=True)
        self.auth(self.make_user(roles=[self.role]))

        parameters = self.client.get("/api/product-parameters/?search=Private parameter product")
        certificates = self.client.get("/api/product-certificates/?search=Private parameter product")
        self.assertEqual(parameters.status_code, 200, parameters.data)
        self.assertEqual(certificates.status_code, 200, certificates.data)
        self.assertEqual(parameters.data["results"], [])
        self.assertEqual(certificates.data["results"], [])
        detail = self.client.get(f"/api/product-parameters/{parameter.pk}/")
        self.assertIsNone(detail.data["product"])
        self.assertEqual(detail.data["product_name"], "")
        certificate_detail = self.client.get(f"/api/product-certificates/{certificate.pk}/")
        self.assertIsNone(certificate_detail.data["product"])
        self.assertEqual(certificate_detail.data["product_name"], "")

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

    def test_admin_can_read_permission_overview_without_organization_view(self):
        admin_role = AccessRole.objects.get(code="admin")
        self.grant(admin_role, "organization", can_view=False)
        admin = self.make_user(username="rbac-overview-admin", roles=[admin_role])
        self.auth(admin)

        self.assertEqual(self.client.get("/api/organization/overview/").status_code, 200)
        # The overview exception is limited to the matrix page and does not grant
        # organization-unit CRUD endpoints to an administrator without the module grant.
        self.assertEqual(self.client.get("/api/organization-units/").status_code, 403)

    def test_ordinary_user_without_organization_view_cannot_read_overview(self):
        self.auth(self.make_user(username="rbac-no-organization-view", roles=[self.role]))
        self.assertEqual(self.client.get("/api/organization/overview/").status_code, 403)
        self.assertEqual(APIClient().get("/api/organization/overview/").status_code, 403)

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

    def test_development_superadmin_can_read_protected_media_without_login(self):
        media_root = tempfile.TemporaryDirectory()
        self.addClassCleanup(media_root.cleanup)
        with override_settings(MEDIA_ROOT=media_root.name):
            customer = Customer.objects.create(name="Development media customer", code="DEV-MEDIA")
            follow_up = FollowUp.objects.create(
                customer=customer,
                followed_at="2026-10-12T09:00:00Z",
                content="development attachment",
            )
            attachment = FollowUpAttachment.objects.create(
                follow_up=follow_up,
                file=SimpleUploadedFile("development.txt", b"development bytes", content_type="text/plain"),
                name="development.txt",
                content_type="text/plain",
                size=17,
            )

            response = APIClient().get(f"/api/media/{attachment.file.name}")

            self.assertEqual(response.status_code, 200)
            self.assertEqual(b"".join(response.streaming_content), b"development bytes")
            self.addClassCleanup(response.close)
