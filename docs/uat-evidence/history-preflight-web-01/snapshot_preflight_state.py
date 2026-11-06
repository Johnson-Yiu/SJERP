"""Print a deterministic snapshot of business tables and private media."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from django.conf import settings
from crm.models import (
    CSVImportBatch,
    CSVImportPreviewAudit,
    CSVImportRowAudit,
    Customer,
    GoodsReceipt,
    InventoryMovement,
    InventoryReservation,
    OperationLog,
    Order,
    OrderItem,
    PaymentPlan,
    Product,
    PurchaseOrder,
    PurchaseOrderItem,
    Shipment,
    ShipmentItem,
    SKU,
    Supplier,
    Transaction,
)


MODELS = (
    Customer, Supplier, Product, SKU, Order, OrderItem, PurchaseOrder, PurchaseOrderItem,
    PaymentPlan, Transaction, GoodsReceipt, Shipment, ShipmentItem, InventoryMovement,
    InventoryReservation, OperationLog, CSVImportBatch, CSVImportPreviewAudit, CSVImportRowAudit,
)


def records(model, **filters):
    fields = [field.attname for field in model._meta.concrete_fields]
    queryset = model.objects.filter(**filters) if filters else model.objects.all()
    return list(queryset.order_by("pk").values(*fields))


def private_media():
    root = Path(settings.MEDIA_ROOT)
    if not root.exists():
        return []
    result = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        result.append({"path": path.relative_to(root).as_posix(), "size": path.stat().st_size, "sha256": digest})
    return result


snapshot = {
    "models": {
        model.__name__: {"count": model.objects.count(), "rows": records(model)}
        for model in MODELS
    },
    "receivables": records(PaymentPlan, direction="receivable"),
    "payables": records(PaymentPlan, direction="payable"),
    "inventory_movements": records(InventoryMovement),
    "sales_orders": records(Order),
    "purchase_orders": records(PurchaseOrder),
    "private_media": private_media(),
}
print(json.dumps(snapshot, ensure_ascii=False, indent=2, default=str))
