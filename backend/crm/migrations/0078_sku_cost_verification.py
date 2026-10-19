from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0077_rmb_cash_events"),
    ]

    operations = [
        migrations.AddField(
            model_name="sku",
            name="cost_currency",
            field=models.CharField(
                blank=True,
                default=None,
                max_length=10,
                null=True,
                verbose_name="成本币种",
            ),
        ),
        migrations.AddField(
            model_name="sku",
            name="cost_verified_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name="成本最后核实时间",
            ),
        ),
        migrations.AddField(
            model_name="sku",
            name="cost_verified_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="verified_sku_costs",
                to=settings.AUTH_USER_MODEL,
                verbose_name="成本最后核实人",
            ),
        ),
        migrations.AddField(
            model_name="suppliersku",
            name="purchase_price_verified_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name="采购参考价最后核实时间",
            ),
        ),
        migrations.AddField(
            model_name="suppliersku",
            name="purchase_price_verified_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="verified_supplier_sku_prices",
                to=settings.AUTH_USER_MODEL,
                verbose_name="采购参考价最后核实人",
            ),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="cost_currency_snapshot",
            field=models.CharField(
                blank=True,
                max_length=10,
                verbose_name="成交时成本币种快照",
            ),
        ),
    ]
