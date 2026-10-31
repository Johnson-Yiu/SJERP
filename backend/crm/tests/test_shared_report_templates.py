from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from crm.models import (
    AccessRole, Customer, EmployeeProfile, OperationLog, Order, OrganizationUnit,
    Position, Product, ProductCategory, RolePermission, SharedReportTemplate, SKU,
)


RBAC_SETTINGS = {
    "APP_STAGE": "production", "DEBUG": False,
    "DEVELOPMENT_SUPERADMIN": False, "RBAC_ENFORCEMENT": True,
}
REPORT_MODULES = ("reports", "orders", "customers", "products", "skus", "categories")


@override_settings(**RBAC_SETTINGS, AUDIT_LOG_ENABLED=True)
class SharedReportTemplateTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        company = OrganizationUnit.objects.create(name="模板公司", code="TPL-ROOT", type="company")
        sales = OrganizationUnit.objects.create(name="模板销售部", code="TPL-SALES", parent=company)
        position = Position.objects.create(unit=sales, name="模板岗位", code="TPL-POS")
        self.manager_role = AccessRole.objects.create(name="模板管理员", code="tpl-manager", default_data_scope="all")
        self.employee_role = AccessRole.objects.create(name="模板员工", code="tpl-employee", default_data_scope="self")
        self.department_role = AccessRole.objects.create(name="模板部门员工", code="tpl-department", default_data_scope="department")
        for module in REPORT_MODULES:
            RolePermission.objects.create(
                role=self.manager_role, module=module, can_view=True, can_create=True,
                can_update=True, can_delete=True, can_export=True,
            )
            RolePermission.objects.create(role=self.employee_role, module=module, can_view=True)
            RolePermission.objects.create(role=self.department_role, module=module, can_view=True)
        for module in ("purchases", "suppliers", "transactions"):
            RolePermission.objects.create(
                role=self.manager_role, module=module, can_view=True, can_create=True,
                can_update=True, can_delete=True, can_export=True,
            )
        User = get_user_model()
        manager_user = User.objects.create_user("template-manager", password="test-password")
        manager_b_user = User.objects.create_user("template-manager-b", password="test-password")
        employee_user = User.objects.create_user("template-employee", password="test-password")
        department_user = User.objects.create_user("template-department", password="test-password")
        self.manager = EmployeeProfile.objects.create(user=manager_user, display_name="模板管理员", unit=sales, position=position)
        self.manager_b = EmployeeProfile.objects.create(user=manager_b_user, display_name="模板管理员B", unit=sales, position=position)
        self.employee = EmployeeProfile.objects.create(user=employee_user, display_name="模板员工", unit=sales, position=position)
        self.department_employee = EmployeeProfile.objects.create(user=department_user, display_name="模板部门员工", unit=sales, position=position)
        self.manager.roles.set([self.manager_role])
        self.manager_b.roles.set([self.manager_role])
        self.employee.roles.set([self.employee_role])
        self.department_employee.roles.set([self.department_role])
        self.customer = Customer.objects.create(code="TPL-CUSTOMER", name="模板客户", country="中国", owner_profile=self.employee)
        self.manager_customer = Customer.objects.create(code="TPL-MANAGER-CUSTOMER", name="管理员客户", country="中国", owner_profile=self.manager)
        category = ProductCategory.objects.create(name="模板分类")
        product = Product.objects.create(code="TPL-PRODUCT", name="模板产品", category=category)
        self.sku = SKU.objects.create(sku="TPL-SKU", product=product, unit="pcs")
        self.order = Order.objects.create(
            order_no="TPL-ORDER", customer=self.customer, order_date=date.today(),
            status="confirmed", currency="CNY", exchange_rate=Decimal("1"),
        )
        self.order.items.create(sku=self.sku, quantity=2, unit_price=Decimal("50"))
        self.manager_order = Order.objects.create(
            order_no="TPL-MANAGER-ORDER", customer=self.manager_customer, order_date=date.today(),
            status="confirmed", currency="CNY", exchange_rate=Decimal("1"),
        )
        self.manager_order.items.create(sku=self.sku, quantity=4, unit_price=Decimal("50"))
        self.config = {
            "source": "sales", "group_by": "country", "group_by_2": "customer",
            "grain": "month", "date_field": "order_date", "metric": "amount",
            "view": "bar", "comparison": "previous", "title": "国家客户销售",
            "filters": {},
        }

    def login(self, profile):
        self.client.force_authenticate(user=profile.user)

    def create_template(self, published=False):
        self.login(self.manager)
        response = self.client.post(
            "/api/reports/templates/",
            {"name": "团队销售模板", "description": "按国家和客户查看销售", "config": self.config},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        template = response.data
        if published:
            response = self.client.post(
                f"/api/reports/templates/{template['id']}/publish/",
                {"config_version": template["config_version"]}, format="json",
            )
            self.assertEqual(response.status_code, 200, response.data)
            template = response.data
        return template

    def report_query(self, template_id):
        return {
            "shared_template": template_id, "source": "sales", "group_by": "country",
            "group_by_2": "customer", "grain": "month", "date_field": "order_date",
            "comparison": "previous", "date_from": date.today().isoformat(),
            "date_to": date.today().isoformat(),
        }

    def test_draft_publish_list_and_current_permissions(self):
        draft = self.create_template()
        self.login(self.employee)
        self.assertEqual(self.client.get("/api/reports/templates/").data["results"], [])
        self.assertEqual(self.client.post("/api/reports/templates/", {"name": "员工模板", "config": self.config}, format="json").status_code, 403)

        self.login(self.manager)
        manager_rows = self.client.get("/api/reports/templates/").data["results"]
        self.assertEqual([row["id"] for row in manager_rows], [draft["id"]])
        published = self.client.post(
            f"/api/reports/templates/{draft['id']}/publish/",
            {"config_version": draft["config_version"]}, format="json",
        )
        self.assertEqual(published.status_code, 200, published.data)
        self.login(self.employee)
        rows = self.client.get("/api/reports/templates/").data["results"]
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]["can_use"])

    def test_same_template_uses_current_employee_data_scope_and_unpublish_blocks_url(self):
        template = self.create_template(published=True)
        self.login(self.employee)
        employee_result = self.client.get("/api/reports/data/", self.report_query(template["id"]))
        self.assertEqual(employee_result.status_code, 200, employee_result.data)
        self.assertEqual(employee_result.data["totals"]["amount"], Decimal("100"))
        self.assertEqual(employee_result.data["totals"]["count"], 1)
        self.assertEqual(employee_result.data["rows"][0]["groups"][1]["key"], str(self.customer.id))

        self.login(self.department_employee)
        department_result = self.client.get("/api/reports/data/", self.report_query(template["id"]))
        self.assertEqual(department_result.status_code, 200, department_result.data)
        self.assertEqual(department_result.data["totals"]["amount"], Decimal("300"))
        self.assertEqual(department_result.data["totals"]["count"], 2)
        self.assertEqual(
            {group["key"] for row in department_result.data["rows"] for group in row["groups"] if group["dimension"] == "customer"},
            {str(self.customer.id), str(self.manager_customer.id)},
        )

        self.login(self.manager)
        response = self.client.post(
            f"/api/reports/templates/{template['id']}/unpublish/",
            {"config_version": template["config_version"]}, format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.login(self.employee)
        self.assertEqual(self.client.get("/api/reports/data/", self.report_query(template["id"])).status_code, 404)
        self.assertEqual(self.client.get("/api/reports/templates/").data["results"], [])

    def test_config_whitelist_duplicate_dimensions_and_line_view_are_rejected(self):
        self.login(self.manager)
        invalids = [
            {**self.config, "group_by_2": "country"},
            {**self.config, "view": "line"},
            {**self.config, "filters": {"filter_time": "2026-10"}},
            {**self.config, "arbitrary_query": {"where": "1=1"}},
        ]
        for config in invalids:
            response = self.client.post("/api/reports/templates/", {"name": "非法模板", "config": config}, format="json")
            self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(SharedReportTemplate.objects.count(), 0)

    def test_source_permissions_are_rechecked_for_purchasing_and_actual_cash_templates(self):
        purchase_config = {
            **self.config,
            "source": "purchase", "group_by": "supplier", "group_by_2": "sku",
            "date_field": "order_date",
        }
        actual_cash_config = {
            **self.config,
            "source": "actual_cash", "group_by": "direction", "group_by_2": "",
            "date_field": "bank_date",
        }
        self.login(self.manager)
        created_ids = []
        for config, name in ((purchase_config, "采购模板"), (actual_cash_config, "银行资金模板")):
            response = self.client.post("/api/reports/templates/", {"name": name, "config": config}, format="json")
            self.assertEqual(response.status_code, 201, response.data)
            publish = self.client.post(
                f"/api/reports/templates/{response.data['id']}/publish/",
                {"config_version": response.data["config_version"]}, format="json",
            )
            self.assertEqual(publish.status_code, 200, publish.data)
            created_ids.append(response.data["id"])

        self.login(self.employee)
        self.assertEqual(self.client.get("/api/reports/templates/").data["results"], [])
        for template_id, config in zip(created_ids, (purchase_config, actual_cash_config)):
            params = {
                "shared_template": template_id,
                "source": config["source"], "group_by": config["group_by"],
                "date_field": config["date_field"], "date_from": date.today().isoformat(),
                "date_to": date.today().isoformat(),
            }
            self.assertEqual(self.client.get("/api/reports/data/", params).status_code, 403)

    def test_revoked_reports_view_is_immediate(self):
        template = self.create_template(published=True)
        permission = RolePermission.objects.get(role=self.employee_role, module="reports")
        permission.can_view = False
        permission.save(update_fields=["can_view"])
        self.login(self.employee)
        self.assertEqual(self.client.get("/api/reports/templates/").status_code, 403)
        self.assertEqual(self.client.get("/api/reports/data/", self.report_query(template["id"])).status_code, 403)

    def test_version_conflict_prevents_silent_overwrite_and_operations_are_audited(self):
        template = self.create_template()
        self.login(self.manager)
        response = self.client.patch(
            f"/api/reports/templates/{template['id']}/",
            {"name": "新名称", "config": self.config, "config_version": template["config_version"]}, format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        stale = self.client.patch(
            f"/api/reports/templates/{template['id']}/",
            {"name": "覆盖名称", "config": self.config, "config_version": template["config_version"]}, format="json",
        )
        self.assertEqual(stale.status_code, 409, stale.data)
        current = SharedReportTemplate.objects.get(pk=template["id"])
        self.assertEqual(current.name, "新名称")
        publish = self.client.post(
            f"/api/reports/templates/{template['id']}/publish/",
            {"config_version": current.config_version}, format="json",
        )
        self.assertEqual(publish.status_code, 200, publish.data)
        self.assertEqual(publish.data["config_version"], 3)
        self.assertEqual(SharedReportTemplate.objects.get(pk=template["id"]).config_version, 3)
        history = OperationLog.objects.filter(entity="crm.sharedreporttemplate", object_id=str(template["id"]))
        self.assertEqual(history.count(), 3)
        self.assertEqual(set(history.values_list("action_label", flat=True)), {"创建团队共享模板", "修改团队共享模板", "发布团队共享模板"})
        self.assertEqual(
            sorted(row.metadata["config_version"] for row in history),
            [1, 2, 3],
        )

    def test_publish_and_unpublish_versions_reject_stale_and_duplicate_operations(self):
        template = self.create_template(published=True)
        self.assertEqual(template["config_version"], 2)

        self.login(self.manager)
        unpublished = self.client.post(
            f"/api/reports/templates/{template['id']}/unpublish/",
            {"config_version": template["config_version"]}, format="json",
        )
        self.assertEqual(unpublished.status_code, 200, unpublished.data)
        self.assertEqual(unpublished.data["config_version"], 3)

        self.login(self.manager_b)
        stale_publish = self.client.post(
            f"/api/reports/templates/{template['id']}/publish/",
            {"config_version": template["config_version"]}, format="json",
        )
        self.assertEqual(stale_publish.status_code, 409, stale_publish.data)

        current = self.client.get(f"/api/reports/templates/{template['id']}/")
        self.assertEqual(current.status_code, 200, current.data)
        self.assertEqual(current.data["config_version"], 3)
        published = self.client.post(
            f"/api/reports/templates/{template['id']}/publish/",
            {"config_version": current.data["config_version"]}, format="json",
        )
        self.assertEqual(published.status_code, 200, published.data)
        self.assertEqual(published.data["config_version"], 4)

        stale_unpublish = self.client.post(
            f"/api/reports/templates/{template['id']}/unpublish/",
            {"config_version": 3}, format="json",
        )
        self.assertEqual(stale_unpublish.status_code, 409, stale_unpublish.data)
        unpublished_again = self.client.post(
            f"/api/reports/templates/{template['id']}/unpublish/",
            {"config_version": 4}, format="json",
        )
        self.assertEqual(unpublished_again.status_code, 200, unpublished_again.data)
        self.assertEqual(unpublished_again.data["config_version"], 5)

        duplicate_unpublish = self.client.post(
            f"/api/reports/templates/{template['id']}/unpublish/",
            {"config_version": 5}, format="json",
        )
        self.assertEqual(duplicate_unpublish.status_code, 409, duplicate_unpublish.data)
        republished = self.client.post(
            f"/api/reports/templates/{template['id']}/publish/",
            {"config_version": 5}, format="json",
        )
        self.assertEqual(republished.status_code, 200, republished.data)
        self.assertEqual(republished.data["config_version"], 6)
        duplicate_publish = self.client.post(
            f"/api/reports/templates/{template['id']}/publish/",
            {"config_version": 6}, format="json",
        )
        self.assertEqual(duplicate_publish.status_code, 409, duplicate_publish.data)

        history = OperationLog.objects.filter(entity="crm.sharedreporttemplate", object_id=str(template["id"]))
        self.assertEqual(history.count(), 6)
        self.assertEqual(
            sorted(row.metadata["config_version"] for row in history),
            [1, 2, 3, 4, 5, 6],
        )

    def test_delete_keeps_audit_record(self):
        template = self.create_template()
        self.login(self.manager)
        updated = self.client.patch(
            f"/api/reports/templates/{template['id']}/",
            {"name": "删除前模板", "config": self.config, "config_version": template["config_version"]}, format="json",
        )
        self.assertEqual(updated.status_code, 200, updated.data)
        published = self.client.post(
            f"/api/reports/templates/{template['id']}/publish/",
            {"config_version": updated.data["config_version"]}, format="json",
        )
        self.assertEqual(published.status_code, 200, published.data)
        unpublished = self.client.post(
            f"/api/reports/templates/{template['id']}/unpublish/",
            {"config_version": published.data["config_version"]}, format="json",
        )
        self.assertEqual(unpublished.status_code, 200, unpublished.data)
        response = self.client.delete(
            f"/api/reports/templates/{template['id']}/",
            data={"config_version": unpublished.data["config_version"]}, format="json",
        )
        self.assertEqual(response.status_code, 204, response.data)
        self.assertFalse(SharedReportTemplate.objects.filter(pk=template["id"]).exists())

        history_response = self.client.get(f"/api/reports/templates/{template['id']}/history/")
        self.assertEqual(history_response.status_code, 200, history_response.data)
        history_rows = history_response.data
        self.assertEqual(
            [row["action_display"] for row in history_rows],
            ["创建团队共享模板", "修改团队共享模板", "发布团队共享模板", "取消发布团队共享模板", "删除团队共享模板"],
        )
        self.assertEqual([row["metadata"]["config_version"] for row in history_rows], [1, 2, 3, 4, 4])
        self.assertEqual(history_rows[-1]["object_label"], "删除前模板")
        self.assertEqual(history_rows[-1]["before_data"]["config_version"], 4)

        generic_manager = self.client.get(
            "/api/operation-logs/",
            {"entity": "crm.sharedreporttemplate", "object_id": template["id"]},
        )
        self.assertEqual(generic_manager.status_code, 200, generic_manager.data)
        generic_rows = generic_manager.data.get("results", generic_manager.data)
        self.assertEqual(len(generic_rows), 5)
        self.assertTrue(all(row["entity"] == "crm.sharedreporttemplate" for row in generic_rows))

        self.login(self.employee)
        denied = self.client.get(f"/api/reports/templates/{template['id']}/history/")
        self.assertEqual(denied.status_code, 403, denied.data)
        generic = self.client.get(
            "/api/operation-logs/",
            {"entity": "crm.sharedreporttemplate", "object_id": template["id"]},
        )
        self.assertEqual(generic.status_code, 200, generic.data)
        self.assertEqual(generic.data.get("results", generic.data), [])

        self.login(self.manager)
        invalid = self.client.get("/api/reports/templates/not-an-id/history/")
        self.assertEqual(invalid.status_code, 404, invalid.data)
