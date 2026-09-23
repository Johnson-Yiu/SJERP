from django.db import migrations, models


def two_letter_code(index):
    return f"{chr(65 + index // 26)}{chr(65 + index % 26)}"


def backfill_supplier_codes(apps, schema_editor):
    Supplier = apps.get_model("crm", "Supplier")
    for index, supplier in enumerate(Supplier.objects.order_by("id")):
        supplier.code = two_letter_code(index)
        supplier.save(update_fields=["code"])


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0037_sku_identity_safety"),
    ]

    operations = [
        migrations.AddField(
            model_name="supplier",
            name="code",
            field=models.CharField(blank=True, max_length=2, null=True, unique=True, verbose_name="供应商二字代码"),
        ),
        migrations.RunPython(backfill_supplier_codes, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="supplier",
            name="code",
            field=models.CharField(max_length=2, unique=True, verbose_name="供应商二字代码"),
        ),
        migrations.RemoveField(
            model_name="supplier",
            name="currency",
        ),
    ]
