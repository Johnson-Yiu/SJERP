"""Export-only view models for saved quotations.

The renderer receives these plain values only.  It deliberately has no ORM
knowledge, so a workbook can never silently pick up changed product master
data when an old quotation is re-exported.
"""

from dataclasses import asdict, dataclass
from decimal import Decimal, ROUND_HALF_UP

from .money import LEGACY_AMOUNT_CALCULATION_VERSION, money


TWO_PLACES = Decimal("0.01")
NO_DISCOUNT_TEMPLATE_ID = "standard_en_no_discount"
WITH_DISCOUNT_TEMPLATE_ID = "standard_en_with_discount"


class QuotationExportValidationError(Exception):
    """Raised when a saved quotation cannot safely become a formal document."""

    def __init__(self, fields):
        self.fields = fields
        super().__init__("正式报价缺少关键保存字段，未生成文件。")


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
    model: str = ""


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
    return str(money(value))


def validate_quotation_export_source(quote):
    """Validate only fields required to produce a truthful saved-version file."""
    fields = {}
    if not str(quote.quote_no or "").strip():
        fields["quote_no"] = "缺少已保存报价单号。"
    if not str(quote.buyer_company_name or "").strip():
        fields["buyer_company_name"] = "缺少已保存买方公司名称。"
    currency = str(quote.currency or "").strip().upper()
    if not currency or currency in {"UNDEFINED", "NULL", "NAN"}:
        fields["currency"] = "缺少已保存报价币种。"

    items = list(quote.items.all())
    if not items:
        fields["items"] = "缺少已保存商品明细。"
    else:
        invalid_rows = []
        for index, item in enumerate(items, start=1):
            quantity = item.trade_quantity if item.trade_unit_id else item.quantity
            unit_price = item.trade_unit_price if item.trade_unit_id else item.unit_price
            if quantity is None or quantity <= 0 or unit_price is None or unit_price < 0:
                invalid_rows.append(str(index))
        if invalid_rows:
            fields["items"] = f"第 {', '.join(invalid_rows)} 行的数量或单价缺失/无效。"
    if fields:
        raise QuotationExportValidationError(fields)


def build_quotation_export_dto(quote, *, template_id=None):
    """Build a stable export view from the quotation and its saved snapshots."""
    validate_quotation_export_source(quote)
    products = []
    legacy_calculation = quote.amount_calculation_version == LEGACY_AMOUNT_CALCULATION_VERSION
    subtotal = Decimal("0")
    for item in quote.items.all():
        amount = item.amount if legacy_calculation else money(item.amount)
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
            model=item.sales_model_snapshot,
            product_name=item.product_name_snapshot,
            description=(item.description or item.product_name_snapshot) + (f"\n{item.trade_snapshot['name']}: 1 {item.trade_snapshot['unit']} = {item.trade_snapshot['factor']} {item.trade_snapshot['base_unit']}; Total {item.quantity} {item.trade_snapshot['base_unit']}" if item.trade_unit_id else ""),
            quantity=str(item.trade_quantity if item.trade_unit_id else item.quantity),
            unit=item.trade_snapshot.get("unit", item.unit_snapshot),
            unit_price=str(item.trade_unit_price if item.trade_unit_id else item.unit_price),
            amount=_money(amount),
            image_path=image_path,
        ))

    shipping_fee = money(quote.shipping_fee)
    discount = money(quote.discount)
    resolved_template_id = template_id or (
        NO_DISCOUNT_TEMPLATE_ID if discount == Decimal("0.00") else WITH_DISCOUNT_TEMPLATE_ID
    )
    total_amount = quote.total_amount if legacy_calculation else money(subtotal + shipping_fee - discount)
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
            "shipping_fee": _money(shipping_fee),
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
