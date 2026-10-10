from django.test import TestCase
from rest_framework.test import APIClient
from crm.models import CategoryAttribute, ProductCategory, Product, PurchaseOrderItem, SKU, Supplier, SupplierCandidateOverride, SupplierSKU


class SupplierBatchBindingTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.root = ProductCategory.objects.create(name="灯带")
        self.child = ProductCategory.objects.create(name="COB", parent=self.root)
        self.other = ProductCategory.objects.create(name="电源")
        self.product = Product.objects.create(code="BIND", name="COB灯带", category=self.child)
        self.skus = [SKU.objects.create(product=self.product, sku=f"BIND-{i}", display_name_cn=f"灯带{i}") for i in range(2)]
        self.a = Supplier.objects.create(name="大类供应商", code="AA")
        self.b = Supplier.objects.create(name="子分类供应商", code="BB")
        self.c = Supplier.objects.create(name="其他供应商", code="CC")
        self.a.supply_categories.add(self.root)
        self.b.supply_categories.add(self.child)
        self.c.supply_categories.add(self.other)
        self.url = f"/api/products/{self.product.pk}/supplier-candidate-pool/"

    def bind(self, suppliers=None, ids=None):
        return self.client.post(self.url, {"sku_ids": ids or [s.pk for s in self.skus], "suppliers": suppliers or [{"supplier": self.a.pk}, {"supplier": self.b.pk, "quality": "A+", "notes": "测试差异"}]}, format="json")

    def test_eligible_includes_parents_and_excludes_other_branches(self):
        response = self.client.get(self.url, {"eligible": "1"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual({r["id"] for r in response.data}, {self.a.pk, self.b.pk})

    def test_batch_is_idempotent_and_only_creates_candidates(self):
        for _ in range(2):
            response = self.bind()
            self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(SupplierCandidateOverride.objects.count(), 4)
        self.assertEqual(SupplierSKU.objects.count(), 0)
        traits = SupplierCandidateOverride.objects.get(sku=self.skus[0], supplier=self.a).characteristics
        self.assertEqual(traits["质量等级"], "B")
        self.assertEqual(traits["推荐优先级"], "中")
        self.assertEqual(traits["交货期"], "标准")

    def test_invalid_supplier_rejects_whole_batch(self):
        response = self.bind([{"supplier": self.a.pk}, {"supplier": 999999}])
        self.assertEqual(response.status_code, 400)
        self.assertFalse(SupplierCandidateOverride.objects.exists())

    def test_inactive_and_foreign_skus_rejected(self):
        self.skus[1].active = False
        self.skus[1].save()
        self.assertEqual(self.bind().status_code, 400)
        other_product = Product.objects.create(code="OTHER", name="其他产品", category=self.root)
        other_sku = SKU.objects.create(product=other_product, sku="OTHER-SKU", display_name_cn="其他")
        self.assertEqual(self.bind(ids=[other_sku.pk]).status_code, 400)
        self.assertFalse(SupplierCandidateOverride.objects.exists())

    def test_invalid_traits_rejected_and_existing_traits_preserved(self):
        self.assertEqual(self.bind([{"supplier": self.a.pk, "quality": "D"}]).status_code, 400)
        SupplierCandidateOverride.objects.create(sku=self.skus[0], supplier=self.a, characteristics={"背胶": "3M"}, is_allowed=False)
        self.assertEqual(self.bind().status_code, 200)
        override = SupplierCandidateOverride.objects.get(sku=self.skus[0], supplier=self.a)
        self.assertTrue(override.is_allowed)
        self.assertEqual(override.characteristics["背胶"], "3M")

    def test_supplier_creation_requires_categories_and_allows_multiple(self):
        data = {"name": "新供应商", "code": "DD"}
        self.assertEqual(self.client.post("/api/suppliers/", data, format="json").status_code, 400)
        data["supply_categories"] = [self.root.pk, self.other.pk]
        response = self.client.post("/api/suppliers/", data, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(set(response.data["supply_categories"]), {self.root.pk, self.other.pk})

    def test_candidate_binding_does_not_create_supplier_sku_for_manual_purchase(self):
        self.assertEqual(self.bind().status_code, 200)
        response = self.client.post("/api/purchase-orders/", {"exchange_rate": "1", "supplier": self.b.pk, "order_date": "2026-09-16", "currency": "CNY", "items": [{"sku": self.skus[0].pk, "quantity": "2", "unit_price": "5"}]}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(self.client.post(f"/api/purchase-orders/{response.data['id']}/place/", {}, format="json").status_code, 200)
        item = PurchaseOrderItem.objects.get(purchase_order_id=response.data["id"])
        self.assertIsNone(item.supplier_sku)
        self.assertEqual(item.supplier_name_snapshot, self.b.name)
        self.assertEqual(item.supplier_characteristics_snapshot, {})
        self.assertEqual(SupplierSKU.objects.count(), 0)

    def test_parameter_filters_include_legacy_names(self):
        CategoryAttribute.objects.create(category=self.root, key="色温/发光颜色", name="色温/发光颜色", include_in_sku=True)
        self.skus[0].parameter_values = {f"{self.root.pk}:色温": "3000K"}
        self.skus[0].save(update_fields=["parameter_values"])
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("3000K", response.data["parameter_options"][0]["values"])

    def test_all_suppliers_match_first_and_allow_cross_category_binding(self):
        response = self.client.get(self.url, {"eligible": "1", "all": "1"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 3)
        self.assertTrue(response.data[0]["category_match"])
        self.assertFalse(response.data[-1]["category_match"])
        self.assertEqual(response.data[-1]["id"], self.c.pk)
        response = self.bind([{"supplier": self.c.pk}])
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(SupplierCandidateOverride.objects.filter(supplier=self.c).count(), 2)
        self.assertEqual(list(self.c.supply_categories.values_list("pk", flat=True)), [self.other.pk])
