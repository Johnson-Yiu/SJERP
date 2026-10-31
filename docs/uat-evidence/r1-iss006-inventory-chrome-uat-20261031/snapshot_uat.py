"""Write a JSON before/after snapshot for the isolated ISS-006 UAT database."""
import argparse
import json
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model

from crm.models import (
    FulfillmentIdempotency,
    GoodsReceipt,
    InventoryMovement,
    InventoryReservation,
    OperationLog,
    Order,
    PurchaseOrder,
    Shipment,
    SKU,
)
from crm.services.fulfillment import sku_metrics


EXPECTED_DB = (settings.BASE_DIR / "iss006-chrome-uat.sqlite3").resolve()
assert Path(settings.DATABASES["default"]["NAME"]).resolve() == EXPECTED_DB, "Refusing any non-UAT database"
parser = argparse.ArgumentParser()
parser.add_argument("--stage", required=True)
parser.add_argument("--output", required=True)
args = parser.parse_args()
evidence_dir = Path(__file__).parent
ids = json.loads((evidence_dir / "fixture-ids.json").read_text(encoding="utf-8"))
sku_ids = list(ids["sku"].values())
purchase_ids = list(ids["purchase"].values())
order_ids = [ids["order"]["id"]]

def decimal_map(values):
    return {key: str(value) for key, value in values.items()}

skus = []
for sku in SKU.objects.filter(pk__in=sku_ids).order_by("pk"):
    metrics = decimal_map(sku_metrics(sku))
    skus.append({"id": sku.pk, "sku": sku.sku, "name": sku.display_name_cn, **metrics})

purchases = []
for purchase in PurchaseOrder.objects.filter(pk__in=purchase_ids).order_by("purchase_no"):
    items = []
    for item in purchase.items.order_by("pk"):
        receipts = list(item.receipts.select_related("inventory_movement", "reversal_inventory_movement").order_by("pk"))
        active = [row for row in receipts if row.reversal_inventory_movement_id is None]
        items.append({
            "id": item.pk,
            "sku_id": item.sku_id,
            "ordered_quantity": str(item.quantity),
            "active_received_quantity": str(sum((row.quantity for row in active), start=item.quantity * 0)),
            "active_overage_quantity": str(sum((row.overage_quantity for row in active), start=item.quantity * 0)),
            "receipts": [{
                "id": row.pk,
                "quantity": str(row.quantity),
                "is_overage": row.is_overage,
                "overage_reason": row.overage_reason,
                "movement_id": row.inventory_movement_id,
                "reversal_movement_id": row.reversal_inventory_movement_id,
                "reversed_at": row.reversed_at.isoformat() if row.reversed_at else None,
                "reversal_reason": row.reversal_reason,
            } for row in receipts],
        })
    purchases.append({"id": purchase.pk, "purchase_no": purchase.purchase_no, "status": purchase.status, "items": items})

orders = []
for order in Order.objects.filter(pk__in=order_ids).order_by("pk"):
    active_shipments = Shipment.objects.filter(order=order, status="confirmed").prefetch_related("items")
    orders.append({
        "id": order.pk,
        "order_no": order.order_no,
        "status": order.status,
        "shipped_quantity": str(sum((line.quantity for shipment in active_shipments for line in shipment.items.all() if line.reversal_inventory_movement_id is None), start=order.items.first().quantity * 0)),
        "shipments": [{
            "id": shipment.pk,
            "shipment_no": shipment.shipment_no,
            "status": shipment.status,
            "reversed_at": shipment.reversed_at.isoformat() if shipment.reversed_at else None,
            "reversal_reason": shipment.reversal_reason,
        } for shipment in Shipment.objects.filter(order=order).order_by("pk")],
    })

movements = list(InventoryMovement.objects.filter(sku_id__in=sku_ids).select_related("sku").order_by("pk"))
reservations = list(InventoryReservation.objects.filter(sku_id__in=sku_ids).select_related("sku", "order_item__order").order_by("pk"))
logs = list(OperationLog.objects.filter(
    entity__in=["crm.purchaseorder", "crm.order", "crm.inventorymovement"],
    object_id__in=[str(value) for value in [*purchase_ids, *order_ids, *(row.pk for row in movements)]],
).select_related("operator").order_by("pk"))

payload = {
    "stage": args.stage,
    "database": str(EXPECTED_DB),
    "skus": skus,
    "purchases": purchases,
    "orders": orders,
    "reservations": [{
        "id": row.pk,
        "sku_id": row.sku_id,
        "order_no": row.order_item.order.order_no,
        "quantity": str(row.quantity),
    } for row in reservations],
    "movements": [{
        "id": row.pk,
        "movement_no": row.movement_no,
        "sku": row.sku.sku,
        "type": row.type,
        "signed_quantity": str(row.signed_quantity),
        "source_type": row.source_type,
        "source_no": row.source_no,
        "is_overage": row.is_overage,
        "overage_reason": row.overage_reason,
        "reference": row.reference,
        "notes": row.notes,
    } for row in movements],
    "idempotency_records": list(FulfillmentIdempotency.objects.filter(target_id__in=[*purchase_ids, *order_ids]).values("operation", "target_id", "response_status", "response_payload")),
    "operation_logs": [{
        "id": row.pk,
        "entity": row.entity,
        "object_id": row.object_id,
        "action": row.action,
        "action_label": row.action_label,
        "operator": row.operator.username if row.operator_id else None,
        "created_at": row.created_at.isoformat(),
        "request_path": row.request_path,
        "changed_fields": row.changed_fields,
        "before_data": row.before_data,
        "after_data": row.after_data,
        "metadata": row.metadata,
    } for row in logs],
}
out = Path(args.output).resolve()
assert evidence_dir.resolve() in out.parents, "Snapshot output must stay inside the evidence directory"
out.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
print(f"DATABASE_SNAPSHOT PASS: stage={args.stage}; file={out}; movements={len(movements)}; operation_logs={len(logs)}")
