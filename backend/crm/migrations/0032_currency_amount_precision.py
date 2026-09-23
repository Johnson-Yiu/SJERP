from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("crm", "0031_correct_sku_identity_from_specification"),
    ]

    operations = [
        migrations.AlterField(
            model_name="contractchangerequest",
            name="amount_delta",
            field=models.DecimalField(decimal_places=4, max_digits=14, verbose_name="合同原币变更金额"),
        ),
        migrations.AlterField(
            model_name="order",
            name="discount",
            field=models.DecimalField(decimal_places=4, default=0, max_digits=14, verbose_name="折扣金额"),
        ),
        migrations.AlterField(
            model_name="order",
            name="shipping_fee",
            field=models.DecimalField(decimal_places=4, default=0, max_digits=14, verbose_name="运费"),
        ),
        migrations.AlterField(
            model_name="paymentplan",
            name="planned_amount",
            field=models.DecimalField(decimal_places=4, max_digits=14, verbose_name="计划原币金额"),
        ),
        migrations.AlterField(
            model_name="paymentplan",
            name="settled_amount",
            field=models.DecimalField(decimal_places=4, default=0, max_digits=14, verbose_name="已核销原币金额"),
        ),
        migrations.AlterField(
            model_name="quote",
            name="discount",
            field=models.DecimalField(decimal_places=4, default=0, max_digits=14, verbose_name="折扣金额"),
        ),
        migrations.AlterField(
            model_name="quote",
            name="shipping_fee",
            field=models.DecimalField(decimal_places=4, default=0, max_digits=14, verbose_name="运费"),
        ),
        migrations.AlterField(
            model_name="transaction",
            name="allocated_amount",
            field=models.DecimalField(decimal_places=4, default=0, max_digits=14, verbose_name="已分配原币金额"),
        ),
        migrations.AlterField(
            model_name="transaction",
            name="amount",
            field=models.DecimalField(decimal_places=4, max_digits=14, verbose_name="金额"),
        ),
        migrations.AlterField(
            model_name="transaction",
            name="rmb_amount",
            field=models.DecimalField(decimal_places=4, default=0, max_digits=14, verbose_name="实际人民币金额"),
        ),
    ]
