from django.db import migrations


TABLES = (
    "crm_historyinventorybaseline",
    "crm_historyinventorybaselinereversal",
    "crm_historyoperationalcontract",
)
FUNCTION = "crm_reject_history_truncate"


def install(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(
        "CREATE FUNCTION crm_reject_history_truncate() RETURNS trigger "
        "LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION "
        "'historical records are append-only; TRUNCATE is forbidden' "
        "USING ERRCODE = '55000'; END; $$"
    )
    for table in TABLES:
        schema_editor.execute(
            f"CREATE TRIGGER {table}_truncate_guard BEFORE TRUNCATE ON {table} "
            f"FOR EACH STATEMENT EXECUTE FUNCTION {FUNCTION}()"
        )


def uninstall(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    for table in TABLES:
        schema_editor.execute(f"DROP TRIGGER IF EXISTS {table}_truncate_guard ON {table}")
    schema_editor.execute(f"DROP FUNCTION IF EXISTS {FUNCTION}()")


def refuse_reverse_with_history(apps, schema_editor):
    for model in ("HistoryInventoryBaseline", "HistoryInventoryBaselineReversal", "HistoryOperationalContract"):
        if apps.get_model("crm", model).objects.using(schema_editor.connection.alias).exists():
            raise RuntimeError("Refusing to remove historical append-only TRUNCATE protection while records exist.")


class Migration(migrations.Migration):
    dependencies = [("crm", "0107_inventory_movement_location")]
    operations = [
        migrations.RunPython(install, uninstall),
        migrations.RunPython(migrations.RunPython.noop, refuse_reverse_with_history),
    ]
