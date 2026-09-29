from datetime import date

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from crm.models import (
    CategoryAttribute,
    Customer,
    Order,
    OrderItem,
    Product,
    ProductCategory,
    PurchaseOrder,
    PurchaseOrderItem,
    Quote,
    QuoteItem,
    SKU,
    SKUParameterPlan,
    SKUVersion,
    Supplier,
)
from crm.services.sku_plans import baseline, definitions_for


class ProductCategorySkuIdentitySafetyTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.root = ProductCategory.objects.create(name="身份安全根分类")
        self.category = ProductCategory.objects.create(name="身份安全分类", parent=self.root)
        self.other_category = ProductCategory.objects.create(name="身份安全目标分类")
        self.voltage = CategoryAttribute.objects.create(
            category=self.category,
            name="电压",
            key="voltage",
            unit="V",
            include_in_sku=True,
            include_in_sales_model=True,
        )
        self.width = CategoryAttribute.objects.create(
            category=self.category,
            name="宽度",
            key="width",
            unit="mm",
            include_in_sku=True,
        )
        self.product = Product.objects.create(
            code="I1-LEGACY",
            name="历史 SKU 产品",
            sales_model_prefix="LEGACY",
            category=self.category,
        )
        self.sku = SKU.objects.create(
            sku="SKU-I1-LEGACY",
            product=self.product,
            display_name_cn="历史 SKU 产品 24V 8mm",
            description_cn="历史 SKU",
            description_en="Legacy SKU",
            sales_model="LEGACY-24",
            parameter_values={"voltage": "24", "width": "8"},
            sales_model_abbreviations={f"{self.category.pk}:voltage:24": "24"},
        )

    def publish_current_schema(self):
        return SKUParameterPlan.objects.create(
            product=self.product,
            version=1,
            status="published",
            definitions=definitions_for(self.product),
            baseline=baseline(self.product),
        )

    def assert_unfrozen_error(self, response, message):
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        detail = response.data["detail"]
        self.assertEqual(str(detail[0] if isinstance(detail, list) else detail), message)
        self.assertEqual(
            [{key: str(value) for key, value in row.items()} for row in response.data["affected_products"]],
            [{"id": str(self.product.pk), "code": self.product.code, "name": self.product.name}],
        )

    def test_legacy_sku_blocks_structural_category_attribute_changes_but_allows_plain_optional_property(self):
        structural = self.client.patch(
            f"/api/category-attributes/{self.voltage.pk}/",
            {"uppercase": True},
            format="json",
        )
        self.assert_unfrozen_error(
            structural,
            "该参数仍被尚未冻结参数方案的产品使用。请先在相关产品中发布当前 SKU 参数方案，再修改分类参数。",
        )

        added = self.client.post(
            "/api/category-attributes/",
            {"category": self.category.pk, "name": "安装备注", "key": "installation_note"},
            format="json",
        )
        self.assertEqual(added.status_code, status.HTTP_201_CREATED, added.data)
        identity_field = self.client.post(
            "/api/category-attributes/",
            {"category": self.category.pk, "name": "色温", "key": "color", "include_in_sku": True},
            format="json",
        )
        self.assert_unfrozen_error(
            identity_field,
            "该参数仍被尚未冻结参数方案的产品使用。请先在相关产品中发布当前 SKU 参数方案，再修改分类参数。",
        )
        deleted = self.client.delete(f"/api/category-attributes/{self.voltage.pk}/")
        self.assert_unfrozen_error(
            deleted,
            "该参数仍被尚未冻结参数方案的产品使用。请先在相关产品中发布当前 SKU 参数方案，再修改分类参数。",
        )

    def test_attribute_key_category_and_direct_sort_order_are_immutable_or_formal_only(self):
        cases = [
            ({"key": "voltage_v2"}, "key", "参数标识创建后不可修改；如业务含义发生变化，请新增参数并通过 SKU 参数方案处理。"),
            ({"category": self.other_category.pk}, "category", "参数创建后不能更换所属分类；如需调整请新建参数。"),
            ({"sort_order": 5}, "sort_order", "参数排序请使用正式排序操作。"),
        ]
        for payload, field, message in cases:
            with self.subTest(payload=payload):
                response = self.client.patch(f"/api/category-attributes/{self.voltage.pk}/", payload, format="json")
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
                self.assertEqual(response.data[field][0], message)

        reorder = self.client.post(
            "/api/category-attributes/reorder/",
            {"category": self.category.pk, "ids": [self.width.pk, self.voltage.pk], "confirm": True},
            format="json",
        )
        self.assertEqual(reorder.status_code, status.HTTP_200_OK, reorder.data)

    def test_frozen_product_does_not_auto_mutate_when_category_template_changes(self):
        self.publish_current_schema()
        before = (self.sku.sku, self.sku.display_name_cn, self.sku.sales_model, self.sku.parameter_values)
        response = self.client.patch(
            f"/api/category-attributes/{self.voltage.pk}/",
            {"uppercase": True, "unit": "Volt"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.sku.refresh_from_db()
        self.assertEqual(
            (self.sku.sku, self.sku.display_name_cn, self.sku.sales_model, self.sku.parameter_values),
            before,
        )

    def test_unfrozen_product_category_and_category_parent_changes_are_blocked(self):
        product_move = self.client.patch(
            f"/api/products/{self.product.pk}/", {"category": self.other_category.pk}, format="json"
        )
        self.assertEqual(product_move.status_code, status.HTTP_400_BAD_REQUEST, product_move.data)
        self.assertEqual(product_move.data["category"][0], "该产品已有 SKU，请先发布当前 SKU 参数方案以冻结现有参数结构，再调整产品分类。")

        parent_move = self.client.patch(
            f"/api/categories/{self.category.pk}/", {"parent": self.other_category.pk}, format="json"
        )
        self.assert_unfrozen_error(
            parent_move,
            "该分类层级下仍有未冻结 SKU 参数方案的产品，不能直接改变继承关系。",
        )
        same_level_reorder = self.client.post(
            "/api/categories/reorder/",
            {"id": self.category.pk, "parent": self.root.pk, "index": 0},
            format="json",
        )
        self.assertEqual(same_level_reorder.status_code, status.HTTP_200_OK, same_level_reorder.data)

    def test_frozen_product_can_change_categories_without_mutating_sku_identity(self):
        self.publish_current_schema()
        before = (self.sku.sku, self.sku.display_name_cn, self.sku.sales_model, self.sku.parameter_values)
        response = self.client.patch(
            f"/api/products/{self.product.pk}/",
            {"category": self.other_category.pk, "additional_categories": [self.category.pk]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.sku.refresh_from_db()
        self.assertEqual(
            (self.sku.sku, self.sku.display_name_cn, self.sku.sales_model, self.sku.parameter_values),
            before,
        )

    def test_category_delete_is_blocked_for_children_primary_and_additional_product_relations(self):
        child = ProductCategory.objects.create(name="身份安全待删子分类", parent=self.other_category)
        response = self.client.delete(f"/api/categories/{self.other_category.pk}/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertEqual(response.data["detail"], "该分类仍有子分类或关联产品，不能删除；请先调整产品分类关系。")
        child.delete()

        primary = Product.objects.create(code="I1-PRIMARY", name="主分类产品", sales_model_prefix="I1PRIMARY", category=self.other_category)
        response = self.client.delete(f"/api/categories/{self.other_category.pk}/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        primary.delete()

        secondary = Product.objects.create(code="I1-SECONDARY", name="附加分类产品", sales_model_prefix="I1SECONDARY")
        secondary.additional_categories.add(self.other_category)
        response = self.client.delete(f"/api/categories/{self.other_category.pk}/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertEqual(response.data["detail"], "该分类仍有子分类或关联产品，不能删除；请先调整产品分类关系。")

    def test_sales_model_prefix_preview_apply_preserves_code_and_business_snapshots(self):
        customer = Customer.objects.create(code="I1-CUSTOMER", name="身份安全客户")
        supplier = Supplier.objects.create(code="I1", name="身份安全供应商")
        quote = Quote.objects.create(quote_no="I1-Q-001", customer=customer, quote_date=date(2026, 9, 30))
        quote_item = QuoteItem.objects.create(quote=quote, sku=self.sku, quantity=1, unit_price=10)
        order = Order.objects.create(order_no="I1-SO-001", customer=customer, order_date=date(2026, 9, 30), status="confirmed")
        order_item = OrderItem.objects.create(order=order, sku=self.sku, quantity=1, unit_price=10)
        purchase = PurchaseOrder.objects.create(purchase_no="I1-PO-001", supplier=supplier, order_date=date(2026, 9, 30))
        purchase_item = PurchaseOrderItem.objects.create(purchase_order=purchase, sku=self.sku, quantity=1, unit_price=5)
        snapshots = (
            quote_item.sales_model_snapshot,
            order_item.sales_model_snapshot,
            purchase_item.sales_model_snapshot,
        )
        before_code = self.sku.sku

        preview = self.client.post(
            f"/api/products/{self.product.pk}/sales-model-prefix-preview/",
            {"sales_model_prefix": "NEXT"},
            format="json",
        )
        self.assertEqual(preview.status_code, status.HTTP_200_OK, preview.data)
        self.assertEqual(preview.data["old_prefix"], "LEGACY")
        self.assertEqual(preview.data["new_prefix"], "NEXT")
        self.assertEqual(preview.data["affected_skus"][0]["old_sales_model"], "LEGACY-24")
        self.assertEqual(preview.data["affected_skus"][0]["new_sales_model"], "NEXT-24")
        self.sku.refresh_from_db()
        self.assertEqual(self.sku.sales_model, "LEGACY-24")
        self.assertFalse(SKUVersion.objects.filter(sku=self.sku).exists())

        ordinary = self.client.patch(
            f"/api/products/{self.product.pk}/", {"sales_model_prefix": "NEXT"}, format="json"
        )
        self.assertEqual(ordinary.status_code, status.HTTP_400_BAD_REQUEST, ordinary.data)

        applied = self.client.post(
            f"/api/products/{self.product.pk}/sales-model-prefix-apply/",
            {"sales_model_prefix": "NEXT", "baseline": preview.data["baseline"]},
            format="json",
        )
        self.assertEqual(applied.status_code, status.HTTP_200_OK, applied.data)
        self.product.refresh_from_db()
        self.sku.refresh_from_db()
        quote_item.refresh_from_db(); order_item.refresh_from_db(); purchase_item.refresh_from_db()
        self.assertEqual(self.product.sales_model_prefix, "NEXT")
        self.assertEqual(self.sku.sku, before_code)
        self.assertEqual(self.sku.sales_model, "NEXT-24")
        self.assertEqual(SKUVersion.objects.get(sku=self.sku).sales_model_snapshot, "LEGACY-24")
        self.assertEqual(
            (quote_item.sales_model_snapshot, order_item.sales_model_snapshot, purchase_item.sales_model_snapshot),
            snapshots,
        )

    def test_sales_model_prefix_conflict_is_rejected_without_partial_writes(self):
        other = Product.objects.create(code="I1-CONFLICT", name="冲突产品", sales_model_prefix="OTHER", category=self.other_category)
        SKU.objects.create(
            sku="SKU-I1-CONFLICT",
            product=other,
            display_name_cn="冲突 SKU",
            description_cn="冲突 SKU",
            description_en="Conflict SKU",
            sales_model="NEXT-24",
        )
        response = self.client.post(
            f"/api/products/{self.product.pk}/sales-model-prefix-preview/",
            {"sales_model_prefix": "NEXT"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.product.refresh_from_db(); self.sku.refresh_from_db()
        self.assertEqual(self.product.sales_model_prefix, "LEGACY")
        self.assertEqual(self.sku.sales_model, "LEGACY-24")
        self.assertFalse(SKUVersion.objects.filter(sku=self.sku).exists())

    def test_product_without_sku_can_change_sales_model_prefix_through_normal_patch(self):
        product = Product.objects.create(
            code="I1-NO-SKU",
            name="无 SKU 产品",
            sales_model_prefix="NOSKU",
            category=self.other_category,
        )
        response = self.client.patch(
            f"/api/products/{product.pk}/", {"sales_model_prefix": "NOSKUNEXT"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        product.refresh_from_db()
        self.assertEqual(product.sales_model_prefix, "NOSKUNEXT")

    def test_product_customers_only_counts_formal_orders(self):
        customer = Customer.objects.create(code="I1-CUSTOMERS", name="正式客户")
        for suffix, status_value in (("D", "draft"), ("C", "confirmed"), ("X", "cancelled")):
            order = Order.objects.create(
                order_no=f"I1-CUSTOMERS-{suffix}",
                customer=customer,
                order_date=date(2026, 9, 30),
                status=status_value,
            )
            OrderItem.objects.create(order=order, sku=self.sku, quantity=1, unit_price=10)
        response = self.client.get(f"/api/products/{self.product.pk}/customers/")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data[0]["order_count"], 1)
        self.assertEqual(str(response.data[0]["sales"]), "10")
