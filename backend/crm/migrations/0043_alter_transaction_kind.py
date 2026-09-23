from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0042_alter_inventorymovement_type"),
    ]

    operations = [
        migrations.AlterField(
            model_name="transaction",
            name="kind",
            field=models.CharField(
                choices=[
                    ("other", "其他收支"),
                    ("customer_receipt", "客户收款"),
                    ("supplier_payment", "供应商付款"),
                    ("order_expense", "订单费用"),
                    ("period_expense", "期间费用"),
                    ("unallocated_advance", "未分配预收预付"),
                    ("supplier_refund", "供应商退款返利"),
                    ("other_income", "其他收入"),
                    ("sample_expense", "样品费用"),
                    ("freight_expense", "运费物流费"),
                    ("bank_fee", "银行手续费"),
                    ("tax_fee", "税费"),
                    ("salary_expense", "工资福利"),
                    ("office_expense", "办公费用"),
                    ("travel_expense", "差旅招待"),
                    ("marketing_expense", "营销推广"),
                    ("warehouse_expense", "仓储费用"),
                    ("asset_expense", "设备固定资产"),
                    ("unallocated_payment", "未分配预付款"),
                    ("other_expense", "其他支出"),
                    ("refund", "退款或折让"),
                    ("exchange_difference", "汇兑差额"),
                ],
                default="other",
                max_length=30,
                verbose_name="业务类型",
            ),
        ),
    ]
