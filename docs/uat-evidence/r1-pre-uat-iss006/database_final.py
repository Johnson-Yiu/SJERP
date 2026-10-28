"""Read-only final snapshot for the disposable ISS-006 fixed database."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[3] / "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
os.environ.setdefault("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost")
import django

django.setup()

from django.conf import settings  # noqa: E402
from crm.models import GoodsReceipt, InventoryMovement, InventoryReservation, Order, PurchaseOrder, Shipment  # noqa: E402
from crm.services.fulfillment import order_item_metrics, sku_metrics  # noqa: E402


database_name = Path(settings.DATABASES["default"]["NAME"]).resolve()
if database_name.name != "iss006-fixed-idempotency.sqlite3":
    raise SystemExit(f"Refusing non-disposable database: {database_name}")

purchase = PurchaseOrder.objects.get(purchase_no="PO-ISS006-BASELINE")
purchase_item = purchase.items.get()
order = Order.objects.get(order_no="SO-ISS006-BASELINE")
order_item = order.items.get()
payload = {
    "database": str(database_name),
    "purchase": {
        "status": purchase.status,
        "received_quantity": str(purchase_item.received_quantity),
        "remaining_quantity": str(purchase_item.remaining_quantity),
        "receipt_count": GoodsReceipt.objects.filter(purchase_item=purchase_item).count(),
    },
    "order": {
        "status": order.status,
        "shipped_quantity": str(order_item_metrics(order_item)["shipped_quantity"]),
        "reservation_quantity": str(InventoryReservation.objects.filter(order_item=order_item).values_list("quantity", flat=True).first() or 0),
        "shipment_count": Shipment.objects.filter(order=order).count(),
    },
    "inventory": {
        "receipt_sku": {key: str(value) for key, value in sku_metrics(purchase_item.sku).items()},
        "shipment_sku": {key: str(value) for key, value in sku_metrics(order_item.sku).items()},
    },
    "movements": list(InventoryMovement.objects.values("movement_no", "type", "source_type", "source_no", "quantity", "sku_id").order_by("id")),
}
output = Path(__file__).with_name("database-final.json")
output.write_text(json.dumps(payload, ensure_ascii=False, default=str, indent=2), encoding="utf-8")
print(json.dumps(payload, ensure_ascii=False, default=str, indent=2))
