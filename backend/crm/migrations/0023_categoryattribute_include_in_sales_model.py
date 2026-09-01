from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("crm", "0022_merge_20260823_2351")]

    operations = [
        migrations.AddField(
            model_name="categoryattribute",
            name="include_in_sales_model",
            field=models.BooleanField(default=False, verbose_name="参与生成型号"),
        ),
    ]
