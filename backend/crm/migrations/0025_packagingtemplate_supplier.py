from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("crm", "0024_product_sales_model_prefix_and_sku_abbreviations")]

    operations = [
        migrations.AddField(
            model_name="packagingtemplate",
            name="supplier",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="packaging_templates", to="crm.supplier", verbose_name="包装供应商"),
        ),
    ]
