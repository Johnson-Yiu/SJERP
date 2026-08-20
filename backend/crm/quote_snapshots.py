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
    """Create quote lines with immutable display data captured alongside each FK."""
    sources = list(source_items or [])
    created = []
    for index, row in enumerate(item_rows):
        values = dict(row)
        sku = values["sku"]
        source = sources[index] if index < len(sources) else None
        if source is None:
            snapshots = {
                "sku_code_snapshot": sku.sku,
                "product_name_snapshot": sku.product.name,
                "unit_snapshot": sku.unit,
            }
        else:
            snapshots = {
                "sku_code_snapshot": source.sku_code_snapshot,
                "product_name_snapshot": source.product_name_snapshot,
                "unit_snapshot": source.unit_snapshot,
            }
        item = QuoteItem(quote=quote, **values, **snapshots)
        if source is not None and source.image_snapshot:
            item.image_snapshot.name = source.image_snapshot.name
        elif source is None and sku.image:
            _copy_sku_image(item, sku.image)
        item.save()
        created.append(item)
    return created
