from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("crm", "0089_operationlog_operator_protect"),
    ]

    operations = [
        migrations.CreateModel(
            name="FulfillmentIdempotency",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("key", models.CharField(max_length=128, unique=True, verbose_name="请求标识")),
                ("operation", models.CharField(max_length=20, verbose_name="业务操作")),
                ("target_id", models.PositiveBigIntegerField(verbose_name="目标对象 ID")),
                ("request_hash", models.CharField(max_length=64, verbose_name="请求内容摘要")),
                ("status", models.CharField(choices=[("processing", "处理中"), ("succeeded", "已完成")], default="processing", max_length=20, verbose_name="处理状态")),
                ("response_status", models.PositiveSmallIntegerField(default=201, verbose_name="响应状态码")),
                ("response_payload", models.JSONField(default=dict, verbose_name="原始业务响应")),
                (
                    "operator",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="fulfillment_idempotency_records",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(fields=["operation", "target_id"], name="crm_fi_op_target_idx"),
                    models.Index(fields=["operator", "created_at"], name="crm_fi_operator_created_idx"),
                ],
            },
        ),
    ]
