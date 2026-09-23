from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("crm", "0040_purchaseorder_order_optional")]

    operations = [
        migrations.AddField(
            model_name="inventorymovement",
            name="related_orders",
            field=models.ManyToManyField(blank=True, related_name="related_inventory_movements", to="crm.order", verbose_name="关联订单"),
        ),
    ]
