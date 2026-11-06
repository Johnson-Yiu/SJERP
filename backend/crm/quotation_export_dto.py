"""Export-only view models for saved quotations.

The renderer receives these plain values only.  It deliberately has no ORM
knowledge, so a workbook can never silently pick up changed product master
data when an old quotation is re-exported.
"""

from dataclasses import asdict, dataclass
from decimal import Decimal, ROUND_HALF_UP
from django.core.exceptions import ValidationError
from django.db import connections, transaction

from .money import LEGACY_AMOUNT_CALCULATION_VERSION, money
from .quote_template_snapshot import QuoteTemplateSnapshotError, resolve_quote_template


TWO_PLACES = Decimal("0.01")
NO_DISCOUNT_TEMPLATE_ID = "standard_en_no_discount"
WITH_DISCOUNT_TEMPLATE_ID = "standard_en_with_discount"


class QuotationExportValidationError(Exception):
    """Raised when a saved quotation cannot safely become a formal document."""

    def __init__(self, fields, *, message="正式报价缺少关键保存字段，未生成文件。"):
        self.fields = fields
        super().__init__(message)


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
    template_snapshot: dict
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


def validate_quotation_export_source(quote, *, buyer_name=None):
    """Validate only fields required to produce a truthful saved-version file."""
    fields = {}
    if not str(quote.quote_no or "").strip():
        fields["quote_no"] = "缺少已保存报价单号。"
    if not str((quote.buyer_company_name if buyer_name is None else buyer_name) or "").strip():
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


@transaction.atomic
def build_quotation_export_dto(quote, *, template_id=None):
    """Build a stable export view from the quotation and its saved snapshots."""
    from .models import Quote
    from .party_document_details_models import PartyDocumentDetailsStorage
    from .quote_party_approval_guard import validate_inherited_quote_details
    quote = Quote.objects.select_for_update().get(pk=quote.pk)
    try:
        details = validate_inherited_quote_details(quote)
    except ValidationError as exc:
        raise QuotationExportValidationError({"party_details": "报价主体资料或审批记录无效。"}) from exc
    alias = quote._state.db or 'default'
    if (details is None and PartyDocumentDetailsStorage._meta.db_table in connections[alias].introspection.table_names()
            and PartyDocumentDetailsStorage.objects.using(alias).filter(quote=quote, details__isnull=True).exists()):
        raise QuotationExportValidationError({"party_details": "报价主体资料记录为空，无法安全生成文件。"})
    if details is None:
        buyer = {"company_name": quote.buyer_company_name, "recipient": quote.recipient_name,
                 "address": quote.buyer_address, "tax_id": quote.buyer_tax_id,
                 "email": quote.buyer_email, "phone": quote.buyer_phone}
    else:
        source = details["buyer"]
        unmapped = [field for field in ("country", "contact", "billing_address", "shipping_address")
                    if source[field] not in (None, "")]
        if unmapped:
            raise QuotationExportValidationError(
                {"buyer_unmapped": "已保存的买方资料在现有模板中没有独立位置：" + ", ".join(unmapped)},
                message="现有报价模板无法完整表示已保存的买方资料，暂不能生成。",
            )
        buyer = {"company_name": source["name"], "recipient": source["recipient"],
                 "address": source["address"], "tax_id": source["tax_id"],
                 "email": source["email"], "phone": source["phone"]}
        if any(isinstance(v, str) and v.lstrip().startswith('=') for v in buyer.values()):
            raise QuotationExportValidationError({"party_details": "主体资料包含不能安全导出的公式。"})
        if not str(buyer["company_name"] or "").strip():
            raise QuotationExportValidationError({"buyer_company_name": "当前主体资料缺少买方公司名称。"})
    unknown = [key for key, value in buyer.items() if value is None]
    if unknown:
        raise QuotationExportValidationError(
            {"buyer": "买方资料存在未知字段，无法在现有模板中安全表示：" + ", ".join(unknown)},
            message="报价含未知买方资料，现有模板不能区分未知与留空，暂不能生成。",
        )
    validate_quotation_export_source(quote, buyer_name=buyer["company_name"])
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
    try:
        snapshot = resolve_quote_template(quote, resolved_template_id)
    except QuoteTemplateSnapshotError as exc:
        raise QuotationExportValidationError({"template": str(exc)}) from exc
    if details is not None:
        seller = details["seller"]
        mapping = {"name": "name", "address": "address", "contact": "saler", "email": "email", "phone": "phone"}
        if any(seller[field] is None or seller[field] != snapshot["seller"][key]
               for field, key in mapping.items()):
            raise QuotationExportValidationError({"party_details": "卖方资料与已保存报价模板不一致或未知，无法安全生成文件。"})
        if any(seller[field] not in (None, "") for field in ("country", "tax_id", "billing_address", "shipping_address", "recipient")):
            raise QuotationExportValidationError({"party_details": "卖方扩展资料在已保存报价模板中没有明确位置。"})
    total_amount = quote.total_amount if legacy_calculation else money(subtotal + shipping_fee - discount)
    deposit_amount = (total_amount * quote.deposit_ratio).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    validity_days = (quote.valid_until - quote.quote_date).days if quote.valid_until else 30
    return QuotationExportDTO(
        template_id=resolved_template_id,
        template_snapshot=snapshot,
        invoice_no=quote.quote_no,
        buyer=buyer,
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
