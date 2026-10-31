from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from crm.models import AccessRole, Contact, Customer, EmployeeProfile, OrganizationUnit, Position, RolePermission


RBAC_SETTINGS = {
    "APP_STAGE": "production",
    "DEBUG": False,
    "DEVELOPMENT_SUPERADMIN": False,
    "RBAC_ENFORCEMENT": True,
}


@override_settings(**RBAC_SETTINGS)
class ContactDuplicateScopeTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        company = OrganizationUnit.objects.create(name="重复提醒公司", code="DUP-ROOT", type="company")
        unit = OrganizationUnit.objects.create(name="重复提醒销售部", code="DUP-SALES", parent=company)
        position = Position.objects.create(unit=unit, name="销售", code="DUP-SALES-POS")
        self.all_role = AccessRole.objects.create(name="重复提醒全量角色", code="dup-all", default_data_scope="all")
        self.self_role = AccessRole.objects.create(name="重复提醒本人角色", code="dup-self", default_data_scope="self")
        for role in (self.all_role, self.self_role):
            for module in ("customers", "contacts"):
                RolePermission.objects.create(role=role, module=module, can_view=True, can_create=True, can_update=True)
        all_user = get_user_model().objects.create_user(username="dup-all", password="test-password")
        self.all_employee = EmployeeProfile.objects.create(
            user=all_user, display_name="重复提醒全量", unit=unit, position=position,
        )
        self.all_employee.roles.add(self.all_role)
        own_user = get_user_model().objects.create_user(username="dup-self", password="test-password")
        self.own_employee = EmployeeProfile.objects.create(
            user=own_user, display_name="重复提醒本人", unit=unit, position=position,
        )
        self.own_employee.roles.add(self.self_role)
        self.customer = Customer.objects.create(code="DUP-CUSTOMER", name="重复提醒客户", owner_profile=self.own_employee)
        self.other_customer = Customer.objects.create(code="DUP-OTHER", name="另一客户", owner_profile=self.all_employee)

    def test_customer_contact_query_contains_all_pages_and_excludes_other_customers(self):
        contacts = [
            Contact.objects.create(customer=self.customer, name=f"分页联系人 {index:02d}")
            for index in range(51)
        ]
        other = Contact.objects.create(customer=self.other_customer, name="分页联系人 00")
        self.client.force_authenticate(user=self.all_employee.user)

        first = self.client.get("/api/contacts/", {"customer": self.customer.id})
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.data["count"], 51)
        self.assertEqual(len(first.data["results"]), 50)
        self.assertIsNotNone(first.data["next"])
        self.assertNotIn(other.id, {row["id"] for row in first.data["results"]})

        second = self.client.get("/api/contacts/", {"customer": self.customer.id, "page": 2})
        self.assertEqual(second.status_code, 200)
        self.assertEqual({row["id"] for row in second.data["results"]}, {contacts[-1].id})

    def test_self_scoped_employee_cannot_disclose_other_customer_contacts_through_filter(self):
        own = Contact.objects.create(customer=self.customer, name="本人客户联系人")
        other = Contact.objects.create(customer=self.other_customer, name="同名联系人")
        self.client.force_authenticate(user=self.own_employee.user)

        own_response = self.client.get("/api/contacts/", {"customer": self.customer.id})
        other_response = self.client.get("/api/contacts/", {"customer": self.other_customer.id})

        self.assertEqual(own_response.status_code, 200)
        self.assertEqual({row["id"] for row in own_response.data["results"]}, {own.id})
        self.assertEqual(other_response.status_code, 200)
        self.assertEqual(other_response.data["results"], [])
        self.assertNotIn(other.id, {row["id"] for row in own_response.data["results"]})
