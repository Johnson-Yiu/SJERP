from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("crm", "0049_supplier_main_products")]

    operations = [
        migrations.AddField(
            model_name="supplier",
            name="store_url",
            field=models.URLField(blank=True, max_length=500, verbose_name="店铺链接"),
        ),
    ]
