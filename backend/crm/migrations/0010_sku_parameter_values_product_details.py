from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("crm", "0009_product_hs_code_product_name_en")]

    operations = [
        migrations.AddField(
            model_name="sku",
            name="parameter_values",
            field=models.JSONField(blank=True, default=dict, verbose_name="参数快照"),
        ),
        migrations.AddField(
            model_name="sku",
            name="product_details",
            field=models.JSONField(blank=True, default=list, verbose_name="产品明细"),
        ),
    ]
