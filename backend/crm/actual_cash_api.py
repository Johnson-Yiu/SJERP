"""Read-only reporting for confirmed RMB bank cash facts.

This module deliberately does not read ``Transaction.rmb_amount``.  It only
aggregates manually confirmed ``RmbCashEvent`` rows by their bank date and
keeps the result separate from the legacy book/reference reports.
"""
import csv
from datetime import date, timedelta
from decimal import Decimal

from django.http import HttpResponse
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from .models import RmbCashEvent
from .permissions import user_can
from .reporting import safe_csv
from .services import cash_events as cash


BASIS = "bank_cash_confirmed_v1"
NOTE = (
    "已登记银行资金汇总：仅含按银行日期登记且人工确认的人民币资金事件，"
    "不代表公司全部实际资金，不是利润、销售收入或银行账户余额。"
)
KIND_LABELS = {
    "fx_settlement": "外币结汇到账",
    "cny_direct": "人民币直接收付",
    "bank_fee": "独立银行扣费",
}


def _period(request):
    try:
        start = date.fromisoformat(request.query_params.get("date_from") or timezone.localdate().replace(day=1).isoformat())
        end = date.fromisoformat(request.query_params.get("date_to") or timezone.localdate().isoformat())
        if start > end or (end - start).days > 3660 or start.year < 1900 or end.year > 9990:
            raise ValueError
    except (TypeError, ValueError):
        raise ValidationError("日期范围无效；开始日期不得晚于结束日期，单次查询最多十年。")
    return start, end


def _event_row(event):
    return {
        "id": event.pk,
        "event_no": event.event_no,
        "kind": event.kind,
        "kind_label": KIND_LABELS.get(event.kind, event.kind),
        "currency": event.currency,
        "source_amount": str(event.amount),
        "direction": event.direction,
        "direction_label": "流入" if event.direction == "income" else "流出",
        "bank_date": event.bank_date,
        "bank_net_amount": str(event.bank_net_amount),
        "fee_mode": event.fee_mode,
        "fee_amount": str(event.fee_amount),
        "bank_reference": event.bank_reference,
        "status": event.status,
        "detail_url": f"/rmb-cash-events?event={event.pk}",
    }


def _visible_events(request, start, end):
    candidates = RmbCashEvent.objects.filter(status="confirmed", bank_date__range=(start, end)).order_by("bank_date", "pk")
    return [event for event in candidates if cash.visible(event, request.user)]


def _summary(events, start, end):
    inflow = Decimal("0")
    outflow = Decimal("0")
    monthly = {}
    by_kind = {}
    for event in events:
        amount = event.bank_net_amount
        if event.direction == "income":
            inflow += amount
        else:
            outflow += amount
        month = event.bank_date.strftime("%Y-%m")
        row = monthly.setdefault(month, {"month": month, "inflow": Decimal("0"), "outflow": Decimal("0"), "net": Decimal("0"), "count": 0})
        row["inflow" if event.direction == "income" else "outflow"] += amount
        row["net"] += amount if event.direction == "income" else -amount
        row["count"] += 1
        kind = by_kind.setdefault(event.kind, {"kind": event.kind, "label": KIND_LABELS.get(event.kind, event.kind), "inflow": Decimal("0"), "outflow": Decimal("0"), "net": Decimal("0"), "count": 0})
        kind["inflow" if event.direction == "income" else "outflow"] += amount
        kind["net"] += amount if event.direction == "income" else -amount
        kind["count"] += 1

    def ordered(rows):
        return sorted(rows, key=lambda row: row["month"] if "month" in row else row["kind"])

    month = start.replace(day=1)
    while month <= end:
        key = month.strftime("%Y-%m")
        monthly.setdefault(key, {"month": key, "inflow": Decimal("0"), "outflow": Decimal("0"), "net": Decimal("0"), "count": 0})
        month = (month.replace(day=28) + timedelta(days=4)).replace(day=1)
    totals = {"inflow": inflow, "outflow": outflow, "net": inflow - outflow, "count": len(events)}
    return totals, ordered(monthly.values()), ordered(by_kind.values())


def _serialize_decimal(value):
    return str(value)


@api_view(["GET"])
def actual_cash_report(request):
    """Return confirmed bank facts only; supports a CSV export of the same rows."""
    cash.access(request.user)
    start, end = _period(request)
    events = _visible_events(request, start, end)
    totals, monthly, by_kind = _summary(events, start, end)
    if request.query_params.get("export", "").lower() in {"1", "true", "csv"}:
        if not (user_can(request.user, "reports", "export") or user_can(request.user, "finance", "export")):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("你没有银行资金报表导出权限。")
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="actual-rmb-cash-{start}-{end}.csv"'
        response.write("\ufeff")
        writer = csv.writer(response)
        writer.writerow(["银行实际人民币资金", start, end, "bank_date", BASIS])
        writer.writerow([safe_csv(NOTE)])
        writer.writerow([safe_csv(value) for value in ["事件编号", "银行日期", "类型", "方向", "银行实际净额（人民币）", "含扣手续费", "手续费金额", "银行参考号"]])
        for event in events:
            writer.writerow([safe_csv(event.event_no), safe_csv(event.bank_date), safe_csv(KIND_LABELS.get(event.kind, event.kind)), safe_csv("流入" if event.direction == "income" else "流出"), _serialize_decimal(event.bank_net_amount), event.fee_mode == "included", _serialize_decimal(event.fee_amount), safe_csv(event.bank_reference)])
        writer.writerow([safe_csv("合计"), "", "", safe_csv("流入"), _serialize_decimal(totals["inflow"]), "", "", ""])
        writer.writerow([safe_csv("合计"), "", "", safe_csv("流出"), _serialize_decimal(totals["outflow"]), "", "", ""])
        writer.writerow([safe_csv("净流入/净流出"), "", "", "", _serialize_decimal(totals["net"]), "", "", ""])
        return response
    def encode(row):
        return {key: (_serialize_decimal(value) if isinstance(value, Decimal) else value) for key, value in row.items()}
    return Response({
        "basis": BASIS,
        "version": 1,
        "date_basis": "bank_date",
        "coverage_status": "registered_confirmed_only",
        "coverage_since": None,
        "coverage_configured": False,
        "period": {"date_from": start, "date_to": end},
        "totals": encode(totals),
        "monthly": [encode(row) for row in monthly],
        "by_kind": [encode(row) for row in by_kind],
        "events": [_event_row(event) for event in events],
        "note": NOTE,
    })
