"""Business rules for supplier-specific SKU records."""

from django.db import transaction
from django.utils import timezone

from crm.models import SKU, SupplierSKU


def _lock_sku(sku_id):
    return SKU.objects.select_for_update().get(pk=sku_id)


def _apply_preferred(instance):
    """Keep at most one active preferred source for an internal SKU."""
    if not instance.is_active:
        instance.is_preferred = False
    if instance.is_preferred:
        SupplierSKU.objects.filter(
            sku_id=instance.sku_id,
            is_preferred=True,
        ).exclude(pk=instance.pk).update(
            is_preferred=False,
            updated_at=timezone.now(),
        )


@transaction.atomic
def create_supplier_sku(validated_data):
    sku = _lock_sku(validated_data["sku"].pk)
    validated_data["sku"] = sku
    instance = SupplierSKU(**validated_data)
    _apply_preferred(instance)
    instance.save()
    return instance


@transaction.atomic
def update_supplier_sku(instance, validated_data):
    sku_id = validated_data.get("sku", instance.sku).pk
    locked_sku = _lock_sku(sku_id)
    for field, value in validated_data.items():
        setattr(instance, field, value)
    instance.sku = locked_sku
    _apply_preferred(instance)
    instance.save()
    return instance


@transaction.atomic
def set_preferred_supplier_sku(instance):
    locked_sku = _lock_sku(instance.sku_id)
    instance.sku = locked_sku
    instance.is_active = True
    instance.is_preferred = True
    _apply_preferred(instance)
    instance.save(update_fields=["sku", "is_active", "is_preferred", "updated_at"])
    return instance
