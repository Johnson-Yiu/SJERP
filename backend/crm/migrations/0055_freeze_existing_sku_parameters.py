from django.db import migrations


def freeze(apps, schema_editor):
    Product = apps.get_model("crm", "Product")
    Plan = apps.get_model("crm", "SKUParameterPlan")
    for product in Product.objects.using(schema_editor.connection.alias).all():
        if not product.skus.exists():
            continue
        categories = []
        category = product.category
        while category:
            categories.append(category)
            category = category.parent
        merged = {}
        for category in reversed(categories + list(product.additional_categories.all())):
            for attribute in category.attributes.all():
                merged[attribute.key.lower()] = attribute
        fields = ("category_id", "key", "name", "unit", "include_in_sku", "include_in_sales_model", "uppercase", "required", "default_value")
        definitions = [{field: getattr(attribute, field) for field in fields} for attribute in merged.values()]
        Plan.objects.using(schema_editor.connection.alias).create(product=product, version=1, status="published", definitions=definitions, baseline="")
        product.skus.update(schema_version=1)


class Migration(migrations.Migration):
    dependencies = [("crm", "0054_sku_plans_supplier_capabilities")]
    operations = [migrations.RunPython(freeze, migrations.RunPython.noop)]
