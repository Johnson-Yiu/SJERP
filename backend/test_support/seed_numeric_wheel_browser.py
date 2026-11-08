"""Seed only minimal, clearly synthetic records for the numeric wheel browser check."""

import django
from decimal import Decimal

django.setup()

from django.conf import settings
from test_support.isolated_runtime import verify_isolated_runtime

verify_isolated_runtime(settings=settings, database_must_exist=True)

from crm.models import Customer, Product, ProductCategory, SKU

category, _ = ProductCategory.objects.get_or_create(name="Wheel Guard Test Category")
product, _ = Product.objects.get_or_create(
    code="WG-TEST-PRD-01",
    defaults={"name": "Wheel Guard Test Product", "category": category},
)
sku, _ = SKU.objects.get_or_create(
    sku="WG-TEST-SKU-01",
    defaults={
        "product": product,
        "specification": "Browser test only",
        "sales_model": "WG-TEST-01",
        "display_name_cn": "滚轮保护测试 SKU",
        "cost_price": Decimal("2.5000"),
        "default_price": Decimal("5.0000"),
    },
)
Customer.objects.get_or_create(
    code="WG-TEST-C-01",
    defaults={"name": "Wheel Guard Test Customer", "country": "测试资料"},
)

print("Seeded one synthetic customer, product and SKU in the verified isolated SQLite database.")
