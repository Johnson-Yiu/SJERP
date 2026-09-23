from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0057_sku_name_separator"),
    ]

    operations = [
        migrations.AddField(
            model_name="orderitem",
            name="supplier_allocation_note",
            field=models.CharField(blank=True, max_length=300, verbose_name="供应商分配说明"),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="supplier_allocation_scope",
            field=models.CharField(blank=True, choices=[("order_only", "仅本次订单"), ("recommended", "同时更新为推荐供应商")], max_length=30, verbose_name="供应商分配范围"),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="supplier_allocation_source",
            field=models.CharField(blank=True, choices=[("rule_match", "规则匹配"), ("historical_purchase", "历史采购"), ("manual", "人工补充"), ("supplier_sku", "供货档案")], max_length=30, verbose_name="供应商候选来源"),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="supplier_allocation_sources_snapshot",
            field=models.JSONField(blank=True, default=list, verbose_name="候选来源快照"),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="supplier_allocated_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="供应商分配时间"),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="supplier_barcode_snapshot",
            field=models.CharField(blank=True, max_length=100, verbose_name="供应商条码快照"),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="supplier_characteristics_snapshot",
            field=models.JSONField(blank=True, default=dict, verbose_name="供货特点快照"),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="supplier_currency_snapshot",
            field=models.CharField(blank=True, max_length=10, verbose_name="供应商报价币种快照"),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="supplier_lead_time_days_snapshot",
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name="交期快照（天）"),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="supplier_model_snapshot",
            field=models.CharField(blank=True, max_length=120, verbose_name="供应商型号快照"),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="supplier_moq_snapshot",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True, verbose_name="MOQ 快照"),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="supplier_name_snapshot",
            field=models.CharField(blank=True, max_length=200, verbose_name="供应商名称快照"),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="supplier_price_snapshot",
            field=models.DecimalField(blank=True, decimal_places=4, max_digits=14, null=True, verbose_name="供应商参考价快照"),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="supplier_sku",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="sales_order_items", to="crm.suppliersku", verbose_name="本次采购供应来源"),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="supplier_sku_code_snapshot",
            field=models.CharField(blank=True, max_length=100, verbose_name="供应商 SKU 编码快照"),
        ),
    ]
