from pathlib import Path
from uuid import uuid4

from django.core.files import File
from django.db import migrations, models


def populate_saved_pi_snapshots(apps, schema_editor):
    Quote = apps.get_model("crm", "Quote")
    QuoteItem = apps.get_model("crm", "QuoteItem")

    for quote in Quote.objects.select_related("customer").iterator():
        quote.buyer_company_name = quote.customer.name
        quote.save(update_fields=["buyer_company_name"])

    for item in QuoteItem.objects.select_related("sku__product").iterator():
        item.sku_code_snapshot = item.sku.sku
        item.product_name_snapshot = item.sku.product.name
        item.unit_snapshot = item.sku.unit
        update_fields = ["sku_code_snapshot", "product_name_snapshot", "unit_snapshot"]
        if item.sku.image:
            storage = item.sku.image.storage
            source_name = item.sku.image.name
            if storage.exists(source_name):
                suffix = Path(source_name).suffix
                snapshot_name = f"quote-item-images/migrated/{uuid4().hex}{suffix}"
                with storage.open(source_name, "rb") as source:
                    item.image_snapshot = storage.save(snapshot_name, File(source))
                update_fields.append("image_snapshot")
        item.save(update_fields=update_fields)


class Migration(migrations.Migration):
    dependencies = [("crm", "0011_quote_pi_fields_and_sku_image")]

    operations = [
        migrations.AddField(
            model_name="quote",
            name="buyer_company_name",
            field=models.CharField(blank=True, max_length=200, verbose_name="买方公司快照"),
        ),
        migrations.AddField(
            model_name="quoteitem",
            name="image_snapshot",
            field=models.ImageField(blank=True, upload_to="quote-item-images/%Y/%m/", verbose_name="产品图片快照"),
        ),
        migrations.AddField(
            model_name="quoteitem",
            name="product_name_snapshot",
            field=models.CharField(blank=True, max_length=200, verbose_name="产品名称快照"),
        ),
        migrations.AddField(
            model_name="quoteitem",
            name="sku_code_snapshot",
            field=models.CharField(blank=True, max_length=80, verbose_name="SKU 编码快照"),
        ),
        migrations.AddField(
            model_name="quoteitem",
            name="unit_snapshot",
            field=models.CharField(blank=True, max_length=30, verbose_name="单位快照"),
        ),
        migrations.RunPython(populate_saved_pi_snapshots, migrations.RunPython.noop),
    ]
