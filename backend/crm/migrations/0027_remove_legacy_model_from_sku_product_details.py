from django.db import migrations


def remove_legacy_detail_model(apps, schema_editor):
    SKU = apps.get_model("crm", "SKU")
    for sku in SKU.objects.exclude(product_details=[]).iterator():
        details = sku.product_details or []
        cleaned = [
            {key: value for key, value in detail.items() if key != "model"}
            for detail in details
            if isinstance(detail, dict)
        ]
        if cleaned != details:
            sku.product_details = cleaned
            sku.save(update_fields=["product_details"])


class Migration(migrations.Migration):
    dependencies = [("crm", "0026_packagingtemplate_auto_code_and_legacy_qty")]

    operations = [migrations.RunPython(remove_legacy_detail_model, migrations.RunPython.noop)]
