import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


PREVIEW_TRIGGER = "crm_csv_import_preview_audit_append_only_guard"
PREVIEW_FUNCTION = "crm_csv_import_preview_audit_append_only_guard"


def install_preview_append_only_guard(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    table = schema_editor.quote_name("crm_csvimportpreviewaudit")
    schema_editor.execute(f"DROP TRIGGER IF EXISTS {PREVIEW_TRIGGER} ON {table};")
    schema_editor.execute(
        f"""
        CREATE OR REPLACE FUNCTION {PREVIEW_FUNCTION}()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION 'CSV import preview audits are append-only; use the approved maintenance procedure.'
                USING ERRCODE = '42501';
        END;
        $$;
        """
    )
    schema_editor.execute(
        f"""
        CREATE TRIGGER {PREVIEW_TRIGGER}
        BEFORE UPDATE OR DELETE ON {table}
        FOR EACH ROW EXECUTE FUNCTION {PREVIEW_FUNCTION}();
        """
    )


def remove_preview_append_only_guard(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    table = schema_editor.quote_name("crm_csvimportpreviewaudit")
    schema_editor.execute(f"DROP TRIGGER IF EXISTS {PREVIEW_TRIGGER} ON {table};")
    schema_editor.execute(f"DROP FUNCTION IF EXISTS {PREVIEW_FUNCTION}();")


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0092_merge_fulfillment_and_csv_audit"),
    ]

    operations = [
        migrations.CreateModel(
            name="CSVImportPreviewAudit",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("preview_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name="预览标识")),
                ("entity", models.CharField(max_length=30, verbose_name="数据类型")),
                ("file_sha256", models.CharField(blank=True, max_length=64, verbose_name="文件 SHA256")),
                ("endpoint", models.CharField(blank=True, max_length=120, verbose_name="预览入口")),
                ("status", models.CharField(choices=[("ready", "可执行"), ("invalid", "校验未通过"), ("failed", "解析失败")], max_length=20, verbose_name="预览结果")),
                ("total_rows", models.PositiveIntegerField(default=0, verbose_name="解析行数")),
                ("validation_errors", models.JSONField(blank=True, default=list, verbose_name="预览校验错误")),
                ("failure_reason", models.TextField(blank=True, verbose_name="失败原因")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="操作时间")),
                ("operator", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="csv_import_previews", to=settings.AUTH_USER_MODEL)),
                ("retry_of_batch", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="retry_previews", to="crm.csvimportbatch")),
            ],
            options={
                "ordering": ["-created_at", "-id"],
                "indexes": [
                    models.Index(fields=["entity", "created_at"], name="crm_csvimpo_entity_37832f_idx"),
                    models.Index(fields=["operator", "created_at"], name="crm_csvimpo_operato_7cba16_idx"),
                    models.Index(fields=["status", "created_at"], name="crm_csvimpo_status_6ee3f2_idx"),
                ],
            },
        ),
        migrations.AddField(
            model_name="csvimportbatch",
            name="preview",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="batches", to="crm.csvimportpreviewaudit"),
        ),
        migrations.RunPython(install_preview_append_only_guard, remove_preview_append_only_guard),
    ]
