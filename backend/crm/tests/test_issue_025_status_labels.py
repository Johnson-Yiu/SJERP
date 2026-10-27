from django.test import TestCase
from rest_framework.test import APIClient

from ..models import Contact, Customer
from ..serializers import CustomerSerializer


class Issue025CustomerStatusLabelsTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = Customer.objects.create(
            code="ISS025-C001",
            name="ISS-025 客户",
            country="Germany",
            status="contact",
        )

    def test_lifecycle_values_are_unchanged_but_display_names_are_consistent(self):
        self.assertEqual(
            [value for value, _label in Customer.STATUS_CHOICES],
            ["lead", "contact", "opportunity", "customer", "company"],
        )
        self.assertEqual(self.customer.status, "contact")
        self.assertEqual(CustomerSerializer(self.customer).data["status_display"], "已联系")

        response = self.client.get("/api/customers/", {"status": "contact"})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual([row["status"] for row in response.data["results"]], ["contact"])

    def test_customer_and_contact_details_use_customer_status_label(self):
        customer_context = self.client.get(f"/api/context/customers/{self.customer.pk}/")
        self.assertEqual(customer_context.status_code, 200, customer_context.data)
        self.assertEqual(customer_context.data["badge"], "已联系")

        contact = Contact.objects.create(customer=self.customer, name="ISS-025 联系人")
        contact_context = self.client.get(f"/api/context/contacts/{contact.pk}/")
        self.assertEqual(contact_context.status_code, 200, contact_context.data)
        company = next(section for section in contact_context.data["sections"] if section["key"] == "company")
        self.assertIn(["status_display", "状态", "status"], company["columns"])
        self.assertEqual(company["rows"][0]["status_display"], "已联系")
