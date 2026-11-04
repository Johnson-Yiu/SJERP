from django.db import migrations, models


def refuse_loss_of_locations(apps, schema_editor):
    movement = apps.get_model("crm", "InventoryMovement")
    if movement.objects.exclude(warehouse_type="自有仓").exists() or movement.objects.exclude(lot_reference="").exists():
        raise RuntimeError("库存流水已有仓库类型或批次，不允许回退丢失资料。")


class Migration(migrations.Migration):
    dependencies = [("crm", "0106_historical_purchase_balance_mode")]
    operations = [
        migrations.AddField(model_name="inventorymovement", name="warehouse_type", field=models.CharField(choices=[("自有仓", "自有仓"), ("第三方仓", "第三方仓")], default="自有仓", max_length=10, verbose_name="仓库类型")),
        migrations.AddField(model_name="inventorymovement", name="lot_reference", field=models.CharField(blank=True, max_length=160, verbose_name="批次或货位")),
        migrations.RunPython(migrations.RunPython.noop, refuse_loss_of_locations),
    ]
