"""Seed only the current marked sales evidence database."""
import json
import os
import sys
from datetime import date
from io import BytesIO
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))
if os.environ.get("DJANGO_SETTINGS_MODULE") != "test_support.isolated_settings":
    raise RuntimeError("This fixture requires the isolated browser runner.")

import django

django.setup()

from crm.models import (
    Customer, FollowUp, InventoryMovement, Order, OrderItem, PackagingTemplate,
    Product, Quote, QuoteItem, SKU, SKUTradeUnit, Supplier, SupplierSKU,
)
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone
from test_support.isolated_runtime import verify_isolated_runtime

verify_isolated_runtime(settings=settings, database_must_exist=True)
customer = Customer.objects.create(
    code="E1-R2-LONG",
    name="SYNTH-SALES 森爵界面验收国际商业照明与综合工程采购服务中心 — International Commercial Lighting Project Procurement",
    country="Germany",
)

follow_up = FollowUp.objects.create(
    customer=customer, followed_at=timezone.now(), subject="SYNTH-SALES 附件与重开",
    content="Synthetic follow-up notes.",
)
product = Product.objects.create(code="SYNTH-SALES-LIGHT", name="Synthetic commercial lighting")
quote = Quote.objects.create(
    quote_no="SYNTH-SALES-QUOTATION-20261110-INTERNATIONAL-PROJECT-00000001",
    customer=customer, buyer_company_name=customer.name, quote_date=date(2026, 11, 10),
)
order = Order.objects.create(
    order_no="SYNTH-SALES-ORDER-20261110-00000000001", customer=customer,
    quote=quote, order_date=date(2026, 11, 10),
)
completed_order = Order.objects.create(
    order_no="SYNTH-SALES-COMPLETED-20261110-00000000001", customer=customer,
    order_date=date(2026, 11, 10), status="completed",
)
for index in range(1, 5):
    sku = SKU.objects.create(
        sku=f"SYNTH-SALES-SKU-{index:03d}", product=product, sales_model=f"SYNTH-MODEL-{index}",
        unit="pcs", default_price="12.50",
    )
    InventoryMovement.objects.create(
        movement_no=f"SYNTH-SALES-STOCK-{index:03d}", movement_date=date(2026, 11, 10),
        type="other_in", sku=sku, quantity=100, warehouse="默认仓",
    )
    fields = {
        "sku": sku, "sku_code_snapshot": sku.sku, "quantity": index * 10, "unit_price": "12.50",
        "description": "Synthetic commercial lighting — long item description for wrapped table cells",
    }
    item = QuoteItem.objects.create(quote=quote, **fields)
    if index == 1:
        trade = SKUTradeUnit.objects.create(sku=sku, name="合成五件箱", unit="箱", factor="5", allow_fraction=False)
        image = BytesIO()
        Image.new("RGB", (48, 32), "#e63842").save(image, format="PNG")
        item.image_snapshot.save("e1-r2-synthetic.png", ContentFile(image.getvalue()))
    fields.pop("description")
    OrderItem.objects.create(order=order, **fields)
    OrderItem.objects.create(order=completed_order, **fields)

carton = PackagingTemplate.objects.create(
    code="E1-R2-CARTON", name="合成包装模板", carton_length=40,
    carton_width=30, carton_height=20, carton_tare_weight=1,
)
supplier = Supplier.objects.create(code="E1-R2-PROC", name="合成采购来源")
procurement_sku = SKU.objects.create(sku="SYNTH-PROCUREMENT", product=product, sales_model="SYNTH-PROC", unit="pcs")
source = SupplierSKU.objects.create(
    supplier=supplier, sku=procurement_sku, supplier_sku_code="SYNTH-PROC-SUPPLIER",
    currency="CNY", purchase_price="6.50",
)
procurement_order = Order.objects.create(
    order_no="SYNTH-SALES-PROCUREMENT-20261110", customer=customer,
    order_date=date(2026, 11, 10), status="confirmed",
)
OrderItem.objects.create(
    order=procurement_order, sku=procurement_sku, supplier_sku=source,
    sku_code_snapshot=procurement_sku.sku, quantity=15, unit_price="12.50",
)

print(json.dumps({
    "customer": customer.pk, "quote": quote.pk, "order": order.pk,
    "completedOrder": completed_order.pk, "procurementOrder": procurement_order.pk,
    "tradeUnit": trade.pk, "carton": carton.pk, "followUp": follow_up.pk, "lines": 4,
}))
