from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("crm", "0039_categoryattribute_required")]

    operations = [
        migrations.AlterField(
            model_name="purchaseorder",
            name="order",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="purchase_orders", to="crm.order"),
        ),
    ]
