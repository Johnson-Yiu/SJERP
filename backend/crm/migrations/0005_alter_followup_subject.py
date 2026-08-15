from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("crm", "0004_organization_and_permissions")]

    operations = [
        migrations.AlterField(
            model_name="followup",
            name="subject",
            field=models.CharField(blank=True, default="", max_length=200, verbose_name="主题"),
        ),
    ]
