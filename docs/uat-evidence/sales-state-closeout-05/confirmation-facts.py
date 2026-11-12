"""Read confirmation facts from the audited isolated S5 database."""
import json
import sys
from decimal import Decimal

import django

django.setup()
from django.conf import settings
from test_support.isolated_runtime import verify_isolated_runtime

verify_isolated_runtime(settings=settings, database_must_exist=True)
if not settings.AUDIT_LOG_ENABLED:
    raise RuntimeError("The S5 audit profile is required.")

from crm.models import InventoryMovement, InventoryReservation, OperationLog, Order

order = Order.objects.get(pk=int(sys.argv[1]), order_no__startswith="S5-CONFIRM-")
line = order.items.get()
print(json.dumps({
    "status": order.status,
    "line": line.pk,
    "sku": line.sku_id,
    "quote": order.quote_id,
    "updated": order.updated_at.isoformat(),
    "reservation": list(InventoryReservation.objects.filter(order_item=line).order_by("pk").values("id", "sku_id", "quantity")),
    "plans": list(order.payment_plans.order_by("pk").values("id", "direction", "currency", "status", "planned_amount", "settled_amount", "notes")),
    "audit": list(OperationLog.objects.filter(entity="crm.order", object_id=str(order.pk),
        request_method="POST", request_path=f"/api/orders/{order.pk}/confirm/").order_by("pk").values(
        "id", "action", "action_label", "operator__username", "after_data", "metadata")),
    "movements": list(InventoryMovement.objects.filter(order=order).order_by("pk").values_list("pk", flat=True)),
}, default=str))
