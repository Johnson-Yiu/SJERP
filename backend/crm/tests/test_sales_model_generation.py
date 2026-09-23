from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework.exceptions import ValidationError
from crm.models import CategoryAttribute, ProductCategory, Product, SKU
from crm.services.sku_plans import _sales_model_for_base


class SalesModelGenerationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        category = ProductCategory.objects.create(name="测试灯带")
        CategoryAttribute.objects.create(category=category, key="voltage", name="电压", unit="V", include_in_sku=True, include_in_sales_model=True)
        CategoryAttribute.objects.create(category=category, key="color", name="颜色", include_in_sku=True, include_in_sales_model=False)
        self.product = Product.objects.create(code="MODEL", name="测试产品", sales_model_prefix="TEST", category=category)
        self.category = category

    def create(self, color="red", voltage="12"):
        return self.client.post("/api/skus/", {"product": self.product.pk, "parameter_values": {"voltage": voltage, "color": color}, "sales_model_abbreviations": {f"{self.category.pk}:voltage:{voltage}V": f"{voltage}V"}}, format="json")

    def test_new_model_has_no_sequence_and_model_collision_is_rejected(self):
        response = self.create()
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["sales_model"], "TEST-12V")
        collision = self.create(color="blue")
        self.assertEqual(collision.status_code, 400, collision.data)
        self.assertEqual(SKU.objects.count(), 1)
        different = self.create(voltage="24")
        self.assertEqual(different.status_code, 201, different.data)
        self.assertEqual(different.data["sales_model"], "TEST-24V")

    def test_same_parameters_still_rejected_and_existing_model_not_rewritten(self):
        first = self.create()
        sku = SKU.objects.get(pk=first.data["id"])
        sku.sales_model = "TEST-12V-1"
        sku.save(update_fields=["sales_model"])
        self.assertEqual(self.create().status_code, 400)
        response = self.client.patch(f"/api/skus/{sku.pk}/", {"unit": "reel"}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["sales_model"], "TEST-12V-1")

    def test_plan_generation_never_allocates_a_numeric_suffix(self):
        self.assertEqual(_sales_model_for_base("TEST-12V", set()), "TEST-12V")
        with self.assertRaises(ValidationError):
            _sales_model_for_base("TEST-12V", {"test-12v"})
        self.assertEqual(_sales_model_for_base("TEST-12V", set(), "TEST-12V-2"), "TEST-12V-2")
        self.assertEqual(_sales_model_for_base("TEST-24V", set(), "TEST-12V-2"), "TEST-24V")
