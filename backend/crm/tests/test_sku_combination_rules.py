from django.test import TestCase
from rest_framework.test import APIClient
from crm.models import Product, ProductCategory, CategoryAttribute, SKU


class CombinationRulesTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        category = ProductCategory.objects.create(name="组合测试")
        for key, unit in [("voltage", "V"), ("length", "米")]:
            CategoryAttribute.objects.create(category=category, key=key, name=key, unit=unit, include_in_sku=True)
        self.product = Product.objects.create(code="RULES", name="组合灯带", category=category)
        self.a, self.b = f"{category.pk}:voltage", f"{category.pk}:length"
        self.url = f"/api/products/{self.product.pk}/combination-rules/"

    def rule(self, trigger="12V", value="5米", op="eq"):
        return {"when": self.a, "when_values": [trigger], "target": self.b, "op": op, "values": [value]}

    def post(self, rules, save=True):
        return self.client.post(self.url, {"rules": rules, "save": save}, format="json")

    def create(self, voltage, length):
        return self.client.post("/api/skus/", {"product": self.product.pk, "parameter_values": {"voltage": voltage, "length": length}}, format="json")

    def test_preview_does_not_save_and_creation_enforces_rules_with_units(self):
        rules = [self.rule(), self.rule("24V", "10米")]
        self.assertEqual(self.post(rules, False).status_code, 200)
        self.product.refresh_from_db()
        self.assertEqual(self.product.combination_rules, [])
        self.assertEqual(self.post(rules).status_code, 200)
        self.assertEqual(self.create("12", "5").status_code, 201)
        self.assertEqual(self.create("24", "10").status_code, 201)
        invalid = self.create("12", "10")
        self.assertEqual(invalid.status_code, 400, invalid.data)
        self.assertIn("combination_rules", invalid.data)
        self.assertEqual(SKU.objects.count(), 2)

    def test_conflicting_overlapping_conditions_cannot_save(self):
        good = [self.rule()]
        self.assertEqual(self.post(good).status_code, 200)
        second = self.rule("12v", "10米")
        second["when_values"] += ["24V"]
        response = self.post([self.rule(), second])
        self.assertEqual(response.status_code, 400)
        self.assertIn("1", str(response.data))
        self.assertIn("2", str(response.data))
        self.product.refresh_from_db()
        self.assertEqual(self.product.combination_rules, good)

    def test_global_allowed_values_and_prohibition(self):
        allowed = {"when": "", "when_values": [], "target": self.b, "op": "in", "values": ["5米", "10米"]}
        self.assertEqual(self.post([allowed, self.rule("24V", "5米", "neq")]).status_code, 200)
        self.assertEqual(self.create("24V", "5米").status_code, 400)
        self.assertEqual(self.create("24V", "10米").status_code, 201)
        self.assertEqual(self.create("12V", "20米").status_code, 400)

    def test_three_way_conflict_is_detected(self):
        rules = [{"when": "", "when_values": [], "target": self.b, "op": "in", "values": values} for values in [["5", "10"], ["10", "20"], ["5", "20"]]]
        self.assertEqual(self.post(rules).status_code, 400)

    def test_saving_rules_preserves_existing_skus_and_unrelated_edits(self):
        created = self.create("12V", "10米")
        self.assertEqual(created.status_code, 201, created.data)
        self.assertEqual(self.post([self.rule()]).status_code, 200)
        sku = SKU.objects.get(pk=created.data["id"])
        self.assertEqual(sku.parameter_values["length"], "10米")
        response = self.client.patch(f"/api/skus/{sku.pk}/", {"unit": "reel"}, format="json")
        self.assertEqual(response.status_code, 200, response.data)

    def test_bad_rules_and_removed_parameters_are_rejected(self):
        for rules in [[{**self.rule(), "target": []}], [{**self.rule(), "target": "missing"}], [{**self.rule(), "values": []}], [{**self.rule(), "values": ["5", "10"]}]]:
            self.assertEqual(self.post(rules).status_code, 400)

    def test_product_patch_cannot_bypass_rule_validation(self):
        response = self.client.patch(f"/api/products/{self.product.pk}/", {"combination_rules": [self.rule()]}, format="json")
        self.assertEqual(response.status_code, 200)
        self.product.refresh_from_db()
        self.assertEqual(self.product.combination_rules, [])
