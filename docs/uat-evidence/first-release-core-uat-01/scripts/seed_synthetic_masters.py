"""Seed master data for the isolated 2026-11-06 core UAT database only."""

import json
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import transaction
from django.utils import timezone

from crm.models import (
    Contact,
    Customer,
    FollowUp,
    Product,
    ProductCategory,
    SKU,
    Supplier,
    SupplierSKU,
)
from crm.payment_terms import default_payment_terms


worktree_root = Path.cwd().resolve()
database = settings.DATABASES["default"]
database_path = Path(str(database.get("NAME", ""))).resolve()
expected_database = (worktree_root / "backend" / "db.sqlite3").resolve()
if (
    settings.APP_STAGE != "development"
    or not settings.DEBUG
    or not settings.DEVELOPMENT_SUPERADMIN
    or settings.RBAC_ENFORCEMENT
    or database.get("ENGINE") != "django.db.backends.sqlite3"
    or database_path != expected_database
):
    raise ImproperlyConfigured("Synthetic master seeding is restricted to this worktree's development SQLite database.")

tag = "FRUAT-20261106"
today = timezone.localdate()

with transaction.atomic():
    customer, _ = Customer.objects.get_or_create(
        code=tag,
        defaults={
            "name": f"{tag} 合成客户 GmbH",
            "country": "Germany",
            "address": "Synthetic UAT address; not a real entity.",
            "source": "合成首发 UAT",
            "status": "opportunity",
        },
    )
    contact, _ = Contact.objects.get_or_create(
        customer=customer,
        email="buyer@uat.invalid",
        defaults={"name": "Synthetic Buyer", "title": "UAT only", "is_primary": True},
    )
    follow_up, _ = FollowUp.objects.get_or_create(
        customer=customer,
        subject=f"{tag} 新品提醒入口复测",
        defaults={
            "contact": contact,
            "followed_at": timezone.now(),
            "type": "email",
            "content": "Synthetic UAT follow-up. No customer message was sent.",
            "next_action": "复测新品提醒入口",
            "next_follow_up": today + timedelta(days=7),
        },
    )
    category, _ = ProductCategory.objects.get_or_create(name=f"{tag} 照明")
    product, _ = Product.objects.get_or_create(
        code=f"{tag}-P01",
        defaults={
            "name": f"{tag} 合成壁灯",
            "name_en": "Synthetic UAT Wall Light",
            "category": category,
            "status": "active",
        },
    )
    if not Supplier.objects.filter(code="UT").exists():
        supplier = Supplier.objects.create(
            code="UT",
            name=f"{tag} 合成供应商",
            country="中国",
            payment_terms="本次 UAT 按采购单保存的两阶段条款执行",
            payment_terms_config=default_payment_terms(),
        )
    else:
        supplier = Supplier.objects.get(code="UT")
        if not supplier.name.startswith(tag):
            raise ImproperlyConfigured("Supplier code UT is occupied by a non-UAT record.")

    sku, _ = SKU.objects.get_or_create(
        sku=f"{tag}-SKU01",
        defaults={
            "product": product,
            "specification": "10W / 3000K / IP65",
            "sales_model": f"{tag}-M01",
            "unit": "pcs",
            "cost_price": "12.00",
            "default_price": "25.00",
            "currency": "USD",
            "description_en": "Synthetic UAT wall light; not for sale.",
        },
    )
    supplier_sku, _ = SupplierSKU.objects.get_or_create(
        supplier=supplier,
        supplier_sku_code=f"{tag}-SUPSKU01",
        defaults={
            "sku": sku,
            "supplier_model": f"{tag}-MODEL01",
            "supplier_product_name": f"{tag} synthetic supply item",
            "purchase_price": "12.00",
            "currency": "USD",
            "moq": "0",
            "lead_time_days": 15,
            "is_active": True,
            "is_preferred": True,
        },
    )
    product.suppliers.add(supplier)
    supplier.supply_categories.add(category)

print(
    json.dumps(
        {
            "tag": tag,
            "customer": {"id": customer.pk, "code": customer.code, "name": customer.name},
            "contact": {"id": contact.pk, "name": contact.name, "email": contact.email},
            "follow_up": {"id": follow_up.pk, "subject": follow_up.subject},
            "category": {"id": category.pk, "name": category.name},
            "product": {"id": product.pk, "code": product.code, "name": product.name},
            "sku": {"id": sku.pk, "code": sku.sku, "unit": sku.unit},
            "supplier": {"id": supplier.pk, "code": supplier.code, "name": supplier.name},
            "supplier_sku": {"id": supplier_sku.pk, "code": supplier_sku.supplier_sku_code},
            "initial_inventory": "0 pcs",
        },
        ensure_ascii=False,
    )
)
