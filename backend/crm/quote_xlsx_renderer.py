from __future__ import annotations

from copy import copy
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO
from pathlib import Path
import re

from openpyxl import load_workbook
from openpyxl.cell.cell import MergedCell
from openpyxl.drawing.image import Image
from openpyxl.drawing.spreadsheet_drawing import AnchorMarker, OneCellAnchor
from openpyxl.drawing.xdr import XDRPositiveSize2D
from openpyxl.utils.units import pixels_to_EMU

from .quotation_template_config import QuotationTemplate, quotation_templates


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SUPPORTED_IMAGE_SUFFIXES = {".gif", ".jpg", ".jpeg", ".png", ".webp"}
MONEY_PLACES = Decimal("0.01")


class QuoteXlsxRendererError(Exception):
    """Raised when a PI workbook cannot be rendered safely."""


class QuoteTemplateNotFoundError(QuoteXlsxRendererError):
    pass


class QuoteTemplateConfigurationError(QuoteXlsxRendererError):
    pass


@dataclass(frozen=True)
class CellSnapshot:
    value: object
    style: object
    font: object
    fill: object
    border: object
    alignment: object
    protection: object
    number_format: str
    hyperlink: object
    comment: object


@dataclass(frozen=True)
class RowSnapshot:
    cells: tuple[CellSnapshot, ...]
    height: float | None
    hidden: bool
    outline_level: int
    collapsed: bool
    thick_top: bool
    thick_bottom: bool


def _money(value):
    return Decimal(str(value)).quantize(MONEY_PLACES, rounding=ROUND_HALF_UP)


def _percent_text(value):
    percent = Decimal(str(value)) * 100
    if percent == percent.to_integral_value():
        return f"{int(percent)}%"
    return f"{percent.quantize(MONEY_PLACES, rounding=ROUND_HALF_UP):f}".rstrip("0").rstrip(".") + "%"


def _notes_text(payload):
    terms = payload["terms"]
    payment = payload["payment_splits"]
    totals = payload["totals"]
    money = lambda value: f"{totals['currency']} {_money(value):.2f}"
    rows = [
        "NOTES:",
        f"1. Lead time: {terms['lead_time_days']} Days",
        f"2. Price Valid Date: {terms['validity_days']} Days.",
        "3. Payment terms:",
        (
            f"{_percent_text(payment['deposit_ratio'])} ({money(payment['deposit_amount'])}) payment in advance, "
            f"{_percent_text(payment['balance_ratio'])} ({money(payment['balance_amount'])}) balance payment "
            "should be paid before shipping"
        ),
        f"4. Trading terms: {terms.get('trading_terms') or 'N/A'}",
        f"5. Shipping details: {terms.get('shipping_details') or 'N/A'}",
        (
            "6. The price is EXCLUDE customs duties and VAT. If the goods generate the customs taxes and VAT taxes "
            "in buyer's local, the buyer should pay by themselves."
        ),
    ]
    if terms.get("notes"):
        rows.append(f"7. Additional notes: {terms['notes']}")
    return "\n".join(rows)


def _snapshot_cell(cell):
    return CellSnapshot(
        value=cell.value,
        style=copy(cell._style) if cell.has_style else None,
        font=copy(cell.font),
        fill=copy(cell.fill),
        border=copy(cell.border),
        alignment=copy(cell.alignment),
        protection=copy(cell.protection),
        number_format=cell.number_format,
        hyperlink=copy(cell.hyperlink) if cell.hyperlink else None,
        comment=copy(cell.comment) if cell.comment else None,
    )


def _snapshot_row(sheet, row):
    dimension = sheet.row_dimensions[row]
    cells = []
    for column in range(1, 14):
        cell = sheet._cells.get((row, column))
        if cell is None:
            cell = sheet.cell(row, column)
        cells.append(_snapshot_cell(cell))
    return RowSnapshot(
        cells=tuple(cells),
        height=dimension.height,
        hidden=dimension.hidden,
        outline_level=dimension.outlineLevel,
        collapsed=dimension.collapsed,
        thick_top=dimension.thickTop,
        thick_bottom=dimension.thickBot,
    )


def _restore_cell(snapshot, cell):
    cell.value = snapshot.value
    if snapshot.style is not None:
        cell._style = copy(snapshot.style)
    cell.font = copy(snapshot.font)
    cell.fill = copy(snapshot.fill)
    cell.border = copy(snapshot.border)
    cell.alignment = copy(snapshot.alignment)
    cell.protection = copy(snapshot.protection)
    cell.number_format = snapshot.number_format
    cell.hyperlink = copy(snapshot.hyperlink) if snapshot.hyperlink else None
    cell.comment = copy(snapshot.comment) if snapshot.comment else None


def _restore_row(sheet, snapshot, row):
    for column, cell_snapshot in enumerate(snapshot.cells, start=1):
        _restore_cell(cell_snapshot, sheet.cell(row, column))
    dimension = sheet.row_dimensions[row]
    dimension.height = snapshot.height
    dimension.hidden = snapshot.hidden
    dimension.outlineLevel = snapshot.outline_level
    dimension.collapsed = snapshot.collapsed
    dimension.thickTop = snapshot.thick_top
    dimension.thickBot = snapshot.thick_bottom


def _shift_range(cell_range, amount):
    return re.sub(r"\d+", lambda match: str(int(match.group()) + amount), cell_range)


def _validate_template_structure(sheet, config):
    for cell_range in config.lower_block.merges:
        if cell_range not in {str(merge) for merge in sheet.merged_cells.ranges}:
            raise QuoteTemplateConfigurationError("Quote template merged-cell structure is invalid.")
    if sheet.max_column < 13:
        raise QuoteTemplateConfigurationError("Quote template does not contain the required product columns.")


def _expand_product_area(sheet, config, additional_rows):
    if additional_rows <= 0:
        return

    lower_rows = {
        row: _snapshot_row(sheet, row)
        for row in range(config.lower_block.start_row, config.lower_block.end_row + 1)
    }
    item_source = _snapshot_row(sheet, config.item.source_row)
    for cell_range in config.lower_block.merges:
        sheet.unmerge_cells(cell_range)
    sheet.insert_rows(config.lower_block.start_row, additional_rows)

    for offset in range(additional_rows):
        target_row = config.lower_block.start_row + offset
        _restore_row(sheet, item_source, target_row)
        sheet.merge_cells(f"D{target_row}:I{target_row}")

    for row, snapshot in lower_rows.items():
        _restore_row(sheet, snapshot, row + additional_rows)
    for cell_range in config.lower_block.merges:
        sheet.merge_cells(_shift_range(cell_range, additional_rows))


def _set_value(sheet, address, value):
    sheet[address] = value


def _clear_product_row(sheet, row):
    for column in range(1, 14):
        cell = sheet._cells.get((row, column))
        if cell is None:
            cell = sheet.cell(row, column)
        if not isinstance(cell, MergedCell):
            cell.value = None


def _add_product_image(sheet, image_path, row):
    if not image_path:
        return
    image_file = Path(image_path)
    if image_file.suffix.lower() not in SUPPORTED_IMAGE_SUFFIXES:
        return
    try:
        if not image_file.is_file():
            return
        image = Image(image_file)
    except FileNotFoundError:
        return
    except OSError as exc:
        raise QuoteXlsxRendererError("Product image cannot be read.") from exc

    image.anchor = OneCellAnchor(
        _from=AnchorMarker(
            col=1,
            row=row - 1,
            colOff=pixels_to_EMU(4),
            rowOff=pixels_to_EMU(4),
        ),
        ext=XDRPositiveSize2D(cx=pixels_to_EMU(120), cy=pixels_to_EMU(90)),
    )
    sheet.add_image(image)


def _write_header_fields(sheet, config, payload):
    buyer = payload["buyer"]
    totals = payload["totals"]
    values = {
        "buyer_company": buyer.get("company_name"),
        "buyer_recipient": buyer.get("recipient"),
        "buyer_address": buyer.get("address"),
        "buyer_tax_id": buyer.get("tax_id"),
        "buyer_email": buyer.get("email"),
        "buyer_phone": buyer.get("phone"),
        "quote_date": payload["terms"].get("quote_date"),
        "invoice_no": payload.get("invoice_no"),
        "unit_price_header": f"Unit Price\n{totals['currency']}",
        "total_header": f"Total\n{totals['currency']}",
    }
    for field, value in values.items():
        _set_value(sheet, config.fields[field], value)


def _write_products(sheet, config, payload):
    products = payload.get("products", [])
    visible_rows = max(config.item.template_rows, len(products))
    for index in range(visible_rows):
        row = config.item.start_row + index
        _clear_product_row(sheet, row)
        if index >= len(products):
            continue
        product = products[index]
        _set_value(sheet, f"A{row}", index + 1)
        _set_value(sheet, f"C{row}", product.get("model") or product.get("sku") or "")
        _set_value(sheet, f"D{row}", product.get("description") or product.get("product_name") or "")
        _set_value(sheet, f"J{row}", _money(product.get("quantity", 0)))
        _set_value(sheet, f"K{row}", product.get("unit"))
        _set_value(sheet, f"L{row}", _money(product.get("unit_price", 0)))
        _set_value(sheet, f"M{row}", _money(product.get("amount", 0)))
        _add_product_image(sheet, product.get("image_path"), row)


def _write_lower_block(sheet, config, payload, additional_rows):
    rows = config.lower_block.rows
    shifted = lambda row: row + additional_rows
    totals = payload["totals"]
    _set_value(sheet, f"M{shifted(rows['shipping'])}", _money(totals["shipping_fee"]))
    if "discount" in rows:
        _set_value(sheet, f"M{shifted(rows['discount'])}", _money(totals["discount"]))
    _set_value(sheet, f"M{shifted(rows['total'])}", _money(totals["total_amount"]))
    _set_value(sheet, f"A{shifted(rows['amount_words'])}", totals["amount_words"])
    _set_value(sheet, f"A{shifted(rows['notes'])}", _notes_text(payload))


def _raise_for_cell_errors(sheet):
    for row in sheet.iter_rows():
        for cell in row:
            if cell.data_type == "e":
                raise QuoteXlsxRendererError("Generated workbook contains a formula error.")


def render_quote_xlsx(payload):
    try:
        config = quotation_templates[payload["template_id"]]
    except KeyError as exc:
        raise QuoteTemplateConfigurationError("Unknown quotation template.") from exc

    template_path = PROJECT_ROOT / config.file
    if not template_path.is_file():
        raise QuoteTemplateNotFoundError("Quote template file was not found.")

    try:
        workbook = load_workbook(template_path)
        sheet = workbook[config.sheet]
        _validate_template_structure(sheet, config)
        additional_rows = max(0, len(payload.get("products", [])) - config.item.template_rows)
        _expand_product_area(sheet, config, additional_rows)
        _write_header_fields(sheet, config, payload)
        _write_products(sheet, config, payload)
        _write_lower_block(sheet, config, payload, additional_rows)
        _raise_for_cell_errors(sheet)
        output = BytesIO()
        workbook.save(output)
        return output.getvalue()
    except QuoteXlsxRendererError:
        raise
    except Exception as exc:
        raise QuoteXlsxRendererError("PI workbook generation failed.") from exc
