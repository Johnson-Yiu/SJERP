"""Export-only view models for saved quotations.

The renderer receives these plain values only.  It deliberately has no ORM
knowledge, so a workbook can never silently pick up changed product master
data when an old quotation is re-exported.
"""

from dataclasses import asdict, dataclass
from decimal import Decimal, ROUND_HALF_UP


TWO_PLACES = Decimal("0.01")
NO_DISCOUNT_TEMPLATE_ID = "standard_en_no_discount"
WITH_DISCOUNT_TEMPLATE_ID = "standard_en_with_discount"


@dataclass(frozen=True)
class QuotationExportItemDTO:
    sku: str
    product_name: str
    description: str
    quantity: str
    unit: str
    unit_price: str
    amount: str
    image_path: str = ""


@dataclass(frozen=True)
class QuotationExportDTO:
    template_id: str
    invoice_no: str
    buyer: dict
    terms: dict
    totals: dict
    payment_splits: dict
    products: list[QuotationExportItemDTO]

    def as_renderer_payload(self):
        payload = asdict(self)
        return payload


def _money(value):
    return str(Decimal(value).quantize(TWO_PLACES, rounding=ROUND_HALF_UP))


def build_quotation_export_dto(quote, *, template_id=None):
    """Build a stable export view from the quotation and its saved snapshots."""
    products = []
    subtotal = Decimal("0")
    for item in quote.items.all():
        amount = item.amount
        subtotal += amount
        image_path = ""
        if item.image_snapshot:
            try:
                image_path = item.image_snapshot.path
            except (NotImplementedError, ValueError):
                # Remote storage can still export the workbook; it just omits
                # the embedded image when no local readable path is available.
                pass
        products.append(QuotationExportItemDTO(
            sku=item.sku_code_snapshot,
            product_name=item.product_name_snapshot,
            description=item.description or item.product_name_snapshot,
            quantity=str(item.quantity),
            unit=item.unit_snapshot,
            unit_price=str(item.unit_price),
            amount=_money(amount),
            image_path=image_path,
        ))

    discount = Decimal(quote.discount).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    resolved_template_id = template_id or (
        NO_DISCOUNT_TEMPLATE_ID if discount == Decimal("0.00") else WITH_DISCOUNT_TEMPLATE_ID
    )
    total_amount = Decimal(quote.total_amount).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    deposit_amount = (total_amount * quote.deposit_ratio).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    validity_days = (quote.valid_until - quote.quote_date).days if quote.valid_until else 30
    return QuotationExportDTO(
        template_id=resolved_template_id,
        invoice_no=quote.quote_no,
        buyer={
            "company_name": quote.buyer_company_name,
            "recipient": quote.recipient_name,
            "address": quote.buyer_address,
            "tax_id": "",
            "email": quote.buyer_email,
            "phone": quote.buyer_phone,
        },
        terms={
            "quote_date": quote.quote_date.isoformat(),
            "validity_days": max(validity_days, 0),
            "lead_time_days": quote.lead_time_days or 10,
            "trading_terms": quote.trading_terms,
            "shipping_details": quote.shipping_details,
            "notes": quote.notes,
        },
        totals={
            "currency": quote.currency,
            "subtotal": _money(subtotal),
            "shipping_fee": _money(quote.shipping_fee),
            "discount": _money(discount),
            "total_amount": _money(total_amount),
            "amount_words": "",  # populated by the export service
        },
        payment_splits={
            "deposit_ratio": str(quote.deposit_ratio),
            "deposit_amount": _money(deposit_amount),
            "balance_ratio": str(Decimal("1") - quote.deposit_ratio),
            "balance_amount": _money(total_amount - deposit_amount),
        },
        products=products,
    )
