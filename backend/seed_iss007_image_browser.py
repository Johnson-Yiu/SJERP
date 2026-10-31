"""Seed synthetic SKU/quote fixtures for the ISS-007 real-browser UAT."""

import base64
import hashlib
import io
import json
import os
from pathlib import Path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from django.core.serializers.json import DjangoJSONEncoder
from PIL import Image

from crm.models import Customer, Product, Quote, QuoteItem, SKU
from test_support.isolated_runtime import verify_isolated_runtime


def png_bytes(color):
    stream = io.BytesIO()
    Image.new("RGB", (48, 32), color).save(stream, format="PNG")
    return stream.getvalue()


def main():
    verify_isolated_runtime(settings=django.conf.settings, database_must_exist=True)
    customer = Customer.objects.create(
        code="ISS007-UAT-C",
        name="ISS-007 合成图片买家",
        country="Germany",
        address="仅用于隔离验收，不对应真实客户",
    )
    product = Product.objects.create(code="ISS007-UAT-P", name="ISS-007 图片快照测试产品")
    sku = SKU.objects.create(
        product=product,
        sku="ISS007-UAT-SKU",
        sales_model="ISS007-UAT-MODEL",
        display_name_cn="ISS-007 图片快照测试 SKU",
        description_en="Synthetic image snapshot verification item",
        unit="pcs",
        currency="USD",
        default_price="12.50",
    )

    missing_quote = Quote.objects.create(
        quote_no="ISS007-UAT-MISSING-IMAGE",
        customer=customer,
        buyer_company_name=customer.name,
        recipient_name="合成联系人",
        buyer_address=customer.address,
        quote_date="2026-10-31",
        valid_until="2026-11-30",
        status="accepted",
        currency="USD",
        deposit_ratio="0.3000",
    )
    missing_item = QuoteItem.objects.create(
        quote=missing_quote,
        sku=sku,
        quantity="1.00",
        unit_price="12.50",
        description="用于验证历史图片文件缺失时页面仍可用。",
    )
    missing_item.image_snapshot.name = "quote-item-images/iss007-uat/missing-history-image.png"
    missing_item.save(update_fields=["image_snapshot"])

    original = png_bytes("#d63d3d")
    replacement = png_bytes("#267bb5")
    payload = {
        "synthetic_only": True,
        "customer_id": customer.pk,
        "product_id": product.pk,
        "sku_id": sku.pk,
        "sku_code": sku.sku,
        "missing_quote_id": missing_quote.pk,
        "missing_quote_item_id": missing_item.pk,
        "missing_image_path": missing_item.image_snapshot.name,
        "original_image_sha256": hashlib.sha256(original).hexdigest(),
        "replacement_image_sha256": hashlib.sha256(replacement).hexdigest(),
        "original_image_base64": base64.b64encode(original).decode("ascii"),
        "replacement_image_base64": base64.b64encode(replacement).decode("ascii"),
    }
    evidence_dir = Path(os.environ["ISS007_EVIDENCE_DIR"])
    evidence_dir.mkdir(parents=True, exist_ok=True)
    (evidence_dir / "fixture.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, cls=DjangoJSONEncoder), encoding="utf-8",
    )
    print(json.dumps({key: value for key, value in payload.items() if not key.endswith("_base64")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
