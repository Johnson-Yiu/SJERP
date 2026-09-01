from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("crm", "0025_packagingtemplate_supplier")]

    operations = [
        migrations.RemoveConstraint(model_name="packagingtemplate", name="pack_template_qty_positive"),
        migrations.AlterField(model_name="packagingtemplate", name="code", field=models.CharField(blank=True, max_length=50, unique=True, verbose_name="包装模板编码")),
        migrations.AlterField(model_name="packagingtemplate", name="qty_per_carton", field=models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True, verbose_name="每箱数量（历史）")),
    ]
