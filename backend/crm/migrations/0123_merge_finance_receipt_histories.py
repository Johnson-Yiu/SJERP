from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('crm', '0122_merge_sales_and_finance_review'),
        ('crm', '0120_advanceallocation_cash_amount_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='advanceallocation', name='cash_amount',
            field=models.DecimalField(blank=True, decimal_places=4, default=None, max_digits=14, null=True),
        ),
    ]
