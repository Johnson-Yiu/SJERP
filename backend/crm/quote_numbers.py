from datetime import date

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Max

from .models import Quote, QuoteNumberSequence, QuoteRevisionCounter


COUNTRY_ISO_CODES = {
    "australia": "AU",
    "brazil": "BR",
    "canada": "CA",
    "china": "CN",
    "france": "FR",
    "germany": "DE",
    "india": "IN",
    "italy": "IT",
    "japan": "JP",
    "mexico": "MX",
    "netherlands": "NL",
    "new zealand": "NZ",
    "saudi arabia": "SA",
    "singapore": "SG",
    "south korea": "KR",
    "spain": "ES",
    "united arab emirates": "AE",
    "united kingdom": "GB",
    "united states": "US",
    "united states of america": "US",
    "usa": "US",
}
MAX_REVISION_NO = 99


def _country_iso_code(country: str) -> str:
    country_code = COUNTRY_ISO_CODES.get(country.strip().casefold())
    if not country_code:
        raise ValidationError({"country": f"Unsupported country: {country}"})
    return country_code


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


@transaction.atomic
def allocate_revision_quote_no(root_quote: Quote) -> tuple[str, int]:
    root_quote = Quote.objects.select_for_update().get(pk=root_quote.pk)
    if root_quote.root_quote_id is not None:
        raise ValidationError({"root_quote": "A revision cannot be used as a root quote."})

    counter, created = QuoteRevisionCounter.objects.select_for_update().get_or_create(root_quote=root_quote)
    if created:
        counter.last_value = root_quote.revisions.aggregate(max_revision=Max("revision_no"))["max_revision"] or 0

    next_revision_no = counter.last_value + 1
    if next_revision_no > MAX_REVISION_NO:
        raise ValidationError({"revision_no": f"Maximum revision is {MAX_REVISION_NO}."})
    counter.last_value = next_revision_no
    counter.save(update_fields=["last_value"])
    return f"{root_quote.quote_no}-{next_revision_no}", next_revision_no
