# Generated manually for the finance operating ledger.

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0017_product_suppliers"),
    ]

    operations = [
        migrations.CreateModel(
            name="PaymentPlan",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("direction", models.CharField(choices=[("receivable", "应收"), ("payable", "应付")], max_length=12, verbose_name="收付款方向")),
                ("due_date", models.DateField(blank=True, null=True, verbose_name="预计日期")),
                ("planned_amount", models.DecimalField(decimal_places=2, max_digits=14, verbose_name="计划原币金额")),
                ("settled_amount", models.DecimalField(decimal_places=2, default=0, max_digits=14, verbose_name="已核销原币金额")),
                ("currency", models.CharField(max_length=10, verbose_name="币种")),
                ("status", models.CharField(choices=[("open", "待结清"), ("settled", "已结清"), ("cancelled", "已取消")], default="open", max_length=12, verbose_name="状态")),
                ("notes", models.TextField(blank=True, verbose_name="备注")),
                ("order", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="payment_plans", to="crm.order")),
                ("purchase_order", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="payment_plans", to="crm.purchaseorder")),
            ],
            options={"ordering": ["due_date", "id"]},
        ),
        migrations.AddConstraint(
            model_name="paymentplan",
            constraint=models.CheckConstraint(condition=(models.Q(("order__isnull", False), ("purchase_order__isnull", True)) | models.Q(("order__isnull", True), ("purchase_order__isnull", False))), name="payment_plan_one_contract"),
        ),
        migrations.AddConstraint(
            model_name="paymentplan",
            constraint=models.CheckConstraint(condition=models.Q(("planned_amount__gt", 0)), name="payment_plan_amount_positive"),
        ),
        migrations.AddConstraint(
            model_name="paymentplan",
            constraint=models.CheckConstraint(condition=models.Q(("settled_amount__gte", 0)), name="payment_plan_settled_non_negative"),
        ),
        migrations.AddField(
            model_name="transaction",
            name="kind",
            field=models.CharField(choices=[("other", "其他收支"), ("customer_receipt", "客户收款"), ("supplier_payment", "供应商付款"), ("order_expense", "订单费用"), ("period_expense", "期间费用"), ("unallocated_advance", "未分配预收预付"), ("refund", "退款或折让"), ("exchange_difference", "汇兑差额")], default="other", max_length=30, verbose_name="业务类型"),
        ),
        migrations.AddField(
            model_name="transaction",
            name="plan",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="transactions", to="crm.paymentplan"),
        ),
        migrations.AddField(
            model_name="transaction",
            name="replaces",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="replacements", to="crm.transaction"),
        ),
        migrations.AddField(
            model_name="transaction",
            name="rmb_amount",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=14, verbose_name="实际人民币金额"),
        ),
        migrations.AddField(
            model_name="transaction",
            name="supplier",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="transactions", to="crm.supplier"),
        ),
    ]
