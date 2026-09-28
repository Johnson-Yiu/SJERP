from decimal import Decimal

from django.db import migrations


def backfill_default_allocations(apps, schema_editor):
    PurchaseOrder = apps.get_model("crm", "PurchaseOrder")
    PurchaseCostAllocation = apps.get_model("crm", "PurchaseCostAllocation")
    for purchase in PurchaseOrder.objects.filter(cost_allocation_version=0).iterator():
        for item in purchase.items.all():
            existing = list(PurchaseCostAllocation.objects.filter(purchase_item_id=item.pk))
            total = sum((row.quantity for row in existing), Decimal("0"))
            if existing:
                if total == item.quantity:
                    continue
                raise RuntimeError(
                    f"PurchaseOrderItem {item.pk} has incomplete version-zero cost allocations; manual review required."
                )
            PurchaseCostAllocation.objects.create(
                purchase_item_id=item.pk,
                target_type="order" if purchase.order_id else "inventory",
                order_id=purchase.order_id if purchase.order_id else None,
                quantity=item.quantity,
            )


class Migration(migrations.Migration):
    dependencies = [("crm", "0068_documentnumbersequence")]

    operations = [migrations.RunPython(backfill_default_allocations, migrations.RunPython.noop)]
