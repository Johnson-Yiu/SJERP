import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


BATCH_TRIGGER = "crm_csv_import_batch_append_only_guard"
BATCH_FUNCTION = "crm_csv_import_batch_append_only_guard"
ROW_TRIGGER = "crm_csv_import_row_audit_append_only_guard"
ROW_FUNCTION = "crm_csv_import_row_audit_append_only_guard"


def _postgres_only(schema_editor):
    return schema_editor.connection.vendor == "postgresql"


def install_append_only_guards(apps, schema_editor):
    if not _postgres_only(schema_editor):
        return
    batch_table = schema_editor.quote_name("crm_csvimportbatch")
    row_table = schema_editor.quote_name("crm_csvimportrowaudit")
    schema_editor.execute(f"DROP TRIGGER IF EXISTS {BATCH_TRIGGER} ON {batch_table};")
    schema_editor.execute(f"DROP TRIGGER IF EXISTS {ROW_TRIGGER} ON {row_table};")
    schema_editor.execute(
        f"""
        CREATE OR REPLACE FUNCTION {BATCH_FUNCTION}()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION 'CSV import batches are append-only; use the approved maintenance procedure.'
                USING ERRCODE = '42501';
        END;
        $$;
        """
    )
    schema_editor.execute(
        f"""
        CREATE OR REPLACE FUNCTION {ROW_FUNCTION}()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION 'CSV import row audits are append-only; use the approved maintenance procedure.'
                USING ERRCODE = '42501';
        END;
        $$;
        """
    )
    schema_editor.execute(
        f"""
        CREATE TRIGGER {BATCH_TRIGGER}
        BEFORE UPDATE OR DELETE ON {batch_table}
        FOR EACH ROW EXECUTE FUNCTION {BATCH_FUNCTION}();
        """
    )
    schema_editor.execute(
        f"""
        CREATE TRIGGER {ROW_TRIGGER}
        BEFORE UPDATE OR DELETE ON {row_table}
        FOR EACH ROW EXECUTE FUNCTION {ROW_FUNCTION}();
        """
    )


def remove_append_only_guards(apps, schema_editor):
    if not _postgres_only(schema_editor):
        return
    batch_table = schema_editor.quote_name("crm_csvimportbatch")
    row_table = schema_editor.quote_name("crm_csvimportrowaudit")
    schema_editor.execute(f"DROP TRIGGER IF EXISTS {BATCH_TRIGGER} ON {batch_table};")
    schema_editor.execute(f"DROP TRIGGER IF EXISTS {ROW_TRIGGER} ON {row_table};")
    schema_editor.execute(f"DROP FUNCTION IF EXISTS {BATCH_FUNCTION}();")
    schema_editor.execute(f"DROP FUNCTION IF EXISTS {ROW_FUNCTION}();")


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0089_operationlog_operator_protect"),
    ]

    operations = [
        migrations.CreateModel(
            name="CSVImportBatch",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("batch_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name="批次标识")),
                ("entity", models.CharField(max_length=30, verbose_name="数据类型")),
                ("file_sha256", models.CharField(max_length=64, verbose_name="文件 SHA256")),
                ("status", models.CharField(choices=[("succeeded", "成功"), ("failed", "失败")], max_length=20, verbose_name="批次状态")),
                ("total_rows", models.PositiveIntegerField(default=0, verbose_name="总行数")),
                ("created_rows", models.PositiveIntegerField(default=0, verbose_name="创建行数")),
                ("updated_rows", models.PositiveIntegerField(default=0, verbose_name="更新行数")),
                ("failed_rows", models.PositiveIntegerField(default=0, verbose_name="失败行数")),
                ("failure_reason", models.TextField(blank=True, verbose_name="失败原因")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="操作时间")),
                ("operator", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="csv_import_batches", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-created_at", "-id"],
                "indexes": [
                    models.Index(fields=["entity", "created_at"], name="crm_csvimpo_entity_7ab228_idx"),
                    models.Index(fields=["operator", "created_at"], name="crm_csvimpo_operato_7b4bea_idx"),
                    models.Index(fields=["status", "created_at"], name="crm_csvimpo_status_df1129_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="CSVImportRowAudit",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("row_number", models.PositiveIntegerField(verbose_name="CSV 行号")),
                ("business_key", models.CharField(max_length=255, verbose_name="业务主键")),
                ("object_id", models.CharField(blank=True, max_length=100, verbose_name="业务对象 ID")),
                ("result", models.CharField(choices=[("created", "创建"), ("updated", "更新"), ("failed", "失败")], max_length=20, verbose_name="处理结果")),
                ("before_data", models.JSONField(blank=True, default=dict, verbose_name="更新前快照")),
                ("after_data", models.JSONField(blank=True, default=dict, verbose_name="更新后快照")),
                ("error_message", models.TextField(blank=True, verbose_name="错误信息")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="记录时间")),
                ("batch", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="rows", to="crm.csvimportbatch")),
            ],
            options={
                "ordering": ["row_number", "id"],
                "indexes": [
                    models.Index(fields=["batch", "result"], name="crm_csvimpo_batch_i_aae221_idx"),
                    models.Index(fields=["business_key"], name="crm_csvimpo_busines_775f15_idx"),
                ],
                "constraints": [
                    models.UniqueConstraint(fields=("batch", "row_number"), name="crm_csv_import_batch_row_unique"),
                ],
            },
        ),
        migrations.RunPython(install_append_only_guards, remove_append_only_guards),
    ]
