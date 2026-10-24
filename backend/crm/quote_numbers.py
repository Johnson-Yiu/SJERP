from datetime import date

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Max

from .country_registry import AmbiguousCountryError, CountryNotFoundError, resolve_country_code
from .models import Quote, QuoteChildRevisionCounter, QuoteNumberSequence, QuoteRevisionCounter


MAX_REVISION_NO = 99


def _country_iso_code(country: str) -> str:
    if not str(country or "").strip():
        raise ValidationError({"country": "客户尚未填写国家/地区，请先在客户资料中补充后再保存报价。"})
    try:
        return resolve_country_code(country)
    except AmbiguousCountryError:
        raise ValidationError({"country": f"国家/地区“{country}”存在歧义，请在客户资料中明确选择标准国家后再保存报价。"})
    except CountryNotFoundError:
        raise ValidationError({"country": f"无法识别客户国家/地区“{country}”，请在客户资料中填写标准国家名称或国家代码后再保存报价。"})


@transaction.atomic
def allocate_root_quote_no(quote_date: date, country: str) -> str:
    country_code = _country_iso_code(country)
    try:
        sequence = QuoteNumberSequence.objects.select_for_update().get(
            quote_date=quote_date,
            country_code=country_code,
        )
    except QuoteNumberSequence.DoesNotExist:
        try:
            with transaction.atomic():
                sequence = QuoteNumberSequence.objects.create(
                    quote_date=quote_date,
                    country_code=country_code,
                )
        except IntegrityError:
            sequence = QuoteNumberSequence.objects.select_for_update().get(
                quote_date=quote_date,
                country_code=country_code,
            )

    next_sequence = sequence.last_value + 1
    if next_sequence > 999:
        raise ValidationError({"quote_no": "Daily quote sequence exceeds 999."})
    sequence.last_value = next_sequence
    sequence.save(update_fields=["last_value"])
    return f"SJ{quote_date:%Y%m%d}{country_code}{next_sequence:03d}"


def _legacy_child_revision_number(parent_quote: Quote) -> int:
    prefix = f"{parent_quote.quote_no}-"
    maximum = 0
    for quote_no in parent_quote.child_revisions.values_list("quote_no", flat=True):
        suffix = quote_no.removeprefix(prefix)
        if suffix.isdigit():
            maximum = max(maximum, int(suffix))
    return maximum


@transaction.atomic
def allocate_revision_quote_no(parent_quote: Quote) -> tuple[str, int]:
    parent_quote = Quote.objects.select_for_update().get(pk=parent_quote.pk)
    root_quote = parent_quote.root_quote or parent_quote
    if root_quote.pk != parent_quote.pk:
        root_quote = Quote.objects.select_for_update().get(pk=root_quote.pk)

    counter, created = QuoteRevisionCounter.objects.select_for_update().get_or_create(root_quote=root_quote)
    if created:
        counter.last_value = root_quote.revisions.aggregate(max_revision=Max("revision_no"))["max_revision"] or 0

    next_revision_no = counter.last_value + 1
    if next_revision_no > MAX_REVISION_NO:
        raise ValidationError({"revision_no": f"Maximum revision is {MAX_REVISION_NO}."})
    counter.last_value = next_revision_no
    counter.save(update_fields=["last_value"])

    child_counter, created = QuoteChildRevisionCounter.objects.select_for_update().get_or_create(parent_quote=parent_quote)
    if created:
        child_counter.last_value = _legacy_child_revision_number(parent_quote)
    next_child_revision = child_counter.last_value + 1
    if next_child_revision > MAX_REVISION_NO:
        raise ValidationError({"revision_no": f"Maximum child revision is {MAX_REVISION_NO}."})
    child_counter.last_value = next_child_revision
    child_counter.save(update_fields=["last_value"])
    return f"{parent_quote.quote_no}-{next_child_revision}", next_revision_no
