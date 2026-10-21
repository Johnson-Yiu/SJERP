from __future__ import annotations

from copy import copy
from decimal import Decimal
from io import BytesIO
from pathlib import Path
import re
import zipfile
import xml.etree.ElementTree as ET

from django.core.exceptions import ObjectDoesNotExist
from openpyxl import load_workbook
from openpyxl.cell.cell import MergedCell
from openpyxl.drawing.image import Image

from crm.models import Shipment, ShipmentPackageItem


ZERO = Decimal("0")
DATA_START_ROW = 6
TEMPLATE_DATA_ROWS = 9
TEMPLATE_SUBTOTAL_ROW = 15
TEMPLATE_COLUMN_COUNT = 16
TEMPLATE_PATH = Path(__file__).resolve().parents[1] / "templates" / "packing" / "Packing List装箱单.xlsx"
XLSX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class PackingListExportError(Exception):
    def __init__(self, message, *, differences=None):
        super().__init__(message)
        self.differences = differences or []


def _decimal(value):
    return Decimal(str(value)) if value is not None else None


def _string_decimal(value):
    if value is None:
        return ""
    normalized = value.normalize()
    return format(normalized, "f")


def _shipment_inventory_movement(line):
    try:
        return line.inventory_movement
    except ObjectDoesNotExist:
        return None


def _load_shipment(shipment):
    return (
        Shipment.objects.select_related("order")
        .prefetch_related(
            "items__sku__product__hs_code",
            "items__order_item",
            "items__inventory_movement",
            "packages__items__sku__product__hs_code",
        )
        .get(pk=shipment.pk)
    )


def _sum_by_sku(rows, *, sku_getter, quantity_getter):
    totals = {}
    for row in rows:
        sku_id = sku_getter(row)
        totals[sku_id] = totals.get(sku_id, ZERO) + _decimal(quantity_getter(row))
    return totals


def packing_differences(shipment):
    shipped = _sum_by_sku(
        shipment.items.all(),
        sku_getter=lambda row: row.sku_id,
        quantity_getter=lambda row: row.quantity,
    )
    packed = _sum_by_sku(
        ShipmentPackageItem.objects.filter(shipment_package__shipment=shipment),
        sku_getter=lambda row: row.sku_id,
        quantity_getter=lambda row: row.quantity,
    )
    labels = {}
    for item in shipment.items.select_related("sku").all():
        movement = _shipment_inventory_movement(item)
        labels.setdefault(
            item.sku_id,
            getattr(movement, "sku_code_snapshot", "")
            or item.order_item.sku_code_snapshot
            or item.sku.sku,
        )
    differences = []
    for sku_id in sorted(set(shipped) | set(packed)):
        shipped_quantity = shipped.get(sku_id, ZERO)
        packed_quantity = packed.get(sku_id, ZERO)
        if shipped_quantity != packed_quantity:
            differences.append(
                {
                    "sku_id": sku_id,
                    "sku": labels.get(sku_id, f"SKU #{sku_id}"),
                    "shipped_quantity": _string_decimal(shipped_quantity),
                    "packed_quantity": _string_decimal(packed_quantity),
                    "difference": _string_decimal(shipped_quantity - packed_quantity),
                }
            )
    return differences


def _require_exportable_shipment(shipment):
    if shipment.status != "confirmed" or shipment.reversed_at:
        raise PackingListExportError("只有未冲销的已确认发货单可以导出 Packing List。")
    differences = packing_differences(shipment)
    if differences:
        raise PackingListExportError(
            "实际装箱数量与本次发货数量不一致，请先补齐实际箱单。",
            differences=differences,
        )


def _snapshot_line(shipment, sku_id):
    for line in shipment.items.all():
        if line.sku_id == sku_id:
            movement = _shipment_inventory_movement(line)
            order_item = line.order_item
            sku = line.sku
            code = (getattr(movement, "sku_code_snapshot", "") or order_item.sku_code_snapshot or sku.sku)
            name = (
                getattr(movement, "display_name_snapshot", "")
                or order_item.display_name_snapshot
                or sku.display_name_cn
                or sku.product.name_en
                or sku.product.name
            )
            description = order_item.description_snapshot or sku.description_en or sku.description_cn or sku.specification
            base_unit = (line.trade_snapshot or {}).get("base_unit") or order_item.unit_snapshot or sku.unit
            return {
                "sku": sku,
                "code": code,
                "name": name,
                "description": description,
                "base_unit": base_unit,
            }
    return None


def _physical_value(value):
    """Zero-weight defaults cannot be distinguished from an unmeasured value."""
    value = _decimal(value)
    return None if value is None or value == ZERO else value


def _dimensions(package):
    values = [_decimal(getattr(package, field)) for field in ("length", "width", "height")]
    return tuple(values) if all(value is not None and value > ZERO for value in values) else (None, None, None)


def _cbm(package, dimensions):
    if not all(dimensions):
        return None
    return (dimensions[0] * dimensions[1] * dimensions[2] / Decimal("1000000")).quantize(Decimal("0.000001"))


def _carton_label(numbers):
    labels = [f"CTN-{number:03d}" for number in numbers]
    if len(labels) == 1:
        return labels[0]
    return f"{labels[0]}–{labels[-1]}"


def _append_carton_reference(description, numbers, notes=""):
    text = description or ""
    reference = f"Carton No.: {_carton_label(numbers)}"
    if notes:
        reference = f"{reference}\nNotes: {notes}"
    return f"{text}\n{reference}" if text else reference


def _same_group(previous, current):
    return (
        previous["kind"] == "single"
        and current["kind"] == "single"
        and previous["sku_id"] == current["sku_id"]
        and previous["quantity_per_carton"] == current["quantity_per_carton"]
        and previous["dimensions"] == current["dimensions"]
        and previous["net"] == current["net"]
        and previous["gross"] == current["gross"]
        and previous["cbm"] == current["cbm"]
        and previous["notes"] == current["notes"]
        and previous["carton_numbers"][-1] + 1 == current["carton_numbers"][0]
    )


def _build_rows(shipment):
    rows = []
    for package in shipment.packages.all():
        package_items = list(package.items.all())
        dimensions = _dimensions(package)
        physical = {
            "dimensions": dimensions,
            "net": _physical_value(package.actual_net_weight),
            "gross": _physical_value(package.actual_gross_weight),
            "cbm": _cbm(package, dimensions),
            "notes": package.notes or "",
        }
        mixed = len(package_items) > 1
        for item_index, item in enumerate(package_items):
            line = _snapshot_line(shipment, item.sku_id)
            if not line:
                continue
            item_quantity = _decimal(item.quantity)
            row = {
                "kind": "mixed" if mixed else "single",
                "sku_id": item.sku_id,
                "code": line["code"],
                "name": line["name"],
                "description": line["description"],
                "sku": line["sku"],
                "quantity": item_quantity,
                "quantity_per_carton": item_quantity,
                "cartons": 1 if item_index == 0 else None,
                "carton_numbers": [package.carton_no],
                "dimensions": dimensions if item_index == 0 else (None, None, None),
                "net": physical["net"] if item_index == 0 else None,
                "gross": physical["gross"] if item_index == 0 else None,
                "cbm": physical["cbm"] if item_index == 0 else None,
                "notes": physical["notes"],
            }
            if not mixed and rows and _same_group(rows[-1], row):
                previous = rows[-1]
                previous["quantity"] += item_quantity
                previous["cartons"] += 1
                previous["carton_numbers"].append(package.carton_no)
            else:
                rows.append(row)
    return rows


def _copy_row_style(sheet, source_row, target_row):
    sheet.row_dimensions[target_row].height = sheet.row_dimensions[source_row].height
    for column in range(1, TEMPLATE_COLUMN_COUNT + 1):
        source = sheet.cell(source_row, column)
        target = sheet.cell(target_row, column)
        target._style = copy(source._style)
        target.number_format = source.number_format
        target.font = copy(source.font)
        target.fill = copy(source.fill)
        target.border = copy(source.border)
        target.alignment = copy(source.alignment)
        target.protection = copy(source.protection)


def _clear_row(sheet, row):
    for column in range(1, TEMPLATE_COLUMN_COUNT + 1):
        cell = sheet.cell(row, column)
        if not isinstance(cell, MergedCell):
            cell.value = None


def _set_cell(sheet, address, value, *, number_format=None, wrap=False):
    cell = sheet[address]
    cell.value = value
    if number_format:
        cell.number_format = number_format
    if wrap:
        alignment = copy(cell.alignment)
        alignment.wrap_text = True
        alignment.vertical = "center"
        cell.alignment = alignment


def _validate_template_structure(sheet):
    if sheet.max_column < TEMPLATE_COLUMN_COUNT:
        raise PackingListExportError("Packing List 模板缺少必要列。")
    if "A15:G15" not in {str(item) for item in sheet.merged_cells.ranges}:
        raise PackingListExportError("Packing List 模板的小计区域结构不完整。")
    if sheet.print_title_rows.replace("$", "") != "4:5":
        raise PackingListExportError("Packing List 模板未设置重复打印表头。")


def _image_path(sku):
    if not sku.image or not sku.image.name:
        return None
    try:
        path = Path(sku.image.path)
    except (NotImplementedError, ValueError, OSError):
        return None
    return path if path.is_file() else None


def _add_image(sheet, sku, row):
    path = _image_path(sku)
    if not path:
        return
    try:
        image = Image(str(path))
    except (OSError, ValueError):
        return
    image.width = 78
    image.height = 48
    image.anchor = f"C{row}"
    sheet.add_image(image)


def _write_rows(sheet, rows, data_end, *, include_hs_code=True):
    for row in range(DATA_START_ROW, data_end + 1):
        _clear_row(sheet, row)
    for index, item in enumerate(rows):
        row = DATA_START_ROW + index
        dimensions = item["dimensions"]
        description = _append_carton_reference(item["description"], item["carton_numbers"], item["notes"])
        description_lines = 1 + len(description.splitlines())
        base_height = sheet.row_dimensions[row].height or 15
        sheet.row_dimensions[row].height = max(base_height, min(90, description_lines * 15 + 8))
        _set_cell(sheet, f"A{row}", index + 1, number_format="0")
        _set_cell(sheet, f"B{row}", item["name"], wrap=True)
        _set_cell(sheet, f"D{row}", f"SKU: {item['code']}\n{description}", wrap=True)
        _set_cell(sheet, f"E{row}", item["quantity"], number_format="#,##0.##")
        hs_code = (
            item["sku"].product.hs_code.code
            if include_hs_code and item["sku"].product.hs_code_id
            else None
        )
        _set_cell(sheet, f"F{row}", hs_code or "")
        _set_cell(sheet, f"G{row}", item["quantity_per_carton"], number_format="#,##0.##")
        _set_cell(sheet, f"H{row}", item["cartons"], number_format="0")
        for column, value in zip(("I", "J", "K"), dimensions):
            _set_cell(sheet, f"{column}{row}", value, number_format="0.00")
        _set_cell(sheet, f"L{row}", item["net"], number_format="0.000")
        _set_cell(sheet, f"M{row}", f'=IF(OR(L{row}="",H{row}=""),"",L{row}*H{row})', number_format="0.000")
        _set_cell(sheet, f"N{row}", item["gross"], number_format="0.000")
        _set_cell(sheet, f"O{row}", f'=IF(OR(N{row}="",H{row}=""),"",N{row}*H{row})', number_format="0.000")
        _set_cell(sheet, f"P{row}", item["cbm"], number_format="0.000000")
        _add_image(sheet, item["sku"], row)


def _patch_template_artifacts(template_path, workbook_bytes):
    """Restore the original template's VML header logo lost by openpyxl."""
    output = {}
    with zipfile.ZipFile(BytesIO(workbook_bytes), "r") as generated:
        for info in generated.infolist():
            output[info.filename] = generated.read(info.filename)
    with zipfile.ZipFile(template_path, "r") as template:
        for name in (
            "xl/media/image1.png",
            "xl/drawings/vmlDrawing1.vml",
            "xl/drawings/_rels/vmlDrawing1.vml.rels",
            "docProps/custom.xml",
        ):
            if name in template.namelist() and name not in output:
                output[name] = template.read(name)
    ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    rel_ns = "http://schemas.openxmlformats.org/package/2006/relationships"
    office_rel_ns = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

    types = ET.fromstring(output["[Content_Types].xml"])
    existing_defaults = {node.attrib.get("Extension") for node in types.findall(f"{{{types.tag.split('}')[0].strip('{')}}}Default")}
    type_ns = types.tag.split("}")[0].strip("{")
    for extension, content_type in (
        ("vml", "application/vnd.openxmlformats-officedocument.vmlDrawing"),
        ("png", "image/png"),
    ):
        if extension not in existing_defaults:
            ET.SubElement(types, f"{{{type_ns}}}Default", Extension=extension, ContentType=content_type)
    if "docProps/custom.xml" in output and not any(
        node.attrib.get("PartName") == "/docProps/custom.xml" for node in types.findall(f"{{{type_ns}}}Override")
    ):
        ET.SubElement(
            types,
            f"{{{type_ns}}}Override",
            PartName="/docProps/custom.xml",
            ContentType="application/vnd.openxmlformats-officedocument.custom-properties+xml",
        )
    type_ns = types.tag.split("}")[0].strip("{")
    ET.register_namespace("", type_ns)
    output["[Content_Types].xml"] = ET.tostring(types, encoding="utf-8", xml_declaration=True)

    ET.register_namespace("", ns)
    ET.register_namespace("r", office_rel_ns)
    sheet_xml = ET.fromstring(output["xl/worksheets/sheet1.xml"])
    legacy = sheet_xml.find(f"{{{ns}}}legacyDrawingHF")
    if legacy is None:
        legacy = ET.SubElement(sheet_xml, f"{{{ns}}}legacyDrawingHF")
    legacy.set(f"{{{office_rel_ns}}}id", "rIdPackingLogo")
    output["xl/worksheets/sheet1.xml"] = ET.tostring(sheet_xml, encoding="utf-8", xml_declaration=True)

    rel_path = "xl/worksheets/_rels/sheet1.xml.rels"
    if rel_path in output:
        rels = ET.fromstring(output[rel_path])
    else:
        rels = ET.Element(f"{{{rel_ns}}}Relationships")
    if not any(node.attrib.get("Id") == "rIdPackingLogo" for node in rels):
        ET.SubElement(
            rels,
            f"{{{rel_ns}}}Relationship",
            Id="rIdPackingLogo",
            Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/vmlDrawing",
            Target="../drawings/vmlDrawing1.vml",
        )
    output[rel_path] = ET.tostring(rels, encoding="utf-8", xml_declaration=True)

    rebuilt = BytesIO()
    with zipfile.ZipFile(rebuilt, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in output.items():
            archive.writestr(name, content)
    return rebuilt.getvalue()


def render_packing_list_xlsx(shipment, *, include_hs_code=True):
    shipment = _load_shipment(shipment)
    _require_exportable_shipment(shipment)
    if not TEMPLATE_PATH.is_file():
        raise PackingListExportError("Packing List 模板文件不存在。")

    workbook = load_workbook(TEMPLATE_PATH)
    sheet = workbook[workbook.sheetnames[0]]
    _validate_template_structure(sheet)
    rows = _build_rows(shipment)
    if not rows:
        raise PackingListExportError("本次发货没有可导出的实际装箱明细。")

    subtotal_row = TEMPLATE_SUBTOTAL_ROW
    source_total_style_row = subtotal_row
    for merged in list(sheet.merged_cells.ranges):
        if str(merged) == f"A{subtotal_row}:G{subtotal_row}":
            sheet.unmerge_cells(str(merged))
    additional_rows = max(0, len(rows) - TEMPLATE_DATA_ROWS)
    if additional_rows:
        sheet.insert_rows(subtotal_row, additional_rows)
    total_row = subtotal_row + additional_rows
    _copy_row_style(sheet, source_total_style_row + additional_rows if additional_rows else source_total_style_row, total_row)
    for row in range(DATA_START_ROW, total_row):
        _copy_row_style(sheet, 6 if row < DATA_START_ROW + len(rows) else 8, row)
    sheet.merge_cells(f"A{total_row}:G{total_row}")

    _set_cell(sheet, "B1", shipment.shipment_no)
    _set_cell(sheet, "B2", shipment.shipment_date.isoformat())
    _set_cell(sheet, "B3", shipment.order.order_no)
    _write_rows(sheet, rows, total_row - 1, include_hs_code=include_hs_code)
    _set_cell(sheet, f"H{total_row}", f"=SUM(H{DATA_START_ROW}:H{total_row - 1})", number_format="0")
    _set_cell(sheet, f"M{total_row}", f"=SUM(M{DATA_START_ROW}:M{total_row - 1})", number_format="0.000")
    _set_cell(sheet, f"O{total_row}", f"=SUM(O{DATA_START_ROW}:O{total_row - 1})", number_format="0.000")
    _set_cell(sheet, f"P{total_row}", f"=SUM(P{DATA_START_ROW}:P{total_row - 1})", number_format="0.000000")
    sheet.print_area = f"A1:P{total_row}"
    sheet.print_title_rows = "$4:$5"
    sheet.page_setup.orientation = "landscape"
    sheet.page_setup.paperSize = sheet.PAPERSIZE_A4
    sheet.page_setup.fitToWidth = 1
    sheet.page_setup.fitToHeight = 0
    sheet.sheet_properties.pageSetUpPr.fitToPage = True
    sheet.oddFooter.center.text = "Page &P of &N"
    try:
        workbook.calculation.fullCalcOnLoad = True
        workbook.calculation.forceFullCalc = True
        workbook.calculation.calcMode = "auto"
    except AttributeError:
        pass

    output = BytesIO()
    workbook.save(output)
    return _patch_template_artifacts(TEMPLATE_PATH, output.getvalue())


def safe_packing_list_filename(shipment_no):
    safe = re.sub(r'[\\/:*?"<>|\r\n]+', "_", str(shipment_no)).strip(" .") or "shipment"
    return f"PackingList-{safe}.xlsx"
