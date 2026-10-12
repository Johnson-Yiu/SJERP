from .finance_scope import scope_transaction_queryset, require_finance_permission
"""Read-only, reusable reporting API. Decimal amounts; no cross-currency sums."""
import csv
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.db.models import Prefetch, Q
from django.http import HttpResponse
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from .models import Customer, InventoryMovement, Order, OrderItem, Product, ProductCategory, PurchaseOrder, PurchaseOrderItem, SKU, Supplier, Transaction
from .permissions import user_can
from .sales_scope import scope_customer_queryset, scope_customer_related_queryset
from .services.profit import order_profit_summary

DIMENSIONS = dict(time="时间", region="业务区域", country="国家/地区", customer="客户", supplier="供应商", product="产品", sku="SKU", category="产品主分类", owner="负责人", source="客户来源", status="状态", currency="原币币种", direction="收支方向", kind="业务类型", warehouse="仓库", type="出入库类型")
SOURCES = {
    "sales": {"label": "销售报表", "dimensions": ["time", "region", "country", "customer", "product", "sku", "category", "owner", "source", "status", "currency"], "dates": {"order_date": "订单日期", "expected_ship_date": "预计交期", "created_at": "创建时间", "updated_at": "更新时间"}, "note": "有效销售订单的合同金额；商品行之外的运费、折扣和已确认合同变更统一列为订单金额调整，不分摊 SKU。金额按订单汇率折人民币，不代表实收或利润。"},
    "purchase": {"label": "采购 / 供应商报表", "dimensions": ["time", "country", "supplier", "product", "sku", "category", "status", "currency"], "dates": {"order_date": "下单日期", "expected_arrival_date": "预计到货日", "created_at": "创建时间", "updated_at": "更新时间"}, "note": "有效采购单的合同金额；已确认合同变更作为采购金额调整独立列示，不含采购附加成本。"},
    "profit": {"label": "订单利润", "dimensions": ["time", "country", "customer", "owner", "currency"], "dates": {"order_date": "订单日期"}, "note": "金额字段表示预计订单利润 = 当前有效销售额 - 已归属采购成本 - 已确认订单费用，不等同于会计净利润。"},
    "customers": {"label": "客户增长", "dimensions": ["time", "region", "country", "customer", "owner", "source", "status"], "dates": {"created_at": "创建时间", "updated_at": "更新时间"}, "note": "按客户档案创建/更新时间统计客户数；状态、负责人、地域使用当前档案，并非历史快照。"},
    "cash": {"label": "现金收支", "dimensions": ["time", "customer", "supplier", "direction", "kind", "category", "currency"], "dates": {"transaction_date": "发生日期", "created_at": "创建时间", "updated_at": "更新时间"}, "note": "仅已确认流水；收入为正、支出为负，汇总为净现金流。优先使用实际人民币金额，否则按流水汇率折算。不重复统计预收预付分配。分类为收支分类。"},
    "inventory": {"label": "库存变动", "dimensions": ["time", "product", "sku", "category", "warehouse", "type"], "dates": {"movement_date": "发生日期", "created_at": "创建时间", "updated_at": "更新时间"}, "note": "期间出入库净变动（入正出负），不是当前库存余额。不同单位数量分别展示；金额不适用。"},
}


def bucket(day, grain):
    if grain == "day": return day.isoformat()
    if grain == "week": return (day - timedelta(days=day.weekday())).isoformat()
    if grain == "quarter": return f"{day.year}-Q{(day.month - 1) // 3 + 1}"
    if grain == "year": return str(day.year)
    return day.strftime("%Y-%m")


def identity(obj, label):
    return (str(obj.pk), str(label)) if obj else ("", "未填写")


def customer_dims(customer):
    return {"customer": identity(customer, customer.name if customer else ""), **{key: (getattr(customer, key, ""), getattr(customer, key, "") or "未填写") for key in ["country", "region", "owner", "source"]}}


def product_dims(sku):
    if not sku:
        return {key: ("__adjustment__", "订单金额调整") for key in ["product", "sku", "category"]}
    return {"sku": identity(sku, f"{sku.sku} · {sku.display_name_cn or sku.product.name}"), "product": identity(sku.product, f"{sku.product.code} · {sku.product.name}"), "category": identity(sku.product.category, sku.product.category.name if sku.product.category else "")}


def records(source, date_field, start, end, user=None):
    """Yield one item/adjustment/event at a time, keeping document IDs for distinct counts."""
    model = {"sales": Order, "purchase": PurchaseOrder, "profit": Order, "customers": Customer, "cash": Transaction, "inventory": InventoryMovement}[source]
    field = date_field + ("__date" if date_field.endswith("_at") else "")
    qs = model.objects.filter(**{field + "__range": (start, end)}).order_by("pk")
    if source in ["sales", "purchase", "profit"]:
        if source in ["sales", "profit"] and user is not None:
            qs = scope_customer_related_queryset(qs, user)
        item_model = OrderItem if source in ["sales", "profit"] else PurchaseOrderItem
        qs = qs.exclude(status__in=["draft", "cancelled"]).select_related("customer" if source in ["sales", "profit"] else "supplier").prefetch_related(Prefetch("items", queryset=item_model.objects.select_related("sku__product__category")), "contract_changes")
    elif source == "cash":
        qs = qs.filter(status="confirmed").select_related("customer", "supplier")
        if user is not None:
            qs = scope_transaction_queryset(qs, user)
    elif source == "customers" and user is not None:
        qs = scope_customer_queryset(qs, user)
    elif source == "inventory": qs = qs.select_related("sku__product__category")
    for obj in qs.iterator(chunk_size=500):
        day = getattr(obj, date_field)
        if isinstance(day, datetime): day = timezone.localtime(day).date()
        dims = {}
        for key in ["status", "currency", "direction", "kind", "warehouse", "type"]:
            value = getattr(obj, key, "")
            display = getattr(obj, f"get_{key}_display", lambda: value)()
            dims[key] = (value, display or "未填写")
        if source in ["sales", "profit", "customers", "cash"]:
            dims.update(customer_dims(obj if source == "customers" else obj.customer))
        if source in ["purchase", "cash"]:
            supplier = obj.supplier
            dims["supplier"] = identity(supplier, supplier.name if supplier else "")
            if source == "purchase":
                dims["country"] = (getattr(supplier, "country", ""), getattr(supplier, "country", "") or "未填写")
        if source == "profit":
            yield day, obj.pk, dims, order_profit_summary(obj)["estimated_profit_rmb"], Decimal(0), ""
        elif source in ["sales", "purchase"]:
            items = list(obj.items.all())
            for item in items:
                yield day, obj.pk, {**dims, **product_dims(item.sku)}, item.amount * obj.exchange_rate, item.quantity, getattr(item, "unit_snapshot", "") or item.sku.unit
            contract_changes = sum(obj.contract_changes.filter(status="approved").values_list("amount_delta", flat=True), Decimal("0"))
            adjustment = ((obj.shipping_fee - obj.discount + contract_changes) if source == "sales" else contract_changes) * obj.exchange_rate
            if adjustment or not items:
                yield day, obj.pk, {**dims, **product_dims(None)}, adjustment, Decimal(0), ""
        elif source == "cash":
            dims["category"] = (obj.category, obj.category or "未填写")
            amount = obj.rmb_amount or obj.amount * obj.exchange_rate
            yield day, obj.pk, dims, amount if obj.direction == "income" else -amount, Decimal(0), ""
        elif source == "inventory":
            yield day, obj.pk, {**dims, **product_dims(obj.sku)}, Decimal(0), obj.signed_quantity, obj.sku.unit
        else:
            yield day, obj.pk, dims, Decimal(0), Decimal(0), ""


def aggregate(source, date_field, start, end, group, grain, filters, user=None):
    groups, total_ids, quantities = {}, set(), {}
    amount = Decimal(0)
    for day, document_id, dims, value, qty, unit in records(source, date_field, start, end, user=user):
        if any(str(dims.get(key, ("", ""))[0]) != expected for key, expected in filters.items()): continue
        key, label = (bucket(day, grain), bucket(day, grain)) if group == "time" else dims[group]
        row = groups.setdefault(key, {"key": key, "label": label, "amount": Decimal(0), "quantities": {}, "ids": set()})
        row["amount"] += value
        row["ids"].add(document_id)
        total_ids.add(document_id)
        amount += value
        if unit:
            row["quantities"][unit] = row["quantities"].get(unit, Decimal(0)) + qty
            quantities[unit] = quantities.get(unit, Decimal(0)) + qty
    if group == "time":
        day = start
        while day <= end:
            key = bucket(day, grain)
            groups.setdefault(key, {"key": key, "label": key, "amount": Decimal(0), "quantities": {}, "ids": set()})
            day += timedelta(days=1)
    rows = [{**{k: v for k, v in row.items() if k != "ids"}, "count": len(row["ids"])} for row in groups.values()]
    rows.sort(key=(lambda row: row["key"]) if group == "time" else (lambda row: (-abs(row["amount"]) if source not in ["customers", "inventory"] else -row["count"], row["label"])))
    return rows, {"amount": amount, "count": len(total_ids), "quantities": quantities}


@api_view(["GET"])
def report_catalog(request):
    return Response({"sources": SOURCES, "dimensions": DIMENSIONS, "grains": dict(day="日", week="周（周一开始）", month="月", quarter="季度", year="年")})


def safe_csv(value):
    value = str(value)
    return "'" + value if value.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")) else value


def filter_summary(source, filters, user=None):
    entities = {"customer": (Customer, "name"), "supplier": (Supplier, "name"), "product": (Product, "name"), "sku": (SKU, "sku"), "category": (ProductCategory, "name")}
    result = []
    for key, value in filters.items():
        label = value or "未填写"
        if value == "__adjustment__": label = "订单金额调整"
        elif key in entities and not (source == "cash" and key == "category") and value.isdigit() and len(value) <= 18:
            model, field = entities[key]
            queryset = model.objects.all()
            if key == "customer" and user is not None:
                queryset = scope_customer_queryset(queryset, user)
            label = queryset.filter(pk=value).values_list(field, flat=True).first() or label
        result.append({"dimension": key, "name": "收支分类" if source == "cash" and key == "category" else DIMENSIONS[key], "value": value, "label": label})
    return result


@api_view(["GET"])
def report_data(request):
    if request.query_params.get("export", "").lower() in {"1", "true", "csv", "xlsx"} and not user_can(request.user, "reports", "export"):
        return Response({"detail": "你没有报表导出权限。"}, status=403)
    params = request.query_params
    source = params.get("source", "sales")
    if source not in SOURCES: raise ValidationError("不支持的报表模块。")
    if source == "cash":
        require_finance_permission(request.user, "transactions", "view")
    if source == "purchase":
        require_finance_permission(request.user, "purchases", "view")
    spec = SOURCES[source]
    group, grain = params.get("group_by", "time"), params.get("grain", "month")
    date_field = params.get("date_field") or next(iter(spec["dates"]))
    if group not in spec["dimensions"] or date_field not in spec["dates"] or grain not in ["day", "week", "month", "quarter", "year"]:
        raise ValidationError("无效的统计维度、时间粒度或日期口径。")
    try:
        start = date.fromisoformat(params.get("date_from") or timezone.localdate().replace(day=1).isoformat())
        end = date.fromisoformat(params.get("date_to") or timezone.localdate().isoformat())
        if start > end or (end - start).days > 3660 or start.year < 1900 or end.year > 9990: raise ValueError
    except ValueError:
        raise ValidationError("日期范围无效；开始日期不得晚于结束日期，单次查询最多十年。")
    filters = {}
    for key, value in params.items():
        if key.startswith("filter_"):
            dimension = key[7:]
            if dimension not in spec["dimensions"] or dimension == "time": raise ValidationError("该模块不支持此筛选维度。")
            filters[dimension] = value
    rows, totals = aggregate(source, date_field, start, end, group, grain, filters, user=request.user)
    comparison = params.get("comparison", "previous")
    if comparison not in ["previous", "year"]: raise ValidationError("无效的比较方式。")
    days = (end - start).days + 1
    previous_end = start - timedelta(days=1)
    previous_start = start - timedelta(days=days)
    if comparison == "year":
        def last_year(day):
            try: return day.replace(year=day.year - 1)
            except ValueError: return day.replace(year=day.year - 1, day=28)
        previous_start, previous_end = last_year(start), last_year(end)
    _, previous = aggregate(source, date_field, previous_start, previous_end, group, grain, filters, user=request.user)
    changes = {key: ((totals[key] - previous[key]) / abs(previous[key]) * 100 if previous[key] else None) for key in ["amount", "count"]}
    if params.get("export") == "csv":
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="report-{source}-{start}-{end}.csv"'
        response.write("\ufeff")
        writer = csv.writer(response)
        writer.writerow([spec["label"], start, end, spec["dates"][date_field], spec["note"]])
        writer.writerow(["筛选条件", safe_csv("；".join(f"{item['name']}：{item['label']}" for item in filter_summary(source, filters, user=request.user)))])
        writer.writerow(["比较期间", previous_start, previous_end])
        writer.writerow([DIMENSIONS[group], "金额（人民币）" if source not in ["customers", "inventory"] else "金额（不适用）", "去重单据/档案数", "数量（按单位）"])
        for row in rows:
            writer.writerow([safe_csv(row["label"]), str(row["amount"]) if source not in ["customers", "inventory"] else "", row["count"], safe_csv(" / ".join(f"{qty} {unit}" for unit, qty in row["quantities"].items()))])
        writer.writerow(["合计（单据去重）", str(totals["amount"]) if source not in ["customers", "inventory"] else "", totals["count"], safe_csv(" / ".join(f"{qty} {unit}" for unit, qty in totals["quantities"].items()))])
        return response
    return Response({"source": source, "group_by": group, "date_field": date_field, "date_label": spec["dates"][date_field], "grain": grain, "comparison": comparison, "period": {"date_from": start, "date_to": end}, "comparison_period": {"date_from": previous_start, "date_to": previous_end}, "totals": totals, "previous": previous, "changes": changes, "rows": rows, "note": spec["note"], "filters": filters, "filter_summary": filter_summary(source, filters, user=request.user), "generated_at": timezone.now()})

