from django.db import migrations, models


HISTORY_DIMENSION_COLUMNS = (
    ("purchaseorder", "supplier_country_snapshot", 100),
    ("orderitem", "product_category_reference_snapshot", 64),
    ("orderitem", "product_category_name_snapshot", 120),
    ("purchaseorderitem", "product_category_reference_snapshot", 64),
    ("purchaseorderitem", "product_category_name_snapshot", 120),
)


def add_columns(apps, schema_editor):
    if schema_editor.connection.vendor not in {"sqlite", "postgresql"}:
        raise RuntimeError("History reporting snapshots require the supported SQLite or PostgreSQL database.")
    quote = schema_editor.quote_name
    for table, column, max_length in HISTORY_DIMENSION_COLUMNS:
        schema_editor.execute(
            f"ALTER TABLE {quote('crm_' + table)} ADD COLUMN {quote(column)} varchar({max_length}) NOT NULL DEFAULT ''"
        )
        if schema_editor.connection.vendor == "postgresql":
            schema_editor.execute(
                f"ALTER TABLE {quote('crm_' + table)} ALTER COLUMN {quote(column)} DROP DEFAULT"
            )


def remove_columns(apps, schema_editor):
    quote = schema_editor.quote_name
    for table, column, _max_length in reversed(HISTORY_DIMENSION_COLUMNS):
        schema_editor.execute(f"ALTER TABLE {quote('crm_' + table)} DROP COLUMN {quote(column)}")


class Migration(migrations.Migration):
    """Add point-in-time dimensions without assigning today's values to history."""

    dependencies = [("crm", "0122_merge_sales_and_finance_review")]

    operations = [migrations.SeparateDatabaseAndState(
        database_operations=[migrations.RunPython(add_columns, remove_columns)],
        state_operations=[
            migrations.AddField(model_name="purchaseorder", name="supplier_country_snapshot", field=models.CharField(blank=True, max_length=100, verbose_name="供应商国家/地区快照")),
            migrations.AddField(model_name="orderitem", name="product_category_reference_snapshot", field=models.CharField(blank=True, max_length=64, verbose_name="产品主分类来源编号快照")),
            migrations.AddField(model_name="orderitem", name="product_category_name_snapshot", field=models.CharField(blank=True, max_length=120, verbose_name="产品主分类名称快照")),
            migrations.AddField(model_name="purchaseorderitem", name="product_category_reference_snapshot", field=models.CharField(blank=True, max_length=64, verbose_name="产品主分类来源编号快照")),
            migrations.AddField(model_name="purchaseorderitem", name="product_category_name_snapshot", field=models.CharField(blank=True, max_length=120, verbose_name="产品主分类名称快照")),
        ],
    )]
