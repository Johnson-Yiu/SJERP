from datetime import date
from copy import deepcopy
from django.test import TestCase
from rest_framework.test import APIClient
from crm.models import CategoryAttribute, ProductCategory, Product, SKU, Supplier, SupplierSKU, InventoryMovement, PurchaseOrderItem


class SKUPlansCandidatesTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.category = ProductCategory.objects.create(name="灯带")
        CategoryAttribute.objects.create(category=self.category, key="voltage", name="电压", include_in_sku=True)
        CategoryAttribute.objects.create(category=self.category, key="color", name="颜色", include_in_sku=True)
        self.product = Product.objects.create(code="PLAN", name="灯带产品", category=self.category)
        self.a = Supplier.objects.create(name="供应商甲", code="JA")
        self.b = Supplier.objects.create(name="供应商乙", code="JB")
        self.sku = self.create_sku("red")
        self.base = f"/api/products/{self.product.pk}/sku-plan/"

    def create_sku(self, color):
        response = self.client.post("/api/skus/", {"product": self.product.pk, "parameter_values": {"voltage": "24", "color": color}}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        return SKU.objects.get(pk=response.data["id"])

    def draft(self):
        response = self.client.post(self.base, {}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        return response.data

    def save_draft(self, draft):
        response = self.client.patch(self.base, draft, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        return response.data

    def action(self, draft, action="publish"):
        return self.client.post(self.base + action + "/", {"updated_at": draft["updated_at"]}, format="json")

    def test_dimension_removal_merges_without_rewriting_history(self):
        other = self.create_sku("blue")
        movement = InventoryMovement.objects.create(sku=self.sku, movement_no="INV-PLAN", type="purchase_in", quantity=10, movement_date=date.today())
        original = deepcopy(self.sku.parameter_values)
        draft = self.draft()
        next(d for d in draft["definitions"] if d["key"] == "color")["include_in_sku"] = False
        draft = self.save_draft(draft)
        impact = self.action(draft, "analyze")
        self.assertEqual(impact.data["new_count"], 1)
        response = self.action(draft)
        self.assertEqual(response.status_code, 200, response.data)
        self.sku.refresh_from_db(); other.refresh_from_db(); movement.refresh_from_db()
        self.assertFalse(self.sku.active); self.assertFalse(other.active)
        self.assertEqual(self.sku.parameter_values, original)
        self.assertEqual(movement.sku_id, self.sku.pk)
        self.assertEqual(movement.quantity, 10)
        target = self.sku.successors.get().target
        self.assertEqual(other.successors.get().target_id, target.pk)
        self.assertEqual(target.parameter_values[f"{self.category.pk}:color"], "")
        self.assertEqual(target.inventory_movements.count(), 0)
        self.assertEqual(self.client.patch(f"/api/skus/{self.sku.pk}/", {"active": True}, format="json").status_code, 400)

    def test_add_dimension_fills_existing_identity_and_does_not_multiply(self):
        draft = self.draft()
        draft["definitions"].append({"category_id": 0, "key": "pcb", "name": "PCB", "include_in_sku": True, "default_value": "double"})
        draft = self.save_draft(draft)
        self.assertEqual(self.action(draft).status_code, 200)
        self.sku.refresh_from_db()
        self.assertTrue(self.sku.active)
        self.assertEqual(self.sku.parameter_values["0:pcb"], "double")
        self.assertEqual(self.product.skus.count(), 1)
        self.assertEqual(self.sku.versions.count(), 1)

    def test_split_requires_distinct_filled_variants(self):
        draft = self.draft()
        draft["definitions"].append({"category_id": 0, "key": "pcb", "name": "PCB", "include_in_sku": True})
        draft = self.save_draft(draft)
        self.assertEqual(self.action(draft).status_code, 400)
        draft["assignments"] = {str(self.sku.pk): [{"0:pcb": "double"}, {"0:pcb": "four"}]}
        draft = self.save_draft(draft)
        response = self.action(draft)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(self.sku.successors.count(), 2)
        self.assertEqual(self.product.skus.filter(active=True).count(), 2)

    def test_category_changes_do_not_change_existing_product_schema(self):
        CategoryAttribute.objects.filter(key="color").delete()
        duplicate = self.client.post("/api/skus/", {"product": self.product.pk, "parameter_values": {"voltage": "24", "color": "red"}}, format="json")
        self.assertEqual(duplicate.status_code, 400)
        result = self.client.patch(f"/api/skus/{self.sku.pk}/", {"default_price": "12"}, format="json")
        self.assertEqual(result.status_code, 200, result.data)

    def test_stale_draft_cannot_publish(self):
        draft = self.draft()
        self.create_sku("blue")
        self.assertTrue(self.action(draft, "analyze").data["stale"])
        self.assertEqual(self.action(draft).status_code, 400)
        self.assertEqual(self.product.skus.count(), 2)

    def test_ordinary_property_does_not_create_identity(self):
        draft = self.draft()
        draft["definitions"].append({"category_id": 0, "key": "glue", "name": "背胶", "default_value": "3M"})
        draft = self.save_draft(draft)
        self.assertEqual(self.action(draft).status_code, 200)
        self.sku.refresh_from_db()
        result = self.client.patch(f"/api/skus/{self.sku.pk}/", {"parameter_values": {**self.sku.parameter_values, "0:glue": "other"}}, format="json")
        self.assertEqual(result.status_code, 200, result.data)
        self.assertEqual(self.product.skus.count(), 1)

    def rule(self):
        response = self.client.post("/api/supplier-capabilities/", {"product": self.product.pk, "supplier": self.a.pk, "name": "24V", "filters": {"voltage": ["24"]}, "characteristics": {"背胶": "3M"}}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def purchase(self, supplier, no):
        response = self.client.post("/api/purchase-orders/", {"exchange_rate": "1", "supplier": supplier.pk, "order_date": "2026-09-15", "currency": "CNY", "items": [{"sku": self.sku.pk, "quantity": 10, "unit_price": "5"}]}, format="json")
        if response.status_code == 201:
            placed = self.client.post(f"/api/purchase-orders/{response.data['id']}/place/", {}, format="json")
            self.assertEqual(placed.status_code, 200, placed.data)
        return response

    def test_candidates_are_dynamic_and_manual_purchase_does_not_create_source(self):
        self.rule()
        self.assertFalse(SupplierSKU.objects.exists())
        pool = self.client.get(f"/api/skus/{self.sku.pk}/supplier-candidates/").data
        self.assertEqual(pool["candidates"][0]["supplier"], self.a.pk)
        self.assertEqual(SupplierSKU.objects.count(), 0)
        for supplier, no in [(self.a, "PA"), (self.b, "PB")]:
            response = self.purchase(supplier, no)
            self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(SupplierSKU.objects.count(), 0)
        item = PurchaseOrderItem.objects.get(purchase_order__supplier=self.a)
        self.assertIsNone(item.supplier_sku)
        self.assertEqual(item.supplier_name_snapshot, self.a.name)
        self.assertEqual(item.supplier_characteristics_snapshot, {})
        self.a.name = "供应商甲新名称"; self.a.save(update_fields=["name"])
        item.refresh_from_db()
        self.assertEqual(item.supplier_name_snapshot, "供应商甲")

    def test_exclusion_wins_over_rules_and_blocks_purchase(self):
        self.rule()
        url = f"/api/skus/{self.sku.pk}/supplier-candidates/"
        self.client.post(url, {"supplier": self.a.pk, "is_allowed": False}, format="json")
        self.assertEqual(self.client.get(url).data["candidates"], [])
        self.assertEqual(self.purchase(self.a, "BLOCKED").status_code, 400)
        self.client.post(url, {"supplier": self.a.pk, "is_allowed": None}, format="json")
        self.assertEqual(len(self.client.get(url).data["candidates"]), 1)

    def test_new_rule_is_not_allowed_to_match_unknown_parameter(self):
        response = self.client.post("/api/supplier-capabilities/", {"product": self.product.pk, "supplier": self.a.pk, "name": "bad", "filters": {"unknown": ["x"]}}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_supplier_source_cannot_be_reparented(self):
        source = SupplierSKU.objects.create(sku=self.sku, supplier=self.a, supplier_sku_code="TEST")
        response = self.client.patch(f"/api/supplier-skus/{source.pk}/", {"supplier": self.b.pk}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_legacy_combined_label_reads_existing_parameter_values(self):
        from crm.services.sku_plans import draft_plan, analyze
        plan = self.product.sku_parameter_plans.get(status="published")
        for definition in plan.definitions:
            if definition["key"] == "color":
                definition["key"] = "color/light"
                definition["name"] = "颜色/发光颜色"
        plan.save()
        draft = draft_plan(self.product)
        result = analyze(draft)
        self.assertEqual(result["missing"], [])
        self.assertEqual(result["groups"][0]["values"][f"{self.category.pk}:color/light"], "red")

    def test_explicit_empty_required_value_is_not_silently_restored(self):
        draft = self.draft()
        draft["assignments"] = {str(self.sku.pk): [{f"{self.category.pk}:voltage": ""}]}
        draft = self.save_draft(draft)
        self.assertTrue(self.action(draft, "analyze").data["missing"])
        self.assertEqual(self.action(draft).status_code, 400)

    def test_batch_creation_rolls_back_every_row_on_duplicate(self):
        before = self.product.skus.count()
        response = self.client.post("/api/skus/batch-create/", {"items": [
            {"product": self.product.pk, "parameter_values": {"voltage": "24", "color": "green"}},
            {"product": self.product.pk, "parameter_values": {"voltage": "24", "color": "red"}},
        ]}, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(self.product.skus.count(), before)

    def test_batch_creation_only_saves_submitted_combinations(self):
        response = self.client.post("/api/skus/batch-create/", {"items": [
            {"product": self.product.pk, "parameter_values": {"voltage": "12", "color": "green"}},
            {"product": self.product.pk, "parameter_values": {"voltage": "24", "color": "blue"}},
        ]}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(self.product.skus.count(), 3)

    def test_removing_all_dimensions_does_not_make_ordinary_values_identity(self):
        self.create_sku("blue")
        draft = self.draft()
        for definition in draft["definitions"]:
            definition["include_in_sku"] = False
        draft = self.save_draft(draft)
        self.assertEqual(self.action(draft).status_code, 200)
        current = self.product.skus.get(active=True)
        from crm.sku_identity import identity_signature
        self.assertEqual(identity_signature(self.product, {"voltage": "different", "color": "different"}), current.identity_signature)
