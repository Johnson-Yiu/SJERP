from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("crm", "0018_finance_operating_ledger")]

    operations = [
        migrations.AddField(
            model_name="transaction",
            name="allocated_amount",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=14, verbose_name="已分配原币金额"),
        ),
    ]
