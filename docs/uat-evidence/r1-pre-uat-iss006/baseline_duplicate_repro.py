"""ISS-006 baseline reproduction for repeated requests after a lost response.

This script is deliberately limited to a disposable SQLite database selected by
the caller through DATABASE_URL.  It is evidence setup, not a production seed.
"""
import json
import os
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[3] / "backend"))

import django
from django.core.management import call_command


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
os.environ.setdefault("DJANGO_ALLOWED_HOSTS", "testserver,localhost,127.0.0.1")
django.setup()

from crm.models import Customer, GoodsReceipt, InventoryMovement, InventoryReservation, Order, Product, PurchaseOrder, Shipment, SKU, Supplier  # noqa: E402
from crm.services.fulfillment import allocate_order, order_item_metrics, sku_metrics  # noqa: E402
from rest_framework.test import APIClient  # noqa: E402


database_name = Path(django.conf.settings.DATABASES["default"]["NAME"]).resolve()
if database_name.name not in {"iss006-baseline-duplicate.sqlite3", "iss006-fixed-idempotency.sqlite3"}:
    raise SystemExit(f"Refusing non-disposable database: {database_name}")

call_command("migrate", verbosity=0, interactive=False)
day = date(2026, 10, 28)
customer = Customer.objects.create(code="ISS006-B-CUSTOMER", name="ISS-006 基线客户")
supplier = Supplier.objects.create(code="ISS006-B-SUPPLIER", name="ISS-006 基线供应商")
product = Product.objects.create(code="ISS006-B-PRODUCT", name="ISS-006 基线产品")
receipt_sku = SKU.objects.create(product=product, sku="ISS006-B-RECEIPT", unit="pcs")
shipment_sku = SKU.objects.create(product=product, sku="ISS006-B-SHIPMENT", unit="pcs")

purchase = PurchaseOrder.objects.create(
    purchase_no="PO-ISS006-BASELINE",
    supplier=supplier,
    order_date=day,
    status="ordered",
    currency="USD",
)
purchase_item = purchase.items.create(sku=receipt_sku, quantity=Decimal("10"), unit_price=Decimal("2"))

order = Order.objects.create(
    order_no="SO-ISS006-BASELINE",
    customer=customer,
    order_date=day,
    status="confirmed",
    currency="USD",
)
order_item = order.items.create(sku=shipment_sku, quantity=Decimal("10"), unit_price=Decimal("3"))
InventoryMovement.objects.create(
    movement_no="IM-ISS006-BASELINE",
    movement_date=day,
    type="adjust_in",
    sku=shipment_sku,
    quantity=Decimal("10"),
    source_type="manual",
)
allocate_order(order)

client = APIClient()
receipt_payload = {
    "purchase_item": purchase_item.pk,
    "receipt_date": str(day),
    "quantity": "5",
    "unit_cost": "2",
}
if os.getenv("ISS006_USE_REQUEST_KEYS"):
    receipt_payload["request_key"] = "iss006-receipt-fixed-retry"
receipt_before = {
    "receipts": purchase_item.receipts.count(),
    "purchase_movements": InventoryMovement.objects.filter(source_type="receipt", sku=receipt_sku).count(),
    "actual": str(sku_metrics(receipt_sku)["actual_quantity"]),
}
receipt_first = client.post(f"/api/purchase-orders/{purchase.pk}/receive/", receipt_payload, format="json")
receipt_second = client.post(f"/api/purchase-orders/{purchase.pk}/receive/", receipt_payload, format="json")
receipt_after = {
    "receipts": purchase_item.receipts.count(),
    "purchase_movements": InventoryMovement.objects.filter(source_type="receipt", sku=receipt_sku).count(),
    "actual": str(sku_metrics(receipt_sku)["actual_quantity"]),
}

shipment_payload = {"shipment_date": str(day), "items": [{"order_item": order_item.pk, "quantity": "5"}]}
if os.getenv("ISS006_USE_REQUEST_KEYS"):
    shipment_payload["request_key"] = "iss006-shipment-fixed-retry"
shipment_before = {
    "shipments": order.shipments.count(),
    "sale_movements": InventoryMovement.objects.filter(source_type="shipment", sku=shipment_sku).count(),
    "actual": str(sku_metrics(shipment_sku)["actual_quantity"]),
}
shipment_first = client.post(f"/api/orders/{order.pk}/ship/", shipment_payload, format="json")
shipment_second = client.post(f"/api/orders/{order.pk}/ship/", shipment_payload, format="json")
shipment_after = {
    "shipments": order.shipments.count(),
    "sale_movements": InventoryMovement.objects.filter(source_type="shipment", sku=shipment_sku).count(),
    "actual": str(sku_metrics(shipment_sku)["actual_quantity"]),
}
purchase.refresh_from_db()
purchase_item.refresh_from_db()
order.refresh_from_db()
order_item.refresh_from_db()
database_after = {
    "purchase": {
        "status": purchase.status,
        "received_quantity": str(purchase_item.received_quantity),
        "remaining_quantity": str(purchase_item.remaining_quantity),
        "receipt_count": GoodsReceipt.objects.filter(purchase_item=purchase_item).count(),
    },
    "order": {
        "status": order.status,
        "shipped_quantity": str(order_item_metrics(order_item)["shipped_quantity"]),
        "reservation_quantity": str(InventoryReservation.objects.filter(order_item=order_item).values_list("quantity", flat=True).first() or Decimal("0")),
        "shipment_count": Shipment.objects.filter(order=order).count(),
    },
    "inventory": {
        "receipt_sku": {key: str(value) for key, value in sku_metrics(receipt_sku).items()},
        "shipment_sku": {key: str(value) for key, value in sku_metrics(shipment_sku).items()},
    },
    "movements": list(InventoryMovement.objects.values("movement_no", "type", "source_type", "source_no", "quantity", "sku_id").order_by("id")),
}

result = {
    "database": str(database_name),
    "receipt": {
        "before": receipt_before,
        "first_status": receipt_first.status_code,
        "second_status": receipt_second.status_code,
        "first_body": receipt_first.data,
        "second_body": receipt_second.data,
        "after": receipt_after,
    },
    "shipment": {
        "before": shipment_before,
        "first_status": shipment_first.status_code,
        "second_status": shipment_second.status_code,
        "first_body": shipment_first.data,
        "second_body": shipment_second.data,
        "after": shipment_after,
    },
    "database_after": database_after,
}
output_name = "fixed-idempotency-repro.json" if os.getenv("ISS006_USE_REQUEST_KEYS") else "baseline-duplicate-repro.json"
output = Path(__file__).with_name(output_name)
output.write_text(json.dumps(result, ensure_ascii=False, default=str, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, default=str, indent=2))
