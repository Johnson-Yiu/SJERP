from django.db import migrations


TRIGGER_NAME = "crm_operationlog_append_only_guard"
FUNCTION_NAME = "crm_operationlog_append_only_guard"


def _postgres_only(schema_editor):
    return schema_editor.connection.vendor == "postgresql"


def install_append_only_guard(apps, schema_editor):
    if not _postgres_only(schema_editor):
        return
    table = schema_editor.quote_name("crm_operationlog")
    schema_editor.execute(f"DROP TRIGGER IF EXISTS {TRIGGER_NAME} ON {table};")
    schema_editor.execute(
        f"""
        CREATE OR REPLACE FUNCTION {FUNCTION_NAME}()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION 'OperationLog rows are append-only; use the approved maintenance procedure.'
                USING ERRCODE = '42501';
        END;
        $$;
        """
    )
    schema_editor.execute(
        f"""
        CREATE TRIGGER {TRIGGER_NAME}
        BEFORE UPDATE OR DELETE ON {table}
        FOR EACH ROW EXECUTE FUNCTION {FUNCTION_NAME}();
        """
    )


def remove_append_only_guard(apps, schema_editor):
    if not _postgres_only(schema_editor):
        return
    table = schema_editor.quote_name("crm_operationlog")
    schema_editor.execute(f"DROP TRIGGER IF EXISTS {TRIGGER_NAME} ON {table};")
    schema_editor.execute(f"DROP FUNCTION IF EXISTS {FUNCTION_NAME}();")


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0087_amount_calculation_compatibility"),
    ]

    operations = [
        migrations.RunPython(install_append_only_guard, remove_append_only_guard),
    ]
