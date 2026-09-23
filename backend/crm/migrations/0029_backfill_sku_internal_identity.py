from django.db import migrations


def rebuild_internal_identity(apps, schema_editor):
    # Import at runtime so the migration uses the current, single identity rule.
    from crm.sku_identity import build_sku_identity

    SKU = apps.get_model("crm", "SKU")
    for sku in SKU.objects.select_related("product__category").prefetch_related("product__additional_categories", "product__category__attributes").iterator(chunk_size=200):
        generated = build_sku_identity(sku.product, sku.specification, sku.parameter_values, sku.product_details, sku.sales_model_abbreviations)
        SKU.objects.filter(pk=sku.pk).update(
            display_name_cn=generated["display_name_cn"],
            description_cn=generated["description_cn"],
            description_en=generated["description_en"],
        )


class Migration(migrations.Migration):
    dependencies = [("crm", "0028_remove_legacy_dimensions_from_sku_product_details")]

    operations = [migrations.RunPython(rebuild_internal_identity, migrations.RunPython.noop)]
