from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("crm", "0023_categoryattribute_include_in_sales_model")]

    operations = [
        migrations.AddField(
            model_name="product",
            name="sales_model_prefix",
            field=models.CharField(blank=True, max_length=30, null=True, unique=True, verbose_name="销售型号前缀"),
        ),
        migrations.AddField(
            model_name="sku",
            name="sales_model_abbreviations",
            field=models.JSONField(blank=True, default=dict, verbose_name="销售型号参数缩写"),
        ),
    ]
