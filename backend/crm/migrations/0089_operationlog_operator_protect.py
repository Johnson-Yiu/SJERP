from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0088_operationlog_append_only"),
    ]

    operations = [
        migrations.AlterField(
            model_name="operationlog",
            name="operator",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.PROTECT,
                related_name="operation_logs",
                to="auth.user",
            ),
        ),
    ]
