from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0086_purchase_moq_exception"),
    ]

    operations = [
        # Existing rows are explicitly marked with the pre-ISS-020 rule so
        # their derived totals do not change during deployment. The model
        # default is changed to the current rule for new rows below.
        migrations.AddField(
            model_name="quote",
            name="amount_calculation_version",
            field=models.PositiveSmallIntegerField(default=1, editable=False),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="order",
            name="amount_calculation_version",
            field=models.PositiveSmallIntegerField(default=1, editable=False),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="quote",
            name="amount_calculation_version",
            field=models.PositiveSmallIntegerField(default=2, editable=False),
        ),
        migrations.AlterField(
            model_name="order",
            name="amount_calculation_version",
            field=models.PositiveSmallIntegerField(default=2, editable=False),
        ),
    ]
