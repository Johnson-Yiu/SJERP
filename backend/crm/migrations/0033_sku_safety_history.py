from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


def backfill_sku_safety_data(apps, schema_editor):
    from crm.sku_identity import identity_signature

    SKU = apps.get_model("crm", "SKU")
    PurchaseOrderItem = apps.get_model("crm", "PurchaseOrderItem")
    InventoryMovement = apps.get_model("crm", "InventoryMovement")
    signatures = {}
    for sku in SKU.objects.select_related("product__category").prefetch_related("product__additional_categories", "product__category__attributes").iterator(chunk_size=200):
        signature = identity_signature(sku.product, sku.parameter_values)
        SKU.objects.filter(pk=sku.pk).update(identity_signature=signature)
        if signature:
            signatures.setdefault((sku.product_id, signature), []).append(sku.sku)
    conflicts = [codes for codes in signatures.values() if len(codes) > 1]
    if conflicts:
        # Existing data remains valid. The report is deliberately emitted rather
        # than failing deployment or silently deleting/merging SKU records.
        print("SKU identity-signature conflicts retained for manual review:", conflicts)

    for item in PurchaseOrderItem.objects.select_related("sku__product").iterator(chunk_size=200):
        sku = item.sku
        item.sku_code_snapshot = item.sku_code_snapshot or sku.sku
        item.sales_model_snapshot = item.sales_model_snapshot or sku.sales_model or ""
        item.display_name_snapshot = item.display_name_snapshot or sku.display_name_cn or sku.product.name
        item.description_snapshot = item.description_snapshot or sku.description_en or sku.description_cn or item.display_name_snapshot
        item.save(update_fields=["sku_code_snapshot", "sales_model_snapshot", "display_name_snapshot", "description_snapshot"])

    for movement in InventoryMovement.objects.select_related("sku__product").iterator(chunk_size=200):
        sku = movement.sku
        movement.sku_code_snapshot = movement.sku_code_snapshot or sku.sku
        movement.sales_model_snapshot = movement.sales_model_snapshot or sku.sales_model or ""
        movement.display_name_snapshot = movement.display_name_snapshot or sku.display_name_cn or sku.product.name
        movement.save(update_fields=["sku_code_snapshot", "sales_model_snapshot", "display_name_snapshot"])


class Migration(migrations.Migration):
    dependencies = [
        ("crm", "0032_currency_amount_precision"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="sku",
            name="identity_signature",
            field=models.CharField(blank=True, db_index=True, max_length=500, verbose_name="身份参数签名"),
        ),
        migrations.CreateModel(
            name="SKUVersion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("version_no", models.PositiveIntegerField(verbose_name="版本号")),
                ("sku_code_snapshot", models.CharField(max_length=80, verbose_name="SKU 编码快照")),
                ("sales_model_snapshot", models.CharField(blank=True, max_length=80, verbose_name="销售型号快照")),
                ("display_name_cn_snapshot", models.CharField(blank=True, max_length=300, verbose_name="内部名称快照")),
                ("description_cn_snapshot", models.TextField(blank=True, verbose_name="中文描述快照")),
                ("description_en_snapshot", models.TextField(blank=True, verbose_name="英文描述快照")),
                ("parameter_values_snapshot", models.JSONField(default=dict, verbose_name="参数快照")),
                ("product_details_snapshot", models.JSONField(default=list, verbose_name="产品明细快照")),
                ("specification_snapshot", models.CharField(blank=True, max_length=200, verbose_name="规格快照")),
                ("changed_fields", models.JSONField(default=list, verbose_name="变更字段")),
                ("changed_at", models.DateTimeField(default=django.utils.timezone.now, verbose_name="变更时间")),
                ("change_reason", models.CharField(blank=True, max_length=300, verbose_name="变更说明")),
                ("changed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="sku_versions", to=settings.AUTH_USER_MODEL)),
                ("sku", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="versions", to="crm.sku")),
            ],
            options={"ordering": ["-version_no"]},
        ),
        migrations.AddConstraint(model_name="skuversion", constraint=models.UniqueConstraint(fields=("sku", "version_no"), name="unique_sku_version_no")),
        migrations.AddField(model_name="purchaseorderitem", name="sku_code_snapshot", field=models.CharField(blank=True, max_length=80, verbose_name="SKU 编码快照")),
        migrations.AddField(model_name="purchaseorderitem", name="sales_model_snapshot", field=models.CharField(blank=True, max_length=80, verbose_name="销售型号快照")),
        migrations.AddField(model_name="purchaseorderitem", name="display_name_snapshot", field=models.CharField(blank=True, max_length=300, verbose_name="显示名称快照")),
        migrations.AddField(model_name="purchaseorderitem", name="description_snapshot", field=models.TextField(blank=True, verbose_name="描述快照")),
        migrations.AddField(model_name="inventorymovement", name="sku_code_snapshot", field=models.CharField(blank=True, max_length=80, verbose_name="SKU 编码快照")),
        migrations.AddField(model_name="inventorymovement", name="sales_model_snapshot", field=models.CharField(blank=True, max_length=80, verbose_name="销售型号快照")),
        migrations.AddField(model_name="inventorymovement", name="display_name_snapshot", field=models.CharField(blank=True, max_length=300, verbose_name="显示名称快照")),
        migrations.RunPython(backfill_sku_safety_data, migrations.RunPython.noop),
    ]
