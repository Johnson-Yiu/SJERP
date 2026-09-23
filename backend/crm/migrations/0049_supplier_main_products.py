from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("crm", "0048_reporting_geography")]

    operations = [
        migrations.RenameField(
            model_name="supplier",
            old_name="region",
            new_name="main_products",
        ),
        migrations.AlterField(
            model_name="supplier",
            name="country",
            field=models.CharField(default="中国", blank=True, max_length=100, verbose_name="国家/地区"),
        ),
        migrations.AlterField(
            model_name="supplier",
            name="main_products",
            field=models.CharField(blank=True, max_length=300, verbose_name="主要产品"),
        ),
        migrations.AlterField(
            model_name="supplier",
            name="payment_terms",
            field=models.CharField(default="30%预付款，70%尾款发货前结清", blank=True, max_length=200, verbose_name="付款条款"),
        ),
    ]
