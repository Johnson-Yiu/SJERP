from pathlib import Path

from django.core.files.base import ContentFile

from .models import QuoteItem


def _copy_sku_image(item, sku_image):
    if not sku_image:
        return
    sku_image.open("rb")
    try:
        content = ContentFile(sku_image.read())
    finally:
        sku_image.close()
    item.image_snapshot.save(Path(sku_image.name).name, content, save=False)


def create_quote_items(quote, item_rows, source_items=None):
    """Create quote lines with immutable commercial/internal display snapshots."""
    from .sales_rules import check_rows
    item_rows = list(item_rows)
    checks = check_rows(quote.quote_date, item_rows, enforce=True)
    sources = list(source_items or [])
    created = []
    for index, row in enumerate(item_rows):
        values = dict(row)
        sku = values["sku"]
        source = sources[index] if index < len(sources) else None
        if source is not None and source.sku_id != sku.pk:
            source = None
        if not sku.active and (source is None or source.sku_id != sku.pk):
            from rest_framework.exceptions import ValidationError
            raise ValidationError({"sku": "新报价行不能选择停用或已归档的 SKU。"})
        manual_sales_model = values.pop("sales_model_snapshot", None)
        if source is None:
            snapshots = {
                "sku_code_snapshot": sku.sku,
                "sales_model_snapshot": sku.sales_model or "",
                "product_name_snapshot": sku.display_name_cn or sku.product.name,
                "unit_snapshot": sku.unit,
            }
        else:
            snapshots = {
                "sku_code_snapshot": source.sku_code_snapshot,
                "sales_model_snapshot": source.sales_model_snapshot,
                "product_name_snapshot": source.product_name_snapshot,
                "unit_snapshot": source.unit_snapshot,
            }
        if manual_sales_model is not None:
            snapshots["sales_model_snapshot"] = manual_sales_model
        if not values.get("description") and source is None:
            values["description"] = sku.description_en or sku.description_cn or snapshots["product_name_snapshot"]
        snapshots["sales_rules_snapshot"] = checks[index]["rules"]
        item = QuoteItem(quote=quote, **values, **snapshots)
        if source is not None and source.image_snapshot:
            item.image_snapshot.name = source.image_snapshot.name
        elif source is None and sku.image:
            _copy_sku_image(item, sku.image)
        item.save()
        created.append(item)
    return created
