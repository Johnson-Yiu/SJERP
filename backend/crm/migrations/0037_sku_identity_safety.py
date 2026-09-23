import re

from django.db import migrations, models
from django.db.models import Max
from django.utils import timezone


def normalize_display_name(value):
    return " ".join(str(value or "").casefold().strip().split())


def normalize_parameter_token(value):
    return " ".join(str(value or "").casefold().strip().split())


def normalize_abbreviation_key(value):
    parts = str(value or "").split(":", 2)
    if len(parts) != 3 or not all(part.strip() for part in parts):
        return str(value or "").strip()
    category_id, attribute_key, raw_value = parts
    return f"{category_id.strip()}:{attribute_key.strip().casefold()}:{normalize_parameter_token(raw_value)}"


def normalize_sales_model_abbreviations(value):
    if not isinstance(value, dict):
        return {}
    result = {}
    for key, abbreviation in value.items():
        canonical_key = normalize_abbreviation_key(key)
        normalized_abbreviation = str(abbreviation or "").strip().upper()
        if canonical_key and normalized_abbreviation:
            result[canonical_key] = normalized_abbreviation
    return result


def values(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]
    return [part.strip() for part in str(value).replace("\r", "\n").split("\n") if part.strip()]


def with_unit(value, unit):
    value = str(value or "").strip()
    unit = str(unit or "").strip()
    if not value or not unit or value.casefold().endswith(unit.casefold()):
        return value
    return f"{value}{unit}"


def category_attributes(product):
    categories = []
    category = getattr(product, "category", None)
    while category:
        categories.append(category)
        category = category.parent
    additional = list(product.additional_categories.all()) if product.pk else []
    merged = {}
    for category in reversed(categories + additional):
        for attribute in category.attributes.all():
            merged[attribute.key.lower()] = attribute
    return list(merged.values())


def identity_signature(product, parameter_values):
    parameter_values = parameter_values if isinstance(parameter_values, dict) else {}
    pairs = []
    for attribute in category_attributes(product):
        keys = [
            f"{attribute.category_id}:{attribute.key}",
            attribute.key,
            attribute.name,
        ]
        raw = next((parameter_values[key] for key in keys if key in parameter_values), "")
        for value in values(raw):
            formatted = with_unit(value, attribute.unit)
            if attribute.uppercase:
                formatted = formatted.upper()
            pairs.append({
                "key": f"{attribute.category_id}:{attribute.key}",
                "value": formatted,
                "include_in_sku": attribute.include_in_sku,
                "include_in_sales_model": attribute.include_in_sales_model,
            })
    if not pairs:
        for key, raw in parameter_values.items():
            for value in values(raw):
                pairs.append({"key": str(key), "value": value, "include_in_sku": True, "include_in_sales_model": False})
    identity_pairs = [pair for pair in pairs if pair["include_in_sku"] or pair["include_in_sales_model"]] or pairs

    def normalized(value):
        return re.sub(r"\s+", "", str(value or "").strip()).casefold()

    signature_values = sorted(
        f"{normalized(pair['key'])}={normalized(pair['value'])}"
        for pair in identity_pairs
        if normalized(pair["value"])
    )
    return f"product={product.pk}|" + "|".join(signature_values) if signature_values else ""


def unique_renamed_display_name(original, sequence, used_keys):
    suffix = f" · #{sequence}"
    base = str(original or "SKU").strip() or "SKU"
    candidate = f"{base[: max(1, 300 - len(suffix))]}{suffix}"
    while normalize_display_name(candidate) in used_keys:
        sequence += 1
        suffix = f" · #{sequence}"
        candidate = f"{base[: max(1, 300 - len(suffix))]}{suffix}"
    return candidate


def rebuild_sku_identity_data(apps, schema_editor):
    SKU = apps.get_model("crm", "SKU")
    SKUVersion = apps.get_model("crm", "SKUVersion")
    latest_versions = dict(
        SKUVersion.objects.values("sku_id").annotate(max_version=Max("version_no")).values_list("sku_id", "max_version")
    )
    used_keys = set()
    for sku in SKU.objects.select_related("product").order_by("id").iterator(chunk_size=200):
        original_name = sku.display_name_cn or ""
        display_name = original_name
        display_name_key = normalize_display_name(display_name)
        if display_name_key and display_name_key in used_keys:
            display_name = unique_renamed_display_name(original_name, 2, used_keys)
            display_name_key = normalize_display_name(display_name)
            version_no = (latest_versions.get(sku.pk) or 0) + 1
            SKUVersion.objects.create(
                sku_id=sku.pk,
                version_no=version_no,
                sku_code_snapshot=sku.sku or "",
                sales_model_snapshot=sku.sales_model or "",
                display_name_cn_snapshot=original_name,
                description_cn_snapshot=sku.description_cn or "",
                description_en_snapshot=sku.description_en or "",
                parameter_values_snapshot=sku.parameter_values or {},
                product_details_snapshot=sku.product_details or [],
                specification_snapshot=sku.specification or "",
                changed_fields=["display_name_cn"],
                changed_at=timezone.now(),
                change_reason="迁移：清理重复的内部识别名称",
            )
            latest_versions[sku.pk] = version_no
        if display_name_key:
            used_keys.add(display_name_key)

        abbreviations = normalize_sales_model_abbreviations(sku.sales_model_abbreviations)
        signature = identity_signature(sku.product, sku.parameter_values)
        SKU.objects.filter(pk=sku.pk).update(
            display_name_cn=display_name,
            display_name_key=display_name_key,
            sales_model_abbreviations=abbreviations,
            identity_signature=signature,
        )


def blank_display_name_keys_to_null(apps, schema_editor):
    SKU = apps.get_model("crm", "SKU")
    SKU.objects.filter(display_name_key="").update(display_name_key=None)


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0036_followupattachment"),
    ]

    operations = [
        migrations.RunPython(rebuild_sku_identity_data, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="sku",
            name="display_name_key",
            field=models.CharField(blank=True, db_index=True, editable=False, max_length=300, null=True, verbose_name="内部名称规范化键"),
        ),
        migrations.RunPython(blank_display_name_keys_to_null, migrations.RunPython.noop),
        migrations.RemoveConstraint(
            model_name="sku",
            name="sku_display_name_key_unique",
        ),
        migrations.AddConstraint(
            model_name="sku",
            constraint=models.UniqueConstraint(fields=("display_name_key",), name="sku_display_name_key_unique"),
        ),
    ]
