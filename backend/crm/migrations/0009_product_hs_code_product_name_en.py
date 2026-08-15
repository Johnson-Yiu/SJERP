from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("crm", "0008_productcodesequence_product_additional_categories")]

    operations = [
        migrations.AddField(model_name="product", name="hs_code", field=models.CharField(blank=True, max_length=30, verbose_name="HS 编码")),
        migrations.AddField(model_name="product", name="name_en", field=models.CharField(blank=True, max_length=200, verbose_name="产品英文名称")),
    ]
