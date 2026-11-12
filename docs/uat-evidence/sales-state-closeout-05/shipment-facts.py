"""Read the isolated shipment, carton and stock facts before and after reversal."""
import json
import sys

import django

django.setup()
from django.conf import settings
from test_support.isolated_runtime import verify_isolated_runtime

verify_isolated_runtime(settings=settings, database_must_exist=True)

from crm.models import InventoryMovement, Shipment
from crm.services.fulfillment import sku_metrics

shipment = Shipment.objects.select_related("order").get(pk=int(sys.argv[1]), order__order_no__startswith="S5-PACK-")
line = shipment.items.select_related("sku", "inventory_movement", "reversal_inventory_movement").get()
outbound = line.inventory_movement
reversal = line.reversal_inventory_movement
print(json.dumps({
    "shipment": shipment.pk,
    "status": shipment.status,
    "order": shipment.order_id,
    "orderStatus": shipment.order.status,
    "reason": shipment.reversal_reason,
    "cartons": [
        {"id": carton.pk, "quantities": [str(item.quantity) for item in carton.items.all()]}
        for carton in shipment.packages.order_by("pk")
    ],
    "outbound": {"id": outbound.pk, "number": outbound.movement_no, "quantity": str(outbound.quantity)},
    "reversal": None if reversal is None else {
        "id": reversal.pk, "type": reversal.type, "order": reversal.order_id,
        "source": reversal.source_no, "reference": reversal.reference, "quantity": str(reversal.quantity),
        "sameLocation": (reversal.warehouse, reversal.lot_reference) == (outbound.warehouse, outbound.lot_reference),
    },
    "reversalCount": InventoryMovement.objects.filter(source_type="reversal", source_no=shipment.shipment_no).count(),
    "stock": {name: str(value) for name, value in sku_metrics(line.sku).items()},
}))
