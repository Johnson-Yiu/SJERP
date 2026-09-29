"""Shared guards around category templates and frozen SKU parameter schemas."""

from django.db.models import Q

from crm.models import Product, ProductCategory


UNFROZEN_SCHEMA_MESSAGE = "该参数仍被尚未冻结参数方案的产品使用。请先在相关产品中发布当前 SKU 参数方案，再修改分类参数。"
UNFROZEN_PRODUCT_CATEGORY_MESSAGE = "该产品已有 SKU，请先发布当前 SKU 参数方案以冻结现有参数结构，再调整产品分类。"
UNFROZEN_CATEGORY_HIERARCHY_MESSAGE = "该分类层级下仍有未冻结 SKU 参数方案的产品，不能直接改变继承关系。"


def product_has_frozen_sku_schema(product):
    """Whether a SKU-bearing product has a published parameter plan."""
    return product.skus.exists() and product.sku_parameter_plans.filter(status="published").exists()


def product_has_unfrozen_sku_schema(product):
    """Legacy/transitional products with SKUs that still read live templates."""
    return product.skus.exists() and not product.sku_parameter_plans.filter(status="published").exists()


def category_scope(category):
    """Return one category and every descendant whose inherited template changes."""
    scope = {category.pk}
    pending = [category.pk]
    while pending:
        children = list(ProductCategory.objects.filter(parent_id__in=pending).values_list("pk", flat=True))
        pending = [child for child in children if child not in scope]
        scope.update(pending)
    return scope


def products_using_category_scope(category):
    scope = category_scope(category)
    return Product.objects.filter(
        Q(category_id__in=scope) | Q(additional_categories__in=scope)
    ).distinct().prefetch_related("skus", "sku_parameter_plans")


def unfrozen_products_using_category_scope(category):
    return [product for product in products_using_category_scope(category) if product_has_unfrozen_sku_schema(product)]


def affected_product_payload(products):
    return [
        {"id": product.pk, "code": product.code, "name": product.name}
        for product in products
    ]


def unfrozen_schema_error(products, message=UNFROZEN_SCHEMA_MESSAGE):
    return {"detail": message, "affected_products": affected_product_payload(products)}
