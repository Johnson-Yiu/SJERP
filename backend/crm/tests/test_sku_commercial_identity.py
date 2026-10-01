from datetime import date

from rest_framework import status
from rest_framework.test import APIClient

from django.core.exceptions import ValidationError
from django.test import TestCase

from crm.models import CategoryAttribute, Contact, Customer, InventoryMovement, Order, OrderItem, Product, ProductCategory, PurchaseOrder, PurchaseOrderItem, Quote, QuoteItem, SKU, SKUVersion, Supplier


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

    def test_sku_category_names_include_full_hierarchy(self):
        root = ProductCategory.objects.create(name="灯具")
        branch = ProductCategory.objects.create(name="户外灯", parent=root)
        leaf = ProductCategory.objects.create(name="投光灯", parent=branch)
        product = Product.objects.create(
            code="P-CATEGORY-PATH",
            name="投光灯产品",
            sales_model_prefix="FLOOD",
            category=leaf,
        )
        sku = SKU.objects.create(sku="SKU-CATEGORY-PATH", product=product, sales_model="FLOOD-1")

        response = self.client.get(f"/api/skus/{sku.id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["category_names"], ["灯具 / 户外灯 / 投光灯"])

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

        self.assertEqual(sku.sales_model, "COB320-6K")
        self.assertEqual(response.data["sales_model"], "COB320-6K")

    def test_required_category_attribute_is_enforced_for_create_and_update(self):
        attribute = CategoryAttribute.objects.get(key="voltage")
        attribute.required = True
        attribute.save(update_fields=["required"])

        response = self.client.post(
            "/api/skus/",
            {
                "product": self.product.id,
                "parameter_values": {"width": "8"},
                "unit": "reel",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertIn("parameter_values", response.data)

        sku, _ = self.create_sku()
        response = self.client.patch(
            f"/api/skus/{sku.id}/",
            {
                "parameter_values": {"width": "8"},
                "identity_change_confirmed": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertIn("parameter_values", response.data)

    def test_generated_sales_model_rejects_collision_when_the_abbreviation_is_repeated(self):
        attribute = CategoryAttribute.objects.get(key="voltage")
        attribute.include_in_sales_model = True
        attribute.save(update_fields=["include_in_sales_model"])
        payload = {"sales_model": None, "sales_model_abbreviations": {f"{self.product.category_id}:voltage:24": "6K"}}

        first, _ = self.create_sku(**payload)
        second = self.client.post("/api/skus/", {**payload, "product": self.product.pk, "parameter_values": {"voltage": "24", "width": "10"}, "specification": "24V / 10mm"}, format="json")

        self.assertEqual(first.sales_model, "COB320-6K")
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST, second.data)
        self.assertIn("duplicate_sku", second.data)
        self.assertEqual(SKU.objects.filter(product=self.product).count(), 1)

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

    def test_parameter_change_requires_confirmation_and_keeps_existing_name(self):
        sku, _ = self.create_sku()
        original_code = sku.sku
        original_model = sku.sales_model
        original_name = sku.display_name_cn

        response = self.client.patch(
            f"/api/skus/{sku.id}/",
            {"parameter_values": {"voltage": "24", "width": "10"}, "specification": "24V / 10mm"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        sku.refresh_from_db()
        self.assertEqual(sku.sku, original_code)
        self.assertEqual(sku.sales_model, original_model)
        self.assertEqual(sku.display_name_cn, original_name)

    def test_confirmed_parameter_change_refreshes_the_existing_sku(self):
        sku, _ = self.create_sku()
        original_name = sku.display_name_cn
        original_signature = sku.identity_signature

        response = self.client.patch(
            f"/api/skus/{sku.id}/",
            {
                "parameter_values": {"voltage": "24", "width": "10"},
                "specification": "24V / 10mm",
                "identity_change_confirmed": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        sku.refresh_from_db()
        self.assertNotEqual(sku.display_name_cn, original_name)
        self.assertNotEqual(sku.identity_signature, original_signature)
        version = SKUVersion.objects.get(sku=sku)
        self.assertEqual(version.display_name_cn_snapshot, original_name)
        self.assertEqual(version.sales_model_snapshot, "CB8-24-A1")
        self.assertIn("parameter_values", version.changed_fields)

    def test_quote_and_order_history_block_parameter_identity_changes_but_allow_display_renames(self):
        quoted, _ = self.create_sku()
        quote = Quote.objects.create(quote_no="QT-SKU-HISTORY", customer=self.customer, quote_date=date(2026, 8, 23))
        quote_item = QuoteItem.objects.create(quote=quote, sku=quoted, quantity="2", unit_price="10")
        quote_snapshot = (quote_item.product_name_snapshot, quote_item.sales_model_snapshot, quote_item.unit_snapshot)

        quote_change = self.client.patch(f"/api/skus/{quoted.pk}/", {
            "parameter_values": {"voltage": "12", "width": "8"},
            "specification": "12V / 8mm",
            "identity_change_confirmed": True,
        }, format="json")
        self.assertEqual(quote_change.status_code, status.HTTP_400_BAD_REQUEST, quote_change.data)
        self.assertEqual(
            quote_change.data["non_field_errors"][0],
            "该 SKU 已存在业务历史，不能直接修改身份参数；如产品规格发生实质变化，请新建 SKU 或通过正式 SKU 参数演化流程处理。",
        )
        quoted.refresh_from_db()
        quote_item.refresh_from_db()
        self.assertEqual(quoted.parameter_values, {"voltage": "24", "width": "8"})
        self.assertEqual((quote_item.product_name_snapshot, quote_item.sales_model_snapshot, quote_item.unit_snapshot), quote_snapshot)

        order_sku, _ = self.create_sku(
            parameter_values={"voltage": "24", "width": "10"},
            specification="24V / 10mm",
            sales_model="CB8-24-A2",
        )
        order = Order.objects.create(order_no="SO-SKU-HISTORY", customer=self.customer, order_date=date(2026, 8, 23), status="confirmed")
        order_item = OrderItem.objects.create(order=order, sku=order_sku, quantity="3", unit_price="12")
        order_snapshot = (order_item.display_name_snapshot, order_item.sales_model_snapshot, order_item.unit_snapshot)

        order_change = self.client.put(f"/api/skus/{order_sku.pk}/", {
            "product": self.product.pk,
            "unit": order_sku.unit,
            "parameter_values": {"voltage": "12", "width": "10"},
            "specification": "12V / 10mm",
            "identity_change_confirmed": True,
        }, format="json")
        self.assertEqual(order_change.status_code, status.HTTP_400_BAD_REQUEST, order_change.data)
        self.assertEqual(order_change.data["non_field_errors"][0], quote_change.data["non_field_errors"][0])
        order_sku.refresh_from_db()
        order_item.refresh_from_db()
        self.assertEqual(order_sku.parameter_values, {"voltage": "24", "width": "10"})
        self.assertEqual((order_item.display_name_snapshot, order_item.sales_model_snapshot, order_item.unit_snapshot), order_snapshot)

        display_change = self.client.patch(f"/api/skus/{quoted.pk}/", {
            "display_name_cn": "历史产品 24V 显示名称更新",
            "sales_model": "CB8-24-A1-NEW",
            "identity_change_confirmed": True,
        }, format="json")
        self.assertEqual(display_change.status_code, status.HTTP_200_OK, display_change.data)
        self.assertEqual(SKUVersion.objects.filter(sku=quoted).count(), 1)
        quote_item.refresh_from_db()
        self.assertEqual((quote_item.product_name_snapshot, quote_item.sales_model_snapshot, quote_item.unit_snapshot), quote_snapshot)

    def test_parameter_change_with_quote_history_is_rejected_and_preserves_snapshot(self):
        voltage = CategoryAttribute.objects.get(key="voltage")
        voltage.include_in_sales_model = True
        voltage.save(update_fields=["include_in_sales_model"])
        sku, _ = self.create_sku(sales_model=None)
        original_code = sku.sku
        original_name = sku.display_name_cn
        original_model = sku.sales_model
        quote_response = self.client.post(
            "/api/quotes/",
            {"customer": self.customer.id, "quote_date": "2026-08-23", "items": [{"sku": sku.id, "quantity": "1", "unit_price": "10"}]},
            format="json",
        )
        self.assertEqual(quote_response.status_code, status.HTTP_201_CREATED, quote_response.data)

        response = self.client.patch(
            f"/api/skus/{sku.id}/",
            {"parameter_values": {"voltage": "12", "width": "8"}, "specification": "12V / 8mm", "identity_change_confirmed": True},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        sku.refresh_from_db()
        self.assertEqual(sku.sku, original_code)
        self.assertEqual(sku.display_name_cn, original_name)
        self.assertEqual(sku.sales_model, original_model)
        self.assertEqual(sku.parameter_values, {"voltage": "24", "width": "8"})
        self.assertFalse(SKUVersion.objects.filter(sku=sku).exists())
        item = Quote.objects.get(pk=quote_response.data["id"]).items.get()
        self.assertEqual(item.product_name_snapshot, original_name)
        self.assertEqual(item.sales_model_snapshot, original_model)

    def test_attribute_rename_keeps_identity_signature_stable(self):
        sku, _ = self.create_sku()
        original_signature = sku.identity_signature

        attribute = CategoryAttribute.objects.get(key="voltage")
        attribute.name = "输入电压"
        attribute.save()

        response = self.client.patch(
            f"/api/skus/{sku.id}/",
            {"parameter_values": {"voltage": "24", "width": "8"}},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        sku.refresh_from_db()
        self.assertEqual(sku.identity_signature, original_signature)

    def test_abbreviation_lookup_is_case_insensitive_and_persisted_canonically(self):
        attribute = CategoryAttribute.objects.get(key="voltage")
        attribute.include_in_sales_model = True
        attribute.save()

        sku, _ = self.create_sku(
            sales_model=None,
            parameter_values={"voltage": "White", "width": "8"},
            sales_model_abbreviations={f"{self.product.category_id}:Voltage: white": "cw"},
        )

        self.assertEqual(sku.sales_model, "COB320-CW")
        self.assertEqual(sku.sales_model_abbreviations, {f"{self.product.category_id}:voltage:white": "CW"})

    def test_category_attribute_reorder_refreshes_identity_after_preview_confirmation(self):
        voltage = CategoryAttribute.objects.get(key="voltage")
        width = CategoryAttribute.objects.get(key="width")
        voltage.include_in_sales_model = True
        width.include_in_sales_model = True
        voltage.save(update_fields=["include_in_sales_model"])
        width.save(update_fields=["include_in_sales_model"])
        abbreviations = {
            f"{self.product.category_id}:voltage:24": "24V",
            f"{self.product.category_id}:width:8": "8M",
        }
        sku, _ = self.create_sku(sales_model=None, sales_model_abbreviations=abbreviations)
        original_name, original_model = sku.display_name_cn, sku.sales_model
        quote_response = self.client.post(
            "/api/quotes/",
            {
                "customer": self.customer.id,
                "quote_date": "2026-09-30",
                "items": [{"sku": sku.id, "quantity": "1", "unit_price": "10"}],
            },
            format="json",
        )
        self.assertEqual(quote_response.status_code, status.HTTP_201_CREATED, quote_response.data)
        quote_item = Quote.objects.get(pk=quote_response.data["id"]).items.get()
        order = Order.objects.create(
            order_no="SO-SKU-REORDER-SNAPSHOT",
            customer=self.customer,
            order_date=date(2026, 9, 30),
            status="confirmed",
        )
        order_item = order.items.create(sku=sku, quantity=1, unit_price=10)
        historical_snapshots = (
            quote_item.sku_code_snapshot,
            quote_item.sales_model_snapshot,
            quote_item.product_name_snapshot,
            order_item.sku_code_snapshot,
            order_item.sales_model_snapshot,
            order_item.display_name_snapshot,
        )
        reordered_ids = [width.id, voltage.id]

        preview = self.client.post(
            "/api/category-attributes/reorder/",
            {"category": self.product.category_id, "ids": reordered_ids, "preview": True},
            format="json",
        )
        self.assertEqual(preview.status_code, status.HTTP_200_OK, preview.data)
        self.assertEqual(preview.data["affected_skus"], 1)
        self.assertEqual(SKU.objects.get(pk=sku.pk).display_name_cn, original_name)

        response = self.client.post(
            "/api/category-attributes/reorder/",
            {"category": self.product.category_id, "ids": reordered_ids, "confirm": True},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        sku.refresh_from_db()
        self.assertNotEqual(sku.display_name_cn, original_name)
        self.assertNotEqual(sku.sales_model, original_model)
        self.assertEqual(sku.sku, "SKU-000001")
        version = SKUVersion.objects.get(sku=sku)
        self.assertEqual(version.display_name_cn_snapshot, original_name)
        self.assertEqual(version.sales_model_snapshot, original_model)
        self.assertIn("分类属性排序变更", version.change_reason)
        quote_item.refresh_from_db()
        order_item.refresh_from_db()
        self.assertEqual(
            (
                quote_item.sku_code_snapshot,
                quote_item.sales_model_snapshot,
                quote_item.product_name_snapshot,
                order_item.sku_code_snapshot,
                order_item.sales_model_snapshot,
                order_item.display_name_snapshot,
            ),
            historical_snapshots,
        )

    def test_confirmed_parameter_change_is_blocked_when_identity_duplicates_another_sku(self):
        first, _ = self.create_sku()
        second, _ = self.create_sku(parameter_values={"voltage": "24", "width": "10"}, specification="24V / 10mm", sales_model="CB8-24-A2")
        original_name, original_model = second.display_name_cn, second.sales_model

        response = self.client.patch(
            f"/api/skus/{second.id}/",
            {"parameter_values": first.parameter_values, "specification": first.specification, "identity_change_confirmed": True},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertIn("duplicate_sku", response.data)
        second.refresh_from_db()
        self.assertEqual(second.display_name_cn, original_name)
        self.assertEqual(second.sales_model, original_model)
        self.assertFalse(SKUVersion.objects.filter(sku=second).exists())

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

    def test_sku_code_is_read_only_after_creation(self):
        sku, _ = self.create_sku()
        response = self.client.patch(f"/api/skus/{sku.id}/", {"sku": "USER-EDITED"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        sku.refresh_from_db()
        self.assertNotEqual(sku.sku, "USER-EDITED")

    def test_model_rejects_direct_sku_code_change(self):
        sku, _ = self.create_sku()
        sku.sku = "USER-EDITED"
        with self.assertRaises(ValidationError):
            sku.save()

    def test_manual_sales_model_persists_and_creates_a_version(self):
        sku, _ = self.create_sku()
        response = self.client.patch(f"/api/skus/{sku.id}/", {"sales_model": "COB08-24-WW"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        response = self.client.patch(f"/api/skus/{sku.id}/", {"sales_model": "COB08-24-WW", "identity_change_confirmed": True}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        sku.refresh_from_db()
        self.assertEqual(sku.sales_model, "COB08-24-WW")
        version = SKUVersion.objects.get(sku=sku)
        self.assertEqual(version.sales_model_snapshot, "CB8-24-A1")
        self.assertIn("sales_model", version.changed_fields)

    def test_description_change_creates_version_but_price_change_does_not(self):
        sku, _ = self.create_sku()
        response = self.client.patch(f"/api/skus/{sku.id}/", {"description_en": "New commercial description"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(SKUVersion.objects.filter(sku=sku).count(), 1)
        response = self.client.patch(f"/api/skus/{sku.id}/", {"default_price": "99.0000"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(SKUVersion.objects.filter(sku=sku).count(), 1)

    def test_old_sales_model_search_returns_current_sku_with_historical_marker(self):
        sku, _ = self.create_sku()
        self.client.patch(f"/api/skus/{sku.id}/", {"sales_model": "COB08-24-12W", "identity_change_confirmed": True}, format="json")
        response = self.client.get("/api/skus/", {"search": "CB8-24-A1"})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        row = next(row for row in response.data["results"] if row["id"] == sku.id)
        self.assertEqual(row["sales_model"], "COB08-24-12W")
        self.assertTrue(row["historical_matches"])

    def test_duplicate_product_parameter_signature_is_rejected_but_different_values_work(self):
        self.create_sku()
        duplicate = self.client.post("/api/skus/", {"product": self.product.id, "parameter_values": {"voltage": "24", "width": "8"}, "specification": "24V / 8mm", "sales_model": "DIFFERENT"}, format="json")
        self.assertEqual(duplicate.status_code, status.HTTP_400_BAD_REQUEST)
        different = self.client.post("/api/skus/", {"product": self.product.id, "parameter_values": {"voltage": "24", "width": "10"}, "specification": "24V / 10mm", "sales_model": "DIFFERENT"}, format="json")
        self.assertEqual(different.status_code, status.HTTP_201_CREATED, different.data)

    def test_purchase_and_inventory_store_commercial_snapshots(self):
        sku, _ = self.create_sku()
        order = Order.objects.create(order_no="SO-SKU-SNAPSHOT", customer=self.customer, order_date=date(2026, 8, 23))
        supplier = Supplier.objects.create(name="SKU Snapshot Supplier", code="SS")
        purchase = PurchaseOrder.objects.create(purchase_no="PO-SKU-SNAPSHOT", supplier=supplier, order=order, order_date=date(2026, 8, 23))
        item = PurchaseOrderItem.objects.create(purchase_order=purchase, sku=sku, quantity="1", unit_price="5")
        movement = InventoryMovement.objects.create(movement_no="IM-SKU-SNAPSHOT", movement_date=date(2026, 8, 23), type="adjust_in", sku=sku, quantity="1")
        self.assertEqual(item.sales_model_snapshot, sku.sales_model)
        self.assertEqual(item.sku_code_snapshot, sku.sku)
        self.assertEqual(movement.sales_model_snapshot, sku.sales_model)
        self.assertEqual(movement.sku_code_snapshot, sku.sku)

    def test_purchase_order_item_history_blocks_parameter_identity_change(self):
        sku, _ = self.create_sku()
        supplier = Supplier.objects.create(name="SKU Purchase History Supplier", code="SH")
        purchase = PurchaseOrder.objects.create(
            purchase_no="PO-SKU-IDENTITY-HISTORY",
            supplier=supplier,
            order_date=date(2026, 8, 23),
        )
        item = PurchaseOrderItem.objects.create(
            purchase_order=purchase,
            sku=sku,
            quantity="1",
            unit_price="5",
        )
        original_identity = (sku.sku, sku.parameter_values, sku.specification)
        original_snapshot = (item.sku_code_snapshot, item.sales_model_snapshot)

        response = self.client.put(f"/api/skus/{sku.pk}/", {
            "product": sku.product_id,
            "unit": sku.unit,
            "parameter_values": {"voltage": "12", "width": "8"},
            "specification": "12V / 8mm",
            "identity_change_confirmed": True,
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertEqual(
            response.data["non_field_errors"][0],
            "该 SKU 已存在业务历史，不能直接修改身份参数；如产品规格发生实质变化，请新建 SKU 或通过正式 SKU 参数演化流程处理。",
        )
        sku.refresh_from_db()
        item.refresh_from_db()
        self.assertEqual((sku.sku, sku.parameter_values, sku.specification), original_identity)
        self.assertEqual((item.sku_code_snapshot, item.sales_model_snapshot), original_snapshot)
        self.assertFalse(SKUVersion.objects.filter(sku=sku).exists())

    def test_inventory_movement_history_blocks_parameter_identity_change(self):
        sku, _ = self.create_sku()
        movement = InventoryMovement.objects.create(
            movement_no="IM-SKU-IDENTITY-HISTORY",
            movement_date=date(2026, 8, 23),
            type="adjust_in",
            sku=sku,
            quantity="1",
        )
        original_identity = (sku.sku, sku.parameter_values, sku.specification)
        original_snapshot = (movement.sku_code_snapshot, movement.sales_model_snapshot)

        response = self.client.patch(f"/api/skus/{sku.pk}/", {
            "parameter_values": {"voltage": "12", "width": "8"},
            "specification": "12V / 8mm",
            "identity_change_confirmed": True,
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertEqual(
            response.data["non_field_errors"][0],
            "该 SKU 已存在业务历史，不能直接修改身份参数；如产品规格发生实质变化，请新建 SKU 或通过正式 SKU 参数演化流程处理。",
        )
        sku.refresh_from_db()
        movement.refresh_from_db()
        self.assertEqual((sku.sku, sku.parameter_values, sku.specification), original_identity)
        self.assertEqual((movement.sku_code_snapshot, movement.sales_model_snapshot), original_snapshot)
        self.assertFalse(SKUVersion.objects.filter(sku=sku).exists())

    def test_referenced_sku_cannot_be_deleted_but_can_be_disabled(self):
        sku, _ = self.create_sku()
        InventoryMovement.objects.create(movement_no="IM-SKU-PROTECT", movement_date=date(2026, 8, 23), type="adjust_in", sku=sku, quantity="1")
        response = self.client.delete(f"/api/skus/{sku.id}/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        response = self.client.patch(f"/api/skus/{sku.id}/", {"active": False}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertFalse(SKU.objects.get(pk=sku.pk).active)

    def test_unreferenced_sku_can_only_be_disabled(self):
        sku, _ = self.create_sku()
        response = self.client.delete(f"/api/skus/{sku.id}/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertTrue(SKU.objects.filter(pk=sku.pk).exists())
