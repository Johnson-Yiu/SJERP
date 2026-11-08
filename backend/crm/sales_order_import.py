"""Preview and create sales-order drafts from source XLSX files."""

from collections import OrderedDict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from io import BytesIO
import json
import uuid
import zipfile

from django.conf import settings
from django.core import signing
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError as DRFValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from .audit import record_operation
from .models import (
    Customer,
    Order,
    SalesOrderImportBatch,
    SalesOrderImportSourceOrder,
    SKU,
    SKUTradeUnit,
)
from .permissions import is_permission_admin, user_can
from .sales_scope import scope_customer_queryset, scope_customer_related_queryset
from .serializers import OrderSerializer


TEMPLATE_FILENAME = "sales-order-import-template.xlsx"
TEMPLATE_SHEET = "订单明细"
TEMPLATE_HEADERS = [
    "来源订单编号",
    "客户编号",
    "订单日期",
    "币种",
    "SKU",
    "交易单位",
    "数量",
    "单价",
    "对人民币汇率",
]
REQUIRED_HEADERS = set(TEMPLATE_HEADERS[:-1])
PREVIEW_SALT = "crm.sales-order-import.preview"
PREVIEW_MAX_AGE_SECONDS = 30 * 60
MAX_ROWS = 5000
MAX_XLSX_FILES = 200
MAX_UNCOMPRESSED_BYTES = 80 * 1024 * 1024


class SalesOrderImportPermission(BasePermission):
    message = "你没有销售订单导入权限。"

    def has_permission(self, request, view):
        action = "view" if request.method in {"GET", "HEAD", "OPTIONS"} else "import"
        return user_can(request.user, "imports", action)


class SalesOrderImportInputError(ValueError):
    pass


def _has_order_permissions(user):
    required = (
        ("orders", "create"),
        ("customers", "view"),
        ("skus", "view"),
    )
    return all(user_can(user, module, action) for module, action in required)


def _require_order_permissions(user):
    if not _has_order_permissions(user):
        raise PermissionDenied("销售订单导入还需要订单新建、客户查看和 SKU 查看权限。")


def _require_batch_result_access(batch, user):
    same_operator = bool(
        user
        and getattr(user, "is_authenticated", False)
        and batch.operator_id == getattr(user, "pk", None)
    )
    if not same_operator and not is_permission_admin(user):
        raise PermissionDenied("只能查看本人提交的销售订单导入结果。")
    order_ids = [
        item.get("order_id")
        for item in (batch.result or {}).get("orders", [])
        if item.get("order_id")
    ]
    visible_ids = set(
        scope_customer_related_queryset(
            Order.objects.filter(pk__in=order_ids), user
        ).values_list("pk", flat=True)
    )
    if len(visible_ids) != len(order_ids):
        raise PermissionDenied("导入结果包含当前账号数据范围外的订单，不能查看完整结果。")


def _template_response():
    workbook = Workbook()
    instructions = workbook.active
    instructions.title = "使用说明"
    instructions.append(["销售订单导入模板"])
    instructions.append(["一行填写一条 SKU 明细；同一来源订单编号的多行会合并为一张销售订单草稿。"])
    instructions.append(["同一订单的客户编号、订单日期、币种和对人民币汇率必须一致。"])
    instructions.append(["编号请按文本填写并保留前导零。客户编号和 SKU 必须与系统资料完全一致。"])
    instructions.append(["交易单位填写 SKU 的基础单位或已启用交易单位；数量与单价按所填交易单位填写。"])
    instructions.append(["USD 未填汇率时按订单草稿默认值 7.2；CNY 必须为 1；其他币种请填写汇率。"])
    instructions.append(["本导入仅创建销售草稿，不确认订单、不占库存、不生成应收计划，也不登记发货。"])
    instructions.append(["已结清、已收款、已发货或需要接续的旧订单，请使用历史资料预检与承接流程。"])
    instructions.column_dimensions["A"].width = 105
    for row in instructions.iter_rows():
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
    instructions["A1"].font = Font(bold=True, size=14, color="17483E")

    sheet = workbook.create_sheet(TEMPLATE_SHEET)
    sheet.append(TEMPLATE_HEADERS)
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = f"A1:{get_column_letter(len(TEMPLATE_HEADERS))}1"
    widths = [24, 18, 16, 12, 22, 24, 14, 14, 20]
    for index, width in enumerate(widths, start=1):
        sheet.column_dimensions[get_column_letter(index)].width = width
        sheet.cell(1, index).font = Font(bold=True, color="FFFFFF")
        sheet.cell(1, index).fill = PatternFill("solid", fgColor="2F6A5D")
        sheet.cell(1, index).alignment = Alignment(wrap_text=True, vertical="center")
    for row in range(2, 202):
        for column in (1, 2, 4, 5, 6):
            sheet.cell(row, column).number_format = "@"
        sheet.cell(row, 3).number_format = "yyyy-mm-dd"
    workbook.active = 1
    output = BytesIO()
    workbook.save(output)
    workbook.close()
    response = HttpResponse(
        output.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{TEMPLATE_FILENAME}"'
    return response


def _read_upload(upload, django_request):
    if getattr(django_request, "_csv_import_upload_limit_exceeded", False):
        limit = settings.CSV_IMPORT_MAX_BYTES
        raise SalesOrderImportInputError(f"文件超过大小限制（最大 {limit:,} 字节）。")
    if upload is None:
        raise SalesOrderImportInputError("请选择销售订单 XLSX 文件。")
    if not str(upload.name or "").lower().endswith(".xlsx"):
        raise SalesOrderImportInputError("仅支持 .xlsx 文件，请使用本任务提供的模板。")
    limit = settings.CSV_IMPORT_MAX_BYTES
    if upload.size > limit:
        raise SalesOrderImportInputError(f"文件超过大小限制（最大 {limit:,} 字节）。")
    data = upload.read(limit + 1)
    if len(data) > limit:
        raise SalesOrderImportInputError(f"文件超过大小限制（最大 {limit:,} 字节）。")
    try:
        with zipfile.ZipFile(BytesIO(data)) as archive:
            infos = archive.infolist()
            if len(infos) > MAX_XLSX_FILES or sum(item.file_size for item in infos) > MAX_UNCOMPRESSED_BYTES:
                raise SalesOrderImportInputError("工作簿内容过大，无法安全预览。")
            names = {item.filename for item in infos}
            if "[Content_Types].xml" not in names or "xl/workbook.xml" not in names:
                raise SalesOrderImportInputError("文件不是有效的 XLSX 工作簿。")
    except SalesOrderImportInputError:
        raise
    except (OSError, zipfile.BadZipFile) as exc:
        raise SalesOrderImportInputError("文件不是有效的 XLSX 工作簿。") from exc
    return data, sha256(data).hexdigest()


def _text(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raw = _text(value)
    if not raw:
        raise ValueError("请填写订单日期。")
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError("订单日期请使用 YYYY-MM-DD 格式。") from exc


def _number(value, label, *, positive=False):
    raw = _text(value)
    try:
        result = Decimal(raw)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{label}请输入有效数字。") from exc
    if not result.is_finite() or result < 0 or (positive and result == 0):
        raise ValueError(f"{label}必须是{'大于 0' if positive else '不小于 0'}的有效数字。")
    return result


def _read_rows(data):
    try:
        workbook = load_workbook(BytesIO(data), read_only=True, data_only=False, keep_links=False)
    except Exception as exc:
        raise SalesOrderImportInputError("无法读取 XLSX 工作簿，请确认文件未损坏。") from exc
    try:
        if TEMPLATE_SHEET not in workbook.sheetnames:
            raise SalesOrderImportInputError(f"工作簿中缺少“{TEMPLATE_SHEET}”工作表。")
        sheet = workbook[TEMPLATE_SHEET]
        iterator = sheet.iter_rows()
        try:
            header_cells = next(iterator)
        except StopIteration as exc:
            raise SalesOrderImportInputError("模板没有表头行。") from exc
        if any(cell.data_type == "f" for cell in header_cells):
            raise SalesOrderImportInputError("模板表头不能包含公式。")
        headers = [_text(cell.value) for cell in header_cells]
        if len(headers) != len(set(headers)):
            raise SalesOrderImportInputError("表头存在重复字段，请重新下载模板。")
        if not REQUIRED_HEADERS.issubset(set(headers)):
            missing = "、".join(sorted(REQUIRED_HEADERS - set(headers)))
            raise SalesOrderImportInputError(f"缺少模板字段：{missing}。")
        unexpected = set(headers) - set(TEMPLATE_HEADERS)
        if unexpected:
            raise SalesOrderImportInputError(f"模板包含不支持的字段：{'、'.join(sorted(unexpected))}。")
        positions = {name: index for index, name in enumerate(headers)}
        rows = []
        for row_number, cells in enumerate(iterator, start=2):
            if row_number > MAX_ROWS + 1:
                raise SalesOrderImportInputError(f"最多支持 {MAX_ROWS:,} 条明细。")
            if any(cell.data_type == "f" for cell in cells):
                raise SalesOrderImportInputError(f"第 {row_number} 行包含公式，请改为普通单元格值后重试。")
            values = {name: cells[index].value if index < len(cells) else None for name, index in positions.items()}
            if not any(_text(value) for value in values.values()):
                continue
            rows.append((row_number, values))
        if not rows:
            raise SalesOrderImportInputError("工作簿没有可导入的销售订单明细。")
        return rows
    finally:
        workbook.close()


def _flatten_error(value, prefix=""):
    if isinstance(value, dict):
        parts = []
        for key, nested in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            parts.extend(_flatten_error(nested, path))
        return parts
    if isinstance(value, (list, tuple)):
        if all(not isinstance(item, (dict, list, tuple)) for item in value):
            return [f"{prefix}: {'；'.join(str(item) for item in value)}".strip(": ")]
        parts = []
        for index, nested in enumerate(value):
            path = f"{prefix}.{index}" if prefix else str(index)
            parts.extend(_flatten_error(nested, path))
        return parts
    return [f"{prefix}: {value}".strip(": ")]


def _add_error(errors, row, key, message):
    errors.append({"row": int(row), "key": str(key or ""), "message": str(message)})


def _group_rows(rows):
    groups = OrderedDict()
    errors = []
    line_count = 0
    for row_number, values in rows:
        line_count += 1
        source_order_no = _text(values.get("来源订单编号"))
        customer_code = _text(values.get("客户编号"))
        sku_code = _text(values.get("SKU"))
        group_key = source_order_no
        if not source_order_no:
            _add_error(errors, row_number, "", "请填写来源订单编号。")
            continue
        if len(source_order_no) > 160:
            _add_error(errors, row_number, source_order_no, "来源订单编号不能超过 160 个字符。")
            continue
        if source_order_no not in groups:
            groups[source_order_no] = {
                "source_order_no": source_order_no,
                "rows": [],
                "header": None,
                "errors": [],
                "payload": None,
                "customer_code": customer_code,
                "line_count": 0,
                "amount": Decimal("0"),
            }
        group = groups[group_key]
        group["line_count"] += 1
        group["rows"].append((row_number, values))
        row_errors = []
        if not customer_code:
            row_errors.append("请填写客户编号。")
        if not sku_code:
            row_errors.append("请填写 SKU。")
        unit_label = _text(values.get("交易单位"))
        if not unit_label:
            row_errors.append("请填写交易单位；按 SKU 基础单位计价时填写基础单位名称。")
        try:
            order_date = _date(values.get("订单日期"))
        except ValueError as exc:
            order_date = None
            row_errors.append(str(exc))
        currency = _text(values.get("币种")).upper()
        if not currency:
            row_errors.append("请填写币种。")
        try:
            quantity = _number(values.get("数量"), "数量", positive=True)
        except ValueError as exc:
            quantity = None
            row_errors.append(str(exc))
        try:
            unit_price = _number(values.get("单价"), "单价")
        except ValueError as exc:
            unit_price = None
            row_errors.append(str(exc))
        exchange_raw = _text(values.get("对人民币汇率"))
        try:
            exchange_rate = _number(exchange_raw, "对人民币汇率", positive=True) if exchange_raw else None
        except ValueError as exc:
            exchange_rate = None
            row_errors.append(str(exc))

        header = {
            "customer_code": customer_code,
            "order_date": order_date.isoformat() if order_date else "",
            "currency": currency,
            "exchange_rate": str(exchange_rate.normalize()) if exchange_rate is not None else "",
        }
        if group["header"] is None:
            group["header"] = header
        elif header != group["header"]:
            row_errors.append("同一来源订单编号下的客户编号、订单日期、币种和对人民币汇率必须一致。")

        for message in row_errors:
            _add_error(group["errors"], row_number, source_order_no, message)
        group["rows"][-1] = (row_number, {
            **values,
            "_customer_code": customer_code,
            "_sku_code": sku_code,
            "_unit_label": unit_label,
            "_order_date": order_date,
            "_currency": currency,
            "_quantity": quantity,
            "_unit_price": unit_price,
            "_exchange_rate": exchange_rate,
        })
    return list(groups.values()), errors, line_count


def _match_group(group, request):
    errors = list(group["errors"])
    if errors:
        return errors
    source_order_no = group["source_order_no"]
    if SalesOrderImportSourceOrder.objects.filter(source_order_no=source_order_no).exists():
        _add_error(errors, group["rows"][0][0], source_order_no, "该来源订单编号已导入，内容无论是否变更均不会重复创建；请先核对订单管理。")
        return errors
    if Order.objects.filter(order_no=source_order_no).exists():
        _add_error(errors, group["rows"][0][0], source_order_no, "该编号已用于系统销售订单，请核对订单管理后再导入。")
        return errors

    customer_code = group["header"]["customer_code"]
    customer = scope_customer_queryset(Customer.objects.all(), request.user).filter(code=customer_code).first()
    if customer is None:
        _add_error(errors, group["rows"][0][0], source_order_no, "客户编号不存在或不在当前数据范围内。")
        return errors

    items = []
    total_amount = Decimal("0")
    for item_index, (row_number, values) in enumerate(group["rows"]):
        sku = SKU.objects.filter(sku=values["_sku_code"]).select_related("product").first()
        if sku is None:
            _add_error(errors, row_number, source_order_no, f"找不到 SKU：{values['_sku_code']}。")
            continue
        if not sku.active:
            _add_error(errors, row_number, source_order_no, f"SKU {values['_sku_code']} 已停用或归档，不能用于新订单。")
            continue
        unit_label = values["_unit_label"]
        trade_unit = None
        if unit_label != sku.unit:
            candidates = list(
                SKUTradeUnit.objects.filter(sku=sku, active=True)
                .filter(unit=unit_label)
                .order_by("id")[:2]
            )
            if not candidates:
                candidates = list(
                    SKUTradeUnit.objects.filter(sku=sku, active=True, name=unit_label).order_by("id")[:2]
                )
            if len(candidates) == 1:
                trade_unit = candidates[0]
                if not user_can(request.user, "trade_units", "view"):
                    raise PermissionDenied("订单交易单位匹配需要交易单位查看权限。")
            elif len(candidates) > 1:
                _add_error(errors, row_number, source_order_no, f"SKU {values['_sku_code']} 有多个“{unit_label}”交易单位，请使用唯一单位名称。")
                continue
            else:
                _add_error(errors, row_number, source_order_no, f"SKU {values['_sku_code']} 没有启用交易单位“{unit_label}”，也不是其基础单位“{sku.unit}”。")
                continue
        if trade_unit is None:
            item = {
                "sku": sku.pk,
                "quantity": str(values["_quantity"]),
                "unit_price": str(values["_unit_price"]),
            }
        else:
            item = {
                "sku": sku.pk,
                "trade_unit": trade_unit.pk,
                "trade_quantity": str(values["_quantity"]),
                "trade_unit_price": str(values["_unit_price"]),
            }
        items.append(item)
        total_amount += values["_quantity"] * values["_unit_price"]

    if errors:
        return errors
    payload = {
        "customer": customer.pk,
        "order_date": group["header"]["order_date"],
        "currency": group["header"]["currency"],
        "items": items,
    }
    rate = group["header"]["exchange_rate"]
    if rate:
        payload["exchange_rate"] = rate
    serializer = OrderSerializer(data=payload, context={"request": request})
    if not serializer.is_valid():
        for message in _flatten_error(serializer.errors):
            index = None
            for part in message.split(":", 1)[0].split("."):
                if part.isdigit():
                    index = int(part)
                    break
            row_number = group["rows"][index][0] if index is not None and index < len(group["rows"]) else group["rows"][0][0]
            _add_error(errors, row_number, source_order_no, message)
        return errors
    group["payload"] = payload
    group["customer_code"] = customer_code
    group["customer_name"] = customer.name
    group["amount"] = total_amount.quantize(Decimal("0.01"))
    group["currency"] = group["header"]["currency"]
    return errors


def _prepare_groups(data, request):
    rows = _read_rows(data)
    groups, errors, total_rows = _group_rows(rows)
    for group in groups:
        group_errors = _match_group(group, request)
        errors.extend(group_errors)
    valid = [group for group in groups if group["payload"] is not None]
    return {
        "rows": total_rows,
        "groups": groups,
        "valid": valid,
        "errors": errors,
        "summary": [
            {
                "source_order_no": group["source_order_no"],
                "customer_code": group.get("customer_code", ""),
                "customer_name": group.get("customer_name", ""),
                "line_count": group["line_count"],
                "currency": group.get("currency", group.get("header", {}).get("currency", "")),
                "total_amount": str(group["amount"].quantize(Decimal("0.01"))),
                "valid": group["payload"] is not None,
            }
            for group in groups
        ],
    }


def _response_data(prepared, *, token=None):
    return {
        "total_rows": prepared["rows"],
        "total_orders": len(prepared["groups"]),
        "valid_orders": len(prepared["valid"]),
        "invalid_orders": len(prepared["groups"]) - len(prepared["valid"]),
        "orders": prepared["summary"],
        "errors": prepared["errors"],
        **({"preview_token": token} if token else {}),
    }


def _operator_or_none(user):
    if not getattr(user, "is_authenticated", False) or not getattr(user, "pk", None):
        return None
    try:
        user._meta.model._default_manager.get(pk=user.pk)
    except Exception:
        return None
    return user


def _group_content_digest(group):
    source = {
        "source_order_no": group["source_order_no"],
        "customer_code": group["header"]["customer_code"],
        "header": group["header"],
        "lines": [
            {
                "sku": values["_sku_code"],
                "trade_unit": values["_unit_label"],
                "quantity": str(values["_quantity"]),
                "unit_price": str(values["_unit_price"]),
            }
            for _row, values in group["rows"]
        ],
    }
    encoded = json.dumps(source, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(encoded).hexdigest()


def _execute_group(group, request, batch):
    source_order_no = group["source_order_no"]
    with transaction.atomic():
        if SalesOrderImportSourceOrder.objects.filter(source_order_no=source_order_no).exists():
            raise ValueError("该来源订单编号已导入，未创建重复订单。")
        if Order.objects.filter(order_no=source_order_no).exists():
            raise ValueError("该编号已用于系统销售订单，未创建重复订单。")
        serializer = OrderSerializer(data=group["payload"], context={"request": request})
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        source = SalesOrderImportSourceOrder.objects.create(
            source_order_no=source_order_no,
            customer_code=group["customer_code"],
            content_sha256=_group_content_digest(group),
            order=order,
            batch=batch,
        )
        record_operation(
            request=request,
            instance=order,
            action="create",
            action_label="销售订单导入创建草稿",
            metadata={"sales_order_import_source_id": source.pk, "source_order_no": source_order_no},
        )
        return {
            "source_order_no": source_order_no,
            "order_id": order.pk,
            "order_no": order.order_no,
            "status": order.status,
            "customer_code": group["customer_code"],
            "customer_name": order.customer_name_snapshot or group.get("customer_name", ""),
            "line_count": group["line_count"],
            "currency": order.currency,
            "total_amount": str(order.total_amount.quantize(Decimal("0.01"))),
        }


class SalesOrderImportTemplateView(APIView):
    permission_classes = [SalesOrderImportPermission]

    def get(self, request):
        return _template_response()


class SalesOrderImportPreviewView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [SalesOrderImportPermission]

    def post(self, request):
        _require_order_permissions(request.user)
        django_request = getattr(request, "_request", request)
        try:
            data, digest = _read_upload(request.FILES.get("file"), django_request)
            prepared = _prepare_groups(data, request)
        except SalesOrderImportInputError as exc:
            return Response({"detail": str(exc), "business_write_performed": False}, status=status.HTTP_400_BAD_REQUEST)
        except PermissionDenied:
            raise
        token = None
        if prepared["valid"]:
            token = signing.dumps(
                {
                    "preview_id": str(uuid.uuid4()),
                    "sha256": digest,
                    "operator_id": getattr(request.user, "pk", None) if request.user.is_authenticated else None,
                },
                salt=PREVIEW_SALT,
                compress=True,
            )
        payload = _response_data(prepared, token=token)
        payload["business_write_performed"] = False
        return Response(payload)


class SalesOrderImportExecuteView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [SalesOrderImportPermission]

    def post(self, request):
        _require_order_permissions(request.user)
        django_request = getattr(request, "_request", request)
        expired = False
        try:
            data, digest = _read_upload(request.FILES.get("file"), django_request)
            token = signing.loads(
                str(request.data.get("preview_token") or ""),
                salt=PREVIEW_SALT,
                max_age=PREVIEW_MAX_AGE_SECONDS,
            )
        except signing.SignatureExpired:
            # An expired preview may retrieve an existing result, never create a batch.
            token = signing.loads(str(request.data.get("preview_token") or ""), salt=PREVIEW_SALT)
            expired = True
        except (signing.BadSignature, TypeError, SalesOrderImportInputError) as exc:
            return Response({"detail": str(exc) or "预览凭证无效，请重新上传并校验。"}, status=status.HTTP_400_BAD_REQUEST)
        operator_id = getattr(request.user, "pk", None) if request.user.is_authenticated else None
        if token.get("operator_id") != operator_id:
            return Response({"detail": "预览凭证不属于当前账号，请重新校验文件。"}, status=status.HTTP_403_FORBIDDEN)
        if token.get("sha256") != digest:
            return Response({"detail": "确认文件与预览文件不同，请重新上传并校验。"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            preview_id = uuid.UUID(token["preview_id"])
        except (KeyError, ValueError, TypeError, AttributeError):
            return Response({"detail": "预览凭证无效，请重新上传并校验。"}, status=status.HTTP_400_BAD_REQUEST)

        if expired:
            batch = SalesOrderImportBatch.objects.filter(preview_id=preview_id).first()
            if batch is not None:
                _require_batch_result_access(batch, request.user)
                return Response(batch.result)
            return Response({"detail": "预览已过期且未找到已完成批次，请重新上传并校验。", "business_write_performed": False}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                batch = SalesOrderImportBatch.objects.create(
                    preview_id=preview_id,
                    file_sha256=digest,
                    operator=_operator_or_none(request.user),
                    status="failed",
                    result={},
                )
                prepared = _prepare_groups(data, request)
                errors = list(prepared["errors"])
                created_orders = []
                for group in prepared["valid"]:
                    try:
                        created_orders.append(_execute_group(group, request, batch))
                    except IntegrityError:
                        _add_error(errors, group["rows"][0][0], group["source_order_no"], "该来源订单编号刚刚完成导入，未创建重复订单。")
                    except PermissionDenied:
                        raise
                    except (DRFValidationError, DjangoValidationError, ValueError) as exc:
                        detail = getattr(exc, "detail", getattr(exc, "messages", str(exc)))
                        details = _flatten_error(detail)
                        message = "；".join(details) or "订单校验失败，未创建该订单。"
                        _add_error(errors, group["rows"][0][0], group["source_order_no"], message)

                total_orders = len(prepared["groups"])
                if created_orders and errors:
                    batch.status = "partial"
                elif created_orders:
                    batch.status = "succeeded"
                else:
                    batch.status = "failed"
                payload = {
                    "batch_id": str(batch.pk),
                    "status": batch.status,
                    "total_rows": prepared["rows"],
                    "total_orders": total_orders,
                    "created_orders": len(created_orders),
                    "failed_orders": total_orders - len(created_orders),
                    "orders": created_orders,
                    "errors": errors,
                    "business_write_performed": bool(created_orders),
                }
                batch.result = payload
                batch.save(update_fields=["status", "result"])
                record_operation(
                    request=request,
                    instance=batch,
                    action="custom",
                    action_label="销售订单 XLSX 导入完成" if created_orders else "销售订单 XLSX 导入未创建订单",
                    after=payload,
                    metadata={"file_sha256": digest, "created_orders": len(created_orders), "failed_orders": payload["failed_orders"]},
                )
                return Response(payload)
        except SalesOrderImportInputError as exc:
            return Response({"detail": str(exc), "business_write_performed": False}, status=status.HTTP_400_BAD_REQUEST)
        except IntegrityError:
            batch = SalesOrderImportBatch.objects.filter(preview_id=preview_id).first()
            if batch is not None:
                _require_batch_result_access(batch, request.user)
                return Response(batch.result)
            return Response({"detail": "导入提交冲突，请重新查看订单列表后再操作。"}, status=status.HTTP_409_CONFLICT)


class SalesOrderImportResultView(APIView):
    permission_classes = [SalesOrderImportPermission]

    def get(self, request, batch_id):
        batch = get_object_or_404(SalesOrderImportBatch, pk=batch_id)
        _require_batch_result_access(batch, request.user)
        return Response(batch.result)
