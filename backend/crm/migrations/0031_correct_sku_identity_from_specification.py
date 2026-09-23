from django.db import migrations


def values_for_this_sku(parameter_values, specification):
    """Legacy SKU records may contain a newline-separated selection set.
    The stored specification identifies the one value belonging to that SKU.
    """
    specification = str(specification or "").lower()
    resolved = {}
    for key, raw in (parameter_values or {}).items():
        values = [value.strip() for value in str(raw or "").replace("\r", "\n").split("\n") if value.strip()]
        matched = [value for value in values if value.lower() in specification]
        resolved[key] = matched[0] if matched else raw
    return resolved


def correct_internal_identity(apps, schema_editor):
    from crm.sku_identity import build_sku_identity

    SKU = apps.get_model("crm", "SKU")
    for sku in SKU.objects.select_related("product__category").prefetch_related("product__additional_categories", "product__category__attributes").iterator(chunk_size=200):
        parameters = values_for_this_sku(sku.parameter_values, sku.specification)
        generated = build_sku_identity(sku.product, sku.specification, parameters, sku.product_details, sku.sales_model_abbreviations)
        SKU.objects.filter(pk=sku.pk).update(
            display_name_cn=generated["display_name_cn"],
            description_cn=generated["description_cn"],
            description_en=generated["description_en"],
        )


class Migration(migrations.Migration):
    dependencies = [("crm", "0030_merge_sku_identity_and_quote_counter")]

    operations = [migrations.RunPython(correct_internal_identity, migrations.RunPython.noop)]
