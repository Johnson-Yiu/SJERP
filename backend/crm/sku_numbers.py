from django.db import transaction

from .models import SKU, SKUCodeSequence


@transaction.atomic
def allocate_sku_code():
    sequence, _ = SKUCodeSequence.objects.select_for_update().get_or_create(pk=1)
    while True:
        sequence.last_value += 1
        candidate = f"SKU-{sequence.last_value:06d}"
        if not SKU.objects.filter(sku=candidate).exists():
            sequence.save(update_fields=["last_value"])
            return candidate
