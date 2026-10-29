from django.db import migrations


BATCH_TRIGGER = "crm_csv_import_batch_truncate_guard"
BATCH_FUNCTION = "crm_csv_import_batch_truncate_guard"
ROW_TRIGGER = "crm_csv_import_row_audit_truncate_guard"
ROW_FUNCTION = "crm_csv_import_row_audit_truncate_guard"


def _postgres_only(schema_editor):
    return schema_editor.connection.vendor == "postgresql"


def install_truncate_guards(apps, schema_editor):
    if not _postgres_only(schema_editor):
        return

    for table_name, trigger_name, function_name, message in (
        (
            "crm_csvimportbatch",
            BATCH_TRIGGER,
            BATCH_FUNCTION,
            "CSV import batches are append-only; TRUNCATE is not permitted.",
        ),
        (
            "crm_csvimportrowaudit",
            ROW_TRIGGER,
            ROW_FUNCTION,
            "CSV import row audits are append-only; TRUNCATE is not permitted.",
        ),
    ):
        table = schema_editor.quote_name(table_name)
        trigger = schema_editor.quote_name(trigger_name)
        function = schema_editor.quote_name(function_name)
        schema_editor.execute(f"DROP TRIGGER IF EXISTS {trigger} ON {table};")
        schema_editor.execute(
            f"""
            CREATE OR REPLACE FUNCTION {function}()
            RETURNS trigger
            LANGUAGE plpgsql
            AS $$
            BEGIN
                RAISE EXCEPTION '{message}' USING ERRCODE = '42501';
                RETURN NULL;
            END;
            $$;
            """
        )
        schema_editor.execute(
            f"""
            CREATE TRIGGER {trigger}
            BEFORE TRUNCATE ON {table}
            FOR EACH STATEMENT EXECUTE FUNCTION {function}();
            """
        )


def remove_truncate_guards(apps, schema_editor):
    if not _postgres_only(schema_editor):
        return

    for table_name, trigger_name, function_name in (
        ("crm_csvimportbatch", BATCH_TRIGGER, BATCH_FUNCTION),
        ("crm_csvimportrowaudit", ROW_TRIGGER, ROW_FUNCTION),
    ):
        table = schema_editor.quote_name(table_name)
        trigger = schema_editor.quote_name(trigger_name)
        function = schema_editor.quote_name(function_name)
        schema_editor.execute(f"DROP TRIGGER IF EXISTS {trigger} ON {table};")
        schema_editor.execute(f"DROP FUNCTION IF EXISTS {function}();")


class Migration(migrations.Migration):
    dependencies = [
        ("crm", "0092_merge_fulfillment_and_csv_audit"),
    ]

    operations = [
        # This DDL-only migration adds a TRUNCATE guard; it never changes audit rows.
        migrations.RunPython(install_truncate_guards, remove_truncate_guards),
    ]
