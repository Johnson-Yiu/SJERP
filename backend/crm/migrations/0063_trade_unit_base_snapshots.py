from django.db import migrations


def backfill(apps, schema_editor):
    for name in ('QuoteItem', 'OrderItem', 'PurchaseOrderItem', 'InventoryMovement', 'GoodsReceipt', 'ShipmentItem'):
        model = apps.get_model('crm', name)
        relation = 'purchase_item__sku' if name == 'GoodsReceipt' else 'sku'
        for line in model.objects.using(schema_editor.connection.alias).select_related(relation).iterator(chunk_size=500):
            if line.trade_snapshot:
                continue
            sku = line.purchase_item.sku if name == 'GoodsReceipt' else line.sku
            unit = getattr(line, 'unit_snapshot', '') or sku.unit
            model.objects.using(schema_editor.connection.alias).filter(pk=line.pk).update(
                trade_snapshot={'unit': unit, 'base_unit': unit, 'factor': '1', 'name': ''})


class Migration(migrations.Migration):
    dependencies = [('crm', '0062_sku_trade_units')]
    operations = [migrations.RunPython(backfill, migrations.RunPython.noop)]
