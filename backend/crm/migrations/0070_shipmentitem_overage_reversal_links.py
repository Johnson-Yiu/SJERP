from django.db import migrations, models
import django.db.models.deletion


def backfill_overage_links(apps, schema_editor):
    ShipmentItem = apps.get_model("crm", "ShipmentItem")
    PaymentPlan = apps.get_model("crm", "PaymentPlan")
    for item in ShipmentItem.objects.filter(is_overage=True).select_related("shipment", "order_item"):
        shipment = item.shipment
        candidates = list(ShipmentItem.objects.filter(shipment_id=shipment.pk, sku_id=item.sku_id, is_overage=False).values_list("order_item_id", flat=True))
        if len(candidates) == 1:
            item.source_order_item_id = candidates[0]
        if item.overage_reason == "customer_addon":
            plans = list(PaymentPlan.objects.filter(
                order_id=shipment.order_id, direction="receivable", notes=f"发货单 {shipment.shipment_no} 客户追加"
            ).values_list("pk", flat=True))
            if len(plans) == 1:
                item.generated_payment_plan_id = plans[0]
        if item.source_order_item_id or item.generated_payment_plan_id:
            item.save(update_fields=["source_order_item", "generated_payment_plan"])


class Migration(migrations.Migration):
    dependencies = [("crm", "0069_backfill_purchase_cost_allocations")]

    operations = [
        migrations.AddField(
            model_name="shipmentitem", name="source_order_item",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="sourced_shipment_items", to="crm.orderitem"),
        ),
        migrations.AddField(
            model_name="shipmentitem", name="generated_payment_plan",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="generated_shipment_items", to="crm.paymentplan"),
        ),
        migrations.RunPython(backfill_overage_links, migrations.RunPython.noop),
    ]
