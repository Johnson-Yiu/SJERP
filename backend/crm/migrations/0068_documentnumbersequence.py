from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0067_order_purchase_cancellation_lifecycle"),
    ]

    operations = [
        migrations.CreateModel(
            name="DocumentNumberSequence",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("document_type", models.CharField(choices=[("SO", "销售订单"), ("PO", "采购订单")], max_length=2)),
                ("year", models.PositiveSmallIntegerField()),
                ("last_value", models.PositiveIntegerField(default=0)),
            ],
            options={
                "constraints": [models.UniqueConstraint(fields=("document_type", "year"), name="unique_document_number_sequence")],
            },
        ),
    ]
