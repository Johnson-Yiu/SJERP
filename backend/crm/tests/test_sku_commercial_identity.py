from datetime import date

from rest_framework import status
from rest_framework.test import APIClient

from django.test import TestCase

from crm.models import CategoryAttribute, Contact, Customer, Order, Product, ProductCategory, Quote, SKU


class SkuCommercialIdentityTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = Customer.objects.create(code="C-SKU-ID", name="Identity Buyer", country="Germany")
        Contact.objects.create(customer=self.customer, name="Buyer Contact", is_primary=True)
        category = ProductCategory.objects.create(name="COB Strip")
        CategoryAttribute.objects.create(category=category, name="电压", key="voltage", unit="V", include_in_sku=True)
        CategoryAttribute.objects.create(category=category, name="宽度", key="width", unit="mm", include_in_sku=True)
        product = Product.objects.create(code="P-SKU-ID", name="COB灯带", name_en="COB LED Strip", sales_model_prefix="COB320", category=category)
        self.product = product

    def create_sku(self, **payload):
        defaults = {
            "product": self.product.id,
            "specification": "24V / 8mm",
            "parameter_values": {"voltage": "24", "width": "8"},
            "product_details": [{"model": "A1"}],
            "sales_model": "CB8-24-A1",
            "unit": "reel",
        }
        defaults.update(payload)
        response = self.client.post("/api/skus/", defaults, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        return SKU.objects.get(pk=response.data["id"]), response

    def test_new_sku_gets_separate_id_display_and_commercial_fields(self):
        sku, response = self.create_sku()

        self.assertTrue(sku.sku.startswith("SKU-"))
        self.assertEqual(response.data["sku_code"], sku.sku)
        self.assertEqual(response.data["sales_model"], "CB8-24-A1")
        self.assertIn("COB灯带", response.data["display_name_cn"])
        self.assertIn("24V", response.data["display_name_cn"])
        self.assertTrue(response.data["description_cn"])
        self.assertIn("COB LED Strip", response.data["description_en"])

    def test_sales_model_is_generated_from_enabled_category_attributes(self):
        attribute = CategoryAttribute.objects.get(key="voltage")
        attribute.include_in_sales_model = True
        attribute.save(update_fields=["include_in_sales_model"])

        sku, response = self.create_sku(sales_model=None, sales_model_abbreviations={f"{self.product.category_id}:voltage:24": "6K"})

        self.assertEqual(sku.sales_model, "COB320-6K-1")
        self.assertEqual(response.data["sales_model"], "COB320-6K-1")

    def test_generated_sales_model_increments_when_the_abbreviation_is_repeated(self):
        attribute = CategoryAttribute.objects.get(key="voltage")
        attribute.include_in_sales_model = True
        attribute.save(update_fields=["include_in_sales_model"])
        payload = {"sales_model": None, "sales_model_abbreviations": {f"{self.product.category_id}:voltage:24": "6K"}}

        first, _ = self.create_sku(**payload)
        second, _ = self.create_sku(**payload)

        self.assertEqual(first.sales_model, "COB320-6K-1")
        self.assertEqual(second.sales_model, "COB320-6K-2")

    def test_same_category_abbreviation_suggestions_are_reused_across_products(self):
        attribute = CategoryAttribute.objects.get(key="voltage")
        attribute.include_in_sales_model = True
        attribute.save(update_fields=["include_in_sales_model"])
        self.create_sku(sales_model=None, sales_model_abbreviations={f"{self.product.category_id}:voltage:24": "6K"})
        sibling = Product.objects.create(code="P-SKU-SIBLING", name="同类产品", sales_model_prefix="SIBLING1", category=self.product.category)
        Product.objects.create(code="P-SKU-OTHER", name="其他分类产品", sales_model_prefix="OTHER1", category=ProductCategory.objects.create(name="Other"))

        response = self.client.get("/api/skus/sales-model-abbreviations/", {"category": sibling.category_id})

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["abbreviations"][f"{self.product.category_id}:voltage:24"], "6K")

    def test_legacy_detail_model_and_dimensions_are_not_saved_on_sku(self):
        sku, _ = self.create_sku(product_details=[{"model": "A1", "unit_weight": 0.2, "length": 40, "width": 30, "height": 20}])

        self.assertNotIn("model", sku.product_details[0])
        self.assertFalse({"length", "width", "height"}.intersection(sku.product_details[0]))
        self.assertEqual(sku.product_details[0]["unit_weight"], 0.2)

    def test_parameter_change_regenerates_display_name_but_not_internal_or_sales_identity(self):
        sku, created = self.create_sku()
        original_code = sku.sku
        original_model = sku.sales_model

        response = self.client.patch(
            f"/api/skus/{sku.id}/",
            {"parameter_values": {"voltage": "24", "width": "10"}, "specification": "24V / 10mm"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        sku.refresh_from_db()
        self.assertEqual(sku.sku, original_code)
        self.assertEqual(sku.sales_model, original_model)
        self.assertIn("10mm", sku.display_name_cn)

    def test_quote_and_order_keep_commercial_snapshots_after_sku_changes(self):
        sku, _ = self.create_sku(description_en="COB LED Strip, 24V, 8mm, CRI>=90")
        quote_response = self.client.post(
            "/api/quotes/",
            {
                "customer": self.customer.id,
                "quote_date": "2026-08-23",
                "items": [{"sku": sku.id, "quantity": "2", "unit_price": "10"}],
            },
            format="json",
        )
        self.assertEqual(quote_response.status_code, status.HTTP_201_CREATED, quote_response.data)
        item = Quote.objects.get(pk=quote_response.data["id"]).items.get()
        self.assertEqual(item.sales_model_snapshot, "CB8-24-A1")
        self.assertEqual(item.description, "COB LED Strip, 24V, 8mm, CRI>=90")

        sku.description_en = "COB LED Strip, 24V, 8mm, CRI>=95"
        sku.parameter_values = {"voltage": "24", "width": "10"}
        sku.specification = "24V / 10mm"
        sku.save()

        pi = self.client.get(f"/api/quotes/{item.quote_id}/pi-data/")
        self.assertEqual(pi.status_code, status.HTTP_200_OK)
        self.assertEqual(pi.data["products"][0]["model"], "CB8-24-A1")
        self.assertEqual(pi.data["products"][0]["description"], "COB LED Strip, 24V, 8mm, CRI>=90")

        draft = self.client.get(f"/api/quotes/{item.quote_id}/order-draft/")
        self.assertEqual(draft.status_code, status.HTTP_200_OK)
        saved = self.client.post("/api/orders/", draft.data, format="json")
        self.assertEqual(saved.status_code, status.HTTP_201_CREATED, saved.data)
        order_item = Order.objects.get(pk=saved.data["id"]).items.get()
        self.assertEqual(order_item.sales_model_snapshot, "CB8-24-A1")
        self.assertEqual(order_item.description_snapshot, "COB LED Strip, 24V, 8mm, CRI>=90")

    def test_quote_line_can_override_model_without_changing_sku(self):
        sku, _ = self.create_sku()
        response = self.client.post(
            "/api/quotes/",
            {
                "customer": self.customer.id,
                "quote_date": date(2026, 8, 23).isoformat(),
                "items": [{"sku": sku.id, "sales_model_snapshot": "CL-1024", "quantity": "1", "unit_price": "5", "description": "Customer description"}],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        item = Quote.objects.get(pk=response.data["id"]).items.get()
        self.assertEqual(item.sales_model_snapshot, "CL-1024")
        self.assertEqual(item.sku_id, sku.id)
        self.assertEqual(SKU.objects.get(pk=sku.id).sales_model, "CB8-24-A1")

    def test_sku_search_matches_display_name_sales_model_and_code(self):
        sku, _ = self.create_sku()
        for query in ("COB灯带", "CB8-24-A1", sku.sku):
            with self.subTest(query=query):
                response = self.client.get("/api/skus/", {"search": query})
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertIn(sku.id, [row["id"] for row in response.data["results"]])
