import re

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import DocumentNumberSequence, Order, PurchaseOrder


MAX_DOCUMENT_SEQUENCE = 99999
DOCUMENT_MODELS = {
    "SO": (Order, "order_no", "销售订单"),
    "PO": (PurchaseOrder, "purchase_no", "采购订单"),
}


def _initial_last_value(document_type, year):
    model, field_name, _label = DOCUMENT_MODELS[document_type]
    pattern = re.compile(rf"^{document_type}-{year}-(\d{{5}})$")
    maximum = 0
    for number in model.objects.filter(**{f"{field_name}__startswith": f"{document_type}-{year}-"}).values_list(field_name, flat=True):
        match = pattern.fullmatch(number)
        if match:
            maximum = max(maximum, int(match.group(1)))
    return maximum


@transaction.atomic
def allocate_document_no(document_type, *, year=None):
    if document_type not in DOCUMENT_MODELS:
        raise ValueError(f"Unsupported document type: {document_type}")

    year = year or timezone.localdate().year
    try:
        sequence = DocumentNumberSequence.objects.select_for_update().get(
            document_type=document_type,
            year=year,
        )
    except DocumentNumberSequence.DoesNotExist:
        try:
            with transaction.atomic():
                sequence = DocumentNumberSequence.objects.create(
                    document_type=document_type,
                    year=year,
                    last_value=_initial_last_value(document_type, year),
                )
        except IntegrityError:
            sequence = DocumentNumberSequence.objects.select_for_update().get(
                document_type=document_type,
                year=year,
            )

    next_value = sequence.last_value + 1
    if next_value > MAX_DOCUMENT_SEQUENCE:
        _model, _field_name, label = DOCUMENT_MODELS[document_type]
        raise ValidationError(f"{year} 年{label}编号已超过 {MAX_DOCUMENT_SEQUENCE}，请扩展编号规则。")
    sequence.last_value = next_value
    sequence.save(update_fields=["last_value"])
    return f"{document_type}-{year}-{next_value:05d}"


def allocate_order_no():
    return allocate_document_no("SO")


def allocate_purchase_no():
    return allocate_document_no("PO")
