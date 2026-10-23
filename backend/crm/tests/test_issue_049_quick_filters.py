from datetime import datetime, timezone as datetime_timezone

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from crm.models import AccessRole, Customer, EmployeeProfile, FollowUp, OrganizationUnit, Position, RolePermission, Transaction


RBAC_SETTINGS = {
    "APP_STAGE": "production",
    "DEBUG": False,
    "DEVELOPMENT_SUPERADMIN": False,
    "RBAC_ENFORCEMENT": True,
}


@override_settings(**RBAC_SETTINGS)
class QuickFilterApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.company = OrganizationUnit.objects.create(name="快捷筛选公司", code="QF-ROOT", type="company")
        self.unit = OrganizationUnit.objects.create(name="快捷筛选销售部", code="QF-SALES", parent=self.company)
        self.position = Position.objects.create(unit=self.unit, name="销售", code="QF-STAFF")
        self.role = AccessRole.objects.create(name="快捷筛选全量角色", code="qf-all", default_data_scope="all")
        for module in ("customers", "contacts", "followups", "transactions"):
            RolePermission.objects.create(role=self.role, module=module, can_view=True, can_create=True, can_update=True, can_delete=True)
        user = get_user_model().objects.create_user(username="qf-all", password="test-password")
        self.employee = EmployeeProfile.objects.create(user=user, display_name="筛选负责人", unit=self.unit, position=self.position)
        self.employee.roles.add(self.role)
        self.client.force_authenticate(user=user)

    @staticmethod
    def rows(response):
        assert response.status_code == 200, response.data
        return response.data.get("results", response.data)

    def test_customer_filters_combine_against_real_fields(self):
        matching = Customer.objects.create(
            code="QF-C1", name="筛选客户一", country="德国", status="customer", owner_profile=self.employee, owner="筛选负责人",
        )
        Customer.objects.create(code="QF-C2", name="筛选客户二", country="德国", status="lead", owner_profile=self.employee, owner="筛选负责人")
        Customer.objects.create(code="QF-C3", name="筛选客户三", country="中国", status="customer", owner_profile=self.employee, owner="筛选负责人")

        response = self.client.get(
            "/api/customers/",
            {"owner_profile": self.employee.id, "country": "德国", "status": "customer"},
        )

        self.assertEqual({row["id"] for row in self.rows(response)}, {matching.id})

    def test_customer_filter_options_are_scoped(self):
        Customer.objects.create(code="QF-C4", name="德国客户", country="德国", owner_profile=self.employee, owner="筛选负责人")
        Customer.objects.create(code="QF-C5", name="中国客户", country="中国", owner_profile=self.employee, owner="筛选负责人")

        countries = self.client.get("/api/customers/country-options/")
        owners = self.client.get("/api/customers/owner-options/")

        self.assertEqual({row["value"] for row in countries.data}, {"德国", "中国"})
        self.assertEqual({row["id"] for row in owners.data}, {self.employee.id})

    def test_follow_up_filters_combine_owner_type_and_date_range(self):
        customer = Customer.objects.create(code="QF-C6", name="跟进客户", owner_profile=self.employee, owner="筛选负责人")
        included = FollowUp.objects.create(
            customer=customer,
            followed_at=datetime(2026, 10, 10, 9, 0, tzinfo=datetime_timezone.utc),
            type="call",
            owner="林晓",
            subject="目标记录",
            content="已沟通",
        )
        FollowUp.objects.create(
            customer=customer,
            followed_at=datetime(2026, 10, 11, 9, 0, tzinfo=datetime_timezone.utc),
            type="email",
            owner="林晓",
            subject="其他方式",
            content="已沟通",
        )
        FollowUp.objects.create(
            customer=customer,
            followed_at=datetime(2026, 9, 30, 9, 0, tzinfo=datetime_timezone.utc),
            type="call",
            owner="林晓",
            subject="范围外",
            content="已沟通",
        )

        response = self.client.get(
            "/api/follow-ups/",
            {"owner": "林晓", "type": "call", "from": "2026-10-01", "to": "2026-10-10"},
        )

        self.assertEqual({row["id"] for row in self.rows(response)}, {included.id})
    def test_scoped_employee_cannot_expand_results_with_filter_options(self):
        scoped_role = AccessRole.objects.create(name="快捷筛选本人角色", code="qf-self", default_data_scope="self")
        for module in ("customers", "contacts", "followups"):
            RolePermission.objects.create(role=scoped_role, module=module, can_view=True)
        user = get_user_model().objects.create_user(username="qf-self", password="test-password")
        scoped_employee = EmployeeProfile.objects.create(user=user, display_name="本人负责人", unit=self.unit, position=self.position)
        scoped_employee.roles.add(scoped_role)
        own = Customer.objects.create(code="QF-C7", name="本人客户", country="法国", owner_profile=scoped_employee, owner="本人负责人")
        other = Customer.objects.create(code="QF-C8", name="他人客户", country="日本", owner_profile=self.employee, owner="筛选负责人")
        self.client.force_authenticate(user=user)

        result = self.client.get("/api/customers/", {"country": "日本"})
        options = self.client.get("/api/customers/country-options/")

        self.assertEqual({row["id"] for row in self.rows(result)}, set())
        self.assertEqual({row["value"] for row in options.data}, {"法国"})
        self.assertNotEqual(own.id, other.id)

    def test_existing_transaction_filters_combine_without_changing_finance_scope(self):
        included = Transaction.objects.create(
            transaction_no="QF-T1", transaction_date="2026-10-10", direction="income", kind="other_income",
            category="其他收入", amount="10", currency="CNY", exchange_rate="1", rmb_amount="10", status="confirmed",
        )
        Transaction.objects.create(
            transaction_no="QF-T2", transaction_date="2026-10-11", direction="expense", kind="other_expense",
            category="其他支出", amount="20", currency="CNY", exchange_rate="1", rmb_amount="20", status="confirmed",
        )
        Transaction.objects.create(
            transaction_no="QF-T3", transaction_date="2026-10-10", direction="income", kind="other_income",
            category="其他收入", amount="30", currency="CNY", exchange_rate="1", rmb_amount="30", status="cancelled",
        )

        response = self.client.get(
            "/api/transactions/",
            {"date_from": "2026-10-10", "date_to": "2026-10-10", "direction": "income", "status": "confirmed"},
        )

        self.assertEqual({row["id"] for row in self.rows(response)}, {included.id})
