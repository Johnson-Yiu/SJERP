"""Seed the isolated ISS-022 real-browser evidence database."""

import json
import os
from pathlib import Path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from django.core.serializers.json import DjangoJSONEncoder
from crm.models import Product, SKU, SKUTradeUnit, Supplier, SupplierSKU


def main():
    supplier, _ = Supplier.objects.get_or_create(
        code="Q2",
        defaults={
            "name": "ISS022 浏览器供应商",
            "country": "中国",
            "payment_terms": "现款",
        },
    )
    supplier.name = "ISS022 浏览器供应商"
    supplier.is_active = True
    supplier.save(update_fields=["name", "is_active", "updated_at"])

    product, _ = Product.objects.get_or_create(
        code="ISS022-BROWSER-PRODUCT",
        defaults={"name": "ISS022 浏览器测试产品", "status": "active"},
    )
    sku, _ = SKU.objects.get_or_create(
        sku="ISS022-BROWSER-SKU",
        defaults={
            "product": product,
            "display_name_cn": "ISS022 浏览器测试 SKU",
            "specification": "MOQ 浏览器回归",
            "unit": "pcs",
            "currency": "CNY",
            "cost_price": "3.25",
            "default_price": "8.00",
        },
    )
    sku.product = product
    sku.display_name_cn = "ISS022 浏览器测试 SKU"
    sku.unit = "pcs"
    sku.currency = "CNY"
    sku.cost_price = "3.25"
    sku.save()

    source, _ = SupplierSKU.objects.get_or_create(
        supplier=supplier,
        supplier_sku_code="ISS022-BROWSER-SOURCE",
        defaults={
            "sku": sku,
            "supplier_model": "ISS022-MODEL",
            "supplier_product_name": "ISS022 浏览器测试来源",
            "purchase_price": "12.0000",
            "currency": "CNY",
            "moq": "10.00",
            "is_active": True,
            "is_preferred": True,
        },
    )
    source.sku = sku
    source.purchase_price = "12.0000"
    source.currency = "CNY"
    source.moq = "10.00"
    source.is_active = True
    source.is_preferred = True
    source.save()

    trade_unit, _ = SKUTradeUnit.objects.get_or_create(
        sku=sku,
        supplier=supplier,
        name="10 件箱",
        defaults={
            "unit": "box",
            "factor": "10.00",
            "allow_fraction": True,
            "is_default": False,
            "active": True,
        },
    )
    trade_unit.unit = "box"
    trade_unit.factor = "10.00"
    trade_unit.allow_fraction = True
    trade_unit.active = True
    trade_unit.save()

    payload = {
        "database": os.environ.get("DATABASE_URL", ""),
        "supplier_id": supplier.id,
        "supplier_name": supplier.name,
        "sku_id": sku.id,
        "sku_code": sku.sku,
        "sku_name": sku.display_name_cn,
        "supplier_sku_id": source.id,
        "supplier_sku_code": source.supplier_sku_code,
        "moq": str(source.moq),
        "trade_unit_id": trade_unit.id,
        "trade_unit_name": trade_unit.name,
        "trade_unit": trade_unit.unit,
        "trade_factor": str(trade_unit.factor),
    }
    evidence_dir = Path(os.environ["ISS022_EVIDENCE_DIR"])
    evidence_dir.mkdir(parents=True, exist_ok=True)
    (evidence_dir / "fixture.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, cls=DjangoJSONEncoder),
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
