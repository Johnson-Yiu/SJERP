"""Seed the isolated ISS-075 supplier/payment browser evidence database."""

import json
import os
from pathlib import Path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from django.core.serializers.json import DjangoJSONEncoder
from crm.models import Product, PurchaseOrder, PurchaseOrderItem, SKU, Supplier, SupplierSKU
from crm.payment_terms import default_payment_terms
from crm.services.purchase_lifecycle import place_purchase_order


def main():
    supplier, _ = Supplier.objects.get_or_create(
        code="Q7",
        defaults={
            "name": "ISS075 浏览器供应商",
            "country": "中国",
            "payment_terms": "付款条件按采购单协商",
            "payment_terms_config": default_payment_terms(),
        },
    )
    supplier.name = "ISS075 浏览器供应商"
    supplier.payment_terms = "旧供应商固定比例备注：30%/70%"
    supplier.payment_terms_config = default_payment_terms()
    supplier.is_active = True
    supplier.save()

    product, _ = Product.objects.get_or_create(
        code="ISS075-BROWSER-PRODUCT",
        defaults={"name": "ISS075 浏览器测试产品", "status": "active"},
    )
    sku, _ = SKU.objects.get_or_create(
        sku="ISS075-BROWSER-SKU",
        defaults={
            "product": product,
            "display_name_cn": "ISS075 浏览器测试 SKU",
            "specification": "付款条件回归",
            "unit": "pcs",
            "currency": "CNY",
            "cost_price": "3.25",
            "default_price": "8.00",
        },
    )
    sku.product = product
    sku.display_name_cn = "ISS075 浏览器测试 SKU"
    sku.unit = "pcs"
    sku.active = True
    sku.save()

    source, _ = SupplierSKU.objects.get_or_create(
        supplier=supplier,
        supplier_sku_code="ISS075-BROWSER-SOURCE",
        defaults={
            "sku": sku,
            "supplier_model": "ISS075-MODEL",
            "purchase_price": "12.0000",
            "currency": "CNY",
            "moq": "0",
            "is_active": True,
            "is_preferred": True,
        },
    )
    source.sku = sku
    source.purchase_price = "12.0000"
    source.currency = "CNY"
    source.moq = "0"
    source.is_active = True
    source.is_preferred = True
    source.save()

    historical_terms = [
        {"label": "首付款", "ratio": "0.50", "due_basis": "order_date", "offset_days": 0},
        {"label": "尾款", "ratio": "0.50", "due_basis": "expected_arrival_date", "offset_days": 0},
    ]
    PurchaseOrder.objects.filter(purchase_no="ISS075-HISTORY-01").delete()
    purchase = PurchaseOrder.objects.create(
        purchase_no="ISS075-HISTORY-01",
        supplier=supplier,
        order_date="2026-10-10",
        expected_arrival_date="2026-10-30",
        status="draft",
        currency="CNY",
        exchange_rate="1",
        payment_terms_snapshot=historical_terms,
        notes="ISS-075 历史正式采购单",
    )
    PurchaseOrderItem.objects.create(
        purchase_order=purchase,
        sku=sku,
        supplier_sku=source,
        quantity="1",
        unit_price="1000",
    )
    place_purchase_order(purchase)

    payload = {
        "supplier_id": supplier.id,
        "supplier_name": supplier.name,
        "sku_id": sku.id,
        "sku_code": sku.sku,
        "sku_name": sku.display_name_cn,
        "supplier_sku_id": source.id,
        "supplier_sku_code": source.supplier_sku_code,
        "history_purchase_id": purchase.id,
        "history_purchase_no": purchase.purchase_no,
        "history_payment_terms": historical_terms,
        "history_plan_amounts": [str(plan.planned_amount) for plan in purchase.payment_plans.order_by("id")],
    }
    evidence_dir = Path(os.environ["ISS075_EVIDENCE_DIR"])
    evidence_dir.mkdir(parents=True, exist_ok=True)
    (evidence_dir / "fixture.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2, cls=DjangoJSONEncoder), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
