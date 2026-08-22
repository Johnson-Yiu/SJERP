from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("crm", "0019_transaction_allocated_amount")]

    operations = [
        migrations.CreateModel(
            name="ContractChangeRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("amount_delta", models.DecimalField(decimal_places=2, max_digits=14, verbose_name="合同原币变更金额")),
                ("due_date", models.DateField(blank=True, null=True, verbose_name="新增计划日期")),
                ("status", models.CharField(choices=[("pending", "待确认"), ("approved", "已确认"), ("rejected", "已拒绝")], default="pending", max_length=12, verbose_name="状态")),
                ("notes", models.TextField(verbose_name="变更说明")),
                ("order", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="contract_changes", to="crm.order")),
                ("purchase_order", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="contract_changes", to="crm.purchaseorder")),
            ],
        ),
    ]
