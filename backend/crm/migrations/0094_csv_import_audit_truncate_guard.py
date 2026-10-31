from django.db import migrations


AUDIT_TABLES = (
    "crm_csvimportbatch",
    "crm_csvimportrowaudit",
    "crm_csvimportpreviewaudit",
)
TRUNCATE_FUNCTION = "crm_reject_csv_import_audit_truncate"
TRUNCATE_TRIGGERS = {
    "crm_csvimportbatch": "crm_csvimportbatch_truncate_guard",
    "crm_csvimportrowaudit": "crm_csvimportrowaudit_truncate_guard",
    "crm_csvimportpreviewaudit": "crm_csvimportpreviewaudit_truncate_guard",
}


def install_truncate_guards(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return

    schema_editor.execute(
        f"""
        CREATE OR REPLACE FUNCTION {TRUNCATE_FUNCTION}()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION 'CSV import audit tables are append-only; TRUNCATE is forbidden.'
                USING ERRCODE = '42501';
        END;
        $$;
        """
    )
    for table_name, trigger_name in TRUNCATE_TRIGGERS.items():
        table = schema_editor.quote_name(table_name)
        schema_editor.execute(f"DROP TRIGGER IF EXISTS {trigger_name} ON {table};")
        schema_editor.execute(
            f"""
            CREATE TRIGGER {trigger_name}
            BEFORE TRUNCATE ON {table}
            FOR EACH STATEMENT EXECUTE FUNCTION {TRUNCATE_FUNCTION}();
            """
        )


def remove_truncate_guards(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return

    for table_name, trigger_name in TRUNCATE_TRIGGERS.items():
        table = schema_editor.quote_name(table_name)
        schema_editor.execute(f"DROP TRIGGER IF EXISTS {trigger_name} ON {table};")
    schema_editor.execute(f"DROP FUNCTION IF EXISTS {TRUNCATE_FUNCTION}();")


def refuse_reverse_with_audit_history(apps, schema_editor):
    connection = schema_editor.connection
    existing_tables = set(connection.introspection.table_names())
    with connection.cursor() as cursor:
        for table_name in AUDIT_TABLES:
            if table_name not in existing_tables:
                continue
            table = schema_editor.quote_name(table_name)
            cursor.execute(f"SELECT 1 FROM {table} LIMIT 1")
            if cursor.fetchone():
                raise RuntimeError(
                    "Refusing to reverse CSV import audit protection while audit history exists; "
                    "preserve/export the history before an explicitly approved maintenance operation."
                )


class Migration(migrations.Migration):
    dependencies = [
        ("crm", "0093_csv_import_preview_audit"),
    ]

    operations = [
        migrations.RunPython(install_truncate_guards, remove_truncate_guards),
        # On rollback this check runs before the TRUNCATE guards are removed.
        # A downgrade therefore cannot proceed toward migrations that drop
        # populated audit tables.
        migrations.RunPython(migrations.RunPython.noop, refuse_reverse_with_audit_history),
    ]
