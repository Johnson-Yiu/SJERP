from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0043_alter_transaction_kind"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.CreateModel(
            name="OperationLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("object_id", models.CharField(max_length=100, verbose_name="对象 ID")),
                ("entity", models.CharField(db_index=True, max_length=100, verbose_name="对象类型")),
                ("entity_label", models.CharField(blank=True, max_length=100, verbose_name="对象类型名称")),
                ("object_label", models.CharField(blank=True, max_length=300, verbose_name="对象名称")),
                ("action", models.CharField(choices=[("create", "创建"), ("update", "修改"), ("delete", "删除"), ("custom", "业务操作")], default="custom", max_length=30, verbose_name="操作类型")),
                ("action_label", models.CharField(blank=True, max_length=100, verbose_name="操作说明")),
                ("changed_fields", models.JSONField(blank=True, default=list, verbose_name="变更字段")),
                ("before_data", models.JSONField(blank=True, default=dict, verbose_name="变更前数据")),
                ("after_data", models.JSONField(blank=True, default=dict, verbose_name="变更后数据")),
                ("metadata", models.JSONField(blank=True, default=dict, verbose_name="操作元数据")),
                ("request_method", models.CharField(blank=True, max_length=10, verbose_name="请求方法")),
                ("request_path", models.CharField(blank=True, max_length=500, verbose_name="请求路径")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="操作时间")),
                ("content_type", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="operation_logs", to="contenttypes.contenttype")),
                ("operator", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="operation_logs", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-created_at", "-id"],
                "indexes": [
                    models.Index(fields=["entity", "object_id", "created_at"], name="crm_operati_entity_885ac8_idx"),
                    models.Index(fields=["operator", "created_at"], name="crm_operati_operato_db6864_idx"),
                ],
            },
        ),
    ]
