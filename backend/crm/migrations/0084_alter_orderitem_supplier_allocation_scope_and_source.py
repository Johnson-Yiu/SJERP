from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0083_customer_supplier_preference"),
    ]

    operations = [
        migrations.AlterField(
            model_name="orderitem",
            name="supplier_allocation_scope",
            field=models.CharField(
                blank=True,
                choices=[
                    ("order_only", "仅本次订单"),
                    ("customer_preferred", "设为该客户此 SKU 今后优先来源"),
                    ("recommended", "历史兼容值"),
                ],
                max_length=30,
                verbose_name="供应商分配范围",
            ),
        ),
        migrations.AlterField(
            model_name="orderitem",
            name="supplier_allocation_source",
            field=models.CharField(
                blank=True,
                choices=[
                    ("rule_match", "规则匹配"),
                    ("historical_purchase", "历史采购"),
                    ("manual", "人工补充"),
                    ("supplier_sku", "供货档案"),
                    ("customer_preference", "客户优先来源"),
                ],
                max_length=30,
                verbose_name="供应商候选来源",
            ),
        ),
    ]
