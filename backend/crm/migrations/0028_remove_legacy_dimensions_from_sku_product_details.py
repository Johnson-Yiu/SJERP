from django.db import migrations


def remove_legacy_detail_dimensions(apps, schema_editor):
    SKU = apps.get_model("crm", "SKU")
    removed = {"model", "length", "width", "height"}
    for sku in SKU.objects.exclude(product_details=[]).iterator():
        details = sku.product_details or []
        cleaned = [
            {key: value for key, value in detail.items() if key not in removed}
            for detail in details
            if isinstance(detail, dict)
        ]
        if cleaned != details:
            sku.product_details = cleaned
            sku.save(update_fields=["product_details"])


class Migration(migrations.Migration):
    dependencies = [("crm", "0027_remove_legacy_model_from_sku_product_details")]

    operations = [migrations.RunPython(remove_legacy_detail_dimensions, migrations.RunPython.noop)]
