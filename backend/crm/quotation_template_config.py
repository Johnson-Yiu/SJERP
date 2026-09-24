from dataclasses import dataclass


@dataclass(frozen=True)
class ItemArea:
    start_row: int
    template_rows: int
    source_row: int


@dataclass(frozen=True)
class LowerBlock:
    start_row: int
    end_row: int
    merges: tuple[str, ...]
    rows: dict[str, int]


@dataclass(frozen=True)
class QuotationTemplate:
    file: str
    sheet: str
    fields: dict[str, str]
    item: ItemArea
    lower_block: LowerBlock


def _bank_merges(start_row):
    return (
        *(f"A{row}:B{row}" for row in range(start_row, start_row + 9)),
        *(f"C{row}:M{row}" for row in range(start_row, start_row + 9)),
    )


quotation_templates = {
    "standard_en_no_discount": QuotationTemplate(
        file="templates/quotation/报价单模板_无折扣.xlsx",
        sheet="PI",
        fields={
            "buyer_company": "B3",
            "buyer_recipient": "B4",
            "buyer_address": "B5",
            "buyer_tax_id": "B6",
            "buyer_email": "B7",
            "buyer_phone": "B8",
            "quote_date": "I8",
            "invoice_no": "L9",
            "unit_price_header": "L10",
            "total_header": "M10",
        },
        item=ItemArea(start_row=11, template_rows=2, source_row=12),
        lower_block=LowerBlock(
            start_row=13,
            end_row=34,
            merges=(
                "A13:L13", "A14:L14", "A15:M15", "A16:M20", "A21:M21",
                *_bank_merges(22),
                "A31:M33", "A34:M34",
            ),
            rows={
                "shipping": 13,
                "total": 14,
                "amount_words": 15,
                "notes": 16,
                "bank_header": 21,
                "end": 34,
            },
        ),
    ),
    "standard_en_with_discount": QuotationTemplate(
        file="templates/quotation/报价单模板_有折扣.xlsx",
        sheet="PI",
        fields={
            "buyer_company": "B3",
            "buyer_recipient": "B4",
            "buyer_address": "B5",
            "buyer_tax_id": "B6",
            "buyer_email": "B7",
            "buyer_phone": "B8",
            "quote_date": "I8",
            "invoice_no": "L9",
            "unit_price_header": "L10",
            "total_header": "M10",
        },
        item=ItemArea(start_row=11, template_rows=2, source_row=12),
        lower_block=LowerBlock(
            start_row=13,
            end_row=35,
            merges=(
                "A13:L13", "A14:L14", "A15:L15", "A16:M16", "A17:M21", "A22:M22",
                *_bank_merges(23),
                "A32:M34", "A35:M35",
            ),
            rows={
                "shipping": 13,
                "discount": 14,
                "total": 15,
                "amount_words": 16,
                "notes": 17,
                "bank_header": 22,
                "end": 35,
            },
        ),
    ),
}
