from .finance_basis import BOOK_RMB_BASIS, BOOK_RMB_VERSION, BOOK_RMB_NOTE
from .finance_scope import scope_transaction_queryset, require_finance_permission
"""Read-only, reusable reporting API. Decimal amounts; no cross-currency sums."""
import csv
import json
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.core.paginator import Paginator
from django.db.models import Prefetch, Q
from django.http import HttpResponse
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from .models import Customer, InventoryMovement, Order, OrderItem, Product, ProductCategory, PurchaseOrder, PurchaseOrderItem, RmbCashEvent, SKU, Supplier, Transaction
from .permissions import HistoricalAnalysisPermission, user_can
from .sales_scope import scope_customer_queryset, scope_customer_related_queryset
from .services.profit import order_profit_summary
from .services import cash_events as cash

DIMENSIONS = dict(time="时间", region="业务区域", country="国家/地区", customer="客户", supplier="供应商", product="产品", sku="SKU", category="产品主分类", owner="负责人", source="客户来源", status="状态", currency="原币币种", direction="收支方向", kind="业务类型", warehouse="仓库", type="出入库类型")
SOURCES = {
    "sales": {"label": "销售报表", "dimensions": ["time", "region", "country", "customer", "product", "sku", "category", "owner", "source", "status", "currency"], "dates": {"order_date": "订单日期", "expected_ship_date": "预计交期", "created_at": "创建时间", "updated_at": "更新时间"}, "note": "有效销售订单的合同金额；商品行之外的运费、折扣和已确认合同变更统一列为订单金额调整，不分摊 SKU。金额按订单汇率折人民币，不代表实收或利润。"},
    "purchase": {"label": "采购 / 供应商报表", "dimensions": ["time", "country", "supplier", "product", "sku", "category", "status", "currency"], "dates": {"order_date": "下单日期", "expected_arrival_date": "预计到货日", "created_at": "创建时间", "updated_at": "更新时间"}, "note": "有效采购单的合同金额；已确认合同变更作为采购金额调整独立列示，不含采购附加成本。"},
    "profit": {"label": "订单利润", "dimensions": ["time", "country", "customer", "owner", "currency"], "dates": {"order_date": "订单日期"}, "note": "金额字段表示预计订单利润 = 当前有效销售额 - 已归属采购成本 - 已确认订单费用，不等同于会计净利润。"},
    "customers": {"label": "客户增长", "dimensions": ["time", "region", "country", "customer", "owner", "source", "status"], "dates": {"created_at": "创建时间", "updated_at": "更新时间"}, "note": "按客户档案创建/更新时间统计客户数；状态、负责人、地域使用当前档案，并非历史快照。"},
    "cash": {"label": "账面收支（人民币折算参考）", "basis": BOOK_RMB_BASIS, "version": BOOK_RMB_VERSION, "dimensions": ["time", "customer", "supplier", "direction", "kind", "category", "currency"], "dates": {"transaction_date": "流水发生日期", "created_at": "创建时间", "updated_at": "更新时间"}, "note": BOOK_RMB_NOTE + " 收入为正、支出为负，合计为账面净收支；不重复统计预收预付分配。"},
    "actual_cash": {"label": "银行实际人民币资金", "basis": "bank_cash_confirmed_v1", "version": 1, "dimensions": ["time", "direction", "kind", "currency"], "dates": {"bank_date": "银行实际日期"}, "note": "仅人工确认的银行资金事件；按银行实际日期和人民币净额统计。已登记银行资金汇总，不代表公司全部实际资金，不是利润、销售收入或银行账户余额。"},
    "inventory": {"label": "库存变动", "dimensions": ["time", "product", "sku", "category", "warehouse", "type"], "dates": {"movement_date": "发生日期", "created_at": "创建时间", "updated_at": "更新时间"}, "note": "期间出入库净变动（入正出负），不是当前库存余额。不同单位数量分别展示；金额不适用。"},
}

# A report permission authorizes report operations, while each source module
# still owns access to its underlying business records.
SOURCE_MODULES = {
    "sales": ("orders",),
    "purchase": ("purchases",),
    "profit": ("orders", "purchases", "transactions"),
    "customers": ("customers",),
    "cash": ("transactions",),
    "actual_cash": ("transactions",),
    "inventory": ("inventory",),
}

DIMENSION_MODULES = {
    "customer": "customers", "country": "customers", "region": "customers",
    "owner": "customers", "source": "customers", "supplier": "suppliers",
    "product": "products", "sku": "skus", "category": "categories",
}
DETAIL_MAX_ROWS = 10000


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
    model = {"sales": Order, "purchase": PurchaseOrder, "profit": Order, "customers": Customer, "cash": Transaction, "actual_cash": RmbCashEvent, "inventory": InventoryMovement}[source]
    field = date_field + ("__date" if date_field.endswith("_at") else "")
    qs = model.objects.filter(**{field + "__range": (start, end)}).order_by("pk")
    if source in ["sales", "purchase", "profit"]:
        # Formal operating reports must never mix in explicitly historical-only records.
        qs = qs.filter(historical_only=False)
        if source in ["sales", "profit"] and user is not None:
            qs = scope_customer_related_queryset(qs, user)
        item_model = OrderItem if source in ["sales", "profit"] else PurchaseOrderItem
        qs = qs.exclude(status__in=["draft", "cancelled"]).select_related("customer" if source in ["sales", "profit"] else "supplier").prefetch_related(Prefetch("items", queryset=item_model.objects.select_related("sku__product__category")), "contract_changes")
    elif source == "cash":
        qs = qs.filter(status="confirmed").select_related("customer", "supplier")
        if user is not None:
            qs = scope_transaction_queryset(qs, user)
    elif source == "actual_cash":
        # This source is intentionally independent from the legacy book cash source.
        qs = qs.filter(status="confirmed")
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
        elif source == "actual_cash":
            # Visibility is checked per event so hidden source batches cannot be
            # inferred from an aggregate row.
            if user is not None and not cash.visible(obj, user):
                continue
            dims = {
                "direction": (obj.direction, "流入" if obj.direction == "income" else "流出"),
                "kind": (obj.kind, obj.get_kind_display() or obj.kind),
                "currency": (obj.currency, obj.currency),
            }
            amount = obj.bank_net_amount if obj.direction == "income" else -obj.bank_net_amount
            yield day, obj.pk, dims, amount, Decimal(0), ""
        elif source == "inventory":
            yield day, obj.pk, {**dims, **product_dims(obj.sku)}, Decimal(0), obj.signed_quantity, obj.sku.unit
        else:
            yield day, obj.pk, dims, Decimal(0), Decimal(0), ""


def dimension_value(day, dims, dimension, grain):
    return (bucket(day, grain), bucket(day, grain)) if dimension == "time" else dims[dimension]


def composite_key(first_key, second_key):
    """Encode two keys without allowing separator or prefix collisions."""
    return json.dumps([str(first_key), str(second_key)], ensure_ascii=False, separators=(",", ":"))


def aggregate(source, date_field, start, end, group, grain, filters, group_2=None, user=None):
    groups, total_ids, quantities = {}, set(), {}
    amount = Decimal(0)
    for day, document_id, dims, value, qty, unit in records(source, date_field, start, end, user=user):
        if any(str(dims.get(key, ("", ""))[0]) != expected for key, expected in filters.items()): continue
        first_key, first_label = dimension_value(day, dims, group, grain)
        if group_2:
            second_key, second_label = dimension_value(day, dims, group_2, grain)
            key = composite_key(first_key, second_key)
            label = f"{first_label} · {second_label}"
            group_values = [
                {"dimension": group, "key": first_key, "label": first_label},
                {"dimension": group_2, "key": second_key, "label": second_label},
            ]
        else:
            key, label = first_key, first_label
            group_values = None
        row = groups.setdefault(key, {"key": key, "label": label, "amount": Decimal(0), "quantities": {}, "ids": set(), **({"groups": group_values} if group_values else {})})
        row["amount"] += value
        row["ids"].add(document_id)
        total_ids.add(document_id)
        amount += value
        if unit:
            row["quantities"][unit] = row["quantities"].get(unit, Decimal(0)) + qty
            quantities[unit] = quantities.get(unit, Decimal(0)) + qty
    if group == "time" and not group_2:
        day = start
        while day <= end:
            key = bucket(day, grain)
            groups.setdefault(key, {"key": key, "label": key, "amount": Decimal(0), "quantities": {}, "ids": set()})
            day += timedelta(days=1)
    rows = [{**{k: v for k, v in row.items() if k != "ids"}, "count": len(row["ids"])} for row in groups.values()]
    rows.sort(key=(lambda row: row["key"]) if group == "time" and not group_2 else (lambda row: (-abs(row["amount"]) if source not in ["customers", "inventory"] else -row["count"], row["label"])))
    return rows, {"amount": amount, "count": len(total_ids), "quantities": quantities}


@api_view(["GET"])
def report_catalog(request):
    return Response({"sources": SOURCES, "dimensions": DIMENSIONS, "grains": dict(day="日", week="周（周一开始）", month="月", quarter="季度", year="年")})


@api_view(["GET"])
@permission_classes([HistoricalAnalysisPermission])
def historical_analysis(request):
    """Separate, read-only analysis for explicitly imported historical contracts."""
    # Module access controls the aggregate, while master-data permissions
    # control each identity-bearing dimension.  In particular, an employee
    # may review historical sales totals without receiving SKU or customer
    # labels as a side effect.
    can_sales = user_can(request.user, "orders", "view")
    can_purchase = user_can(request.user, "purchases", "view")
    can_sales_customer = can_sales and user_can(request.user, "customers", "view")
    can_purchase_supplier = can_purchase and user_can(request.user, "suppliers", "view")
    can_sku_dimension = (can_sales or can_purchase) and user_can(request.user, "skus", "view")
    can_category_dimension = can_sku_dimension and user_can(request.user, "categories", "view")
    if not can_sales and not can_purchase:
        return Response({"detail": "你没有历史订单分析权限。"}, status=403)
    today = timezone.localdate()
    default_start = date(today.year - 9, 1, 1)
    default_end = date(today.year, 12, 31)
    try:
        start = date.fromisoformat(request.query_params.get("date_from") or default_start.isoformat())
        end = date.fromisoformat(request.query_params.get("date_to") or default_end.isoformat())
    except ValueError:
        raise ValidationError("历史分析日期范围无效。")
    if start > end or (end - start).days > 3660:
        raise ValidationError("历史分析日期范围无效，单次查询最多十年。")

    payload = {
        "scope": "historical_only",
        "label": "历史订单 · 仅用于经营分析",
        "period": {"date_from": start, "date_to": end},
        "sales": None,
        "purchase": None,
        "profit": {"available": False, "note": "历史订单未提供可靠成本时，不计算利润。"},
    }
    if can_sales:
        sales_qs = scope_customer_related_queryset(
            Order.objects.filter(
                historical_only=True,
                status="historical",
                order_date__range=(start, end),
            ).select_related("customer").prefetch_related("items__sku__product"),
            request.user,
        )
        customer_rows = {}
        customer_order_ids = {}
        country_rows = {}
        category_rows = {}
        sku_rows = {}
        total = Decimal("0")
        quantity = Decimal("0")
        for order in sales_qs:
            order_amount = order.total_amount * order.exchange_rate
            total += order_amount
            if can_sales_customer:
                customer_key = str(order.customer_id)
                customer_rows.setdefault(customer_key, {"id": order.customer_id, "label": order.customer.name, "amount": Decimal("0"), "count": 0})
                customer_rows[customer_key]["amount"] += order_amount
                customer_order_ids.setdefault(customer_key, set()).add(order.pk)
                country_key = order.customer.country or ""
                country_rows.setdefault(country_key, {"id": country_key, "label": country_key or "未填写", "amount": Decimal("0"), "count": 0})
                country_rows[country_key]["amount"] += order_amount
                country_rows[country_key]["count"] += 1
            for item in order.items.all():
                quantity += item.quantity
                if can_sku_dimension:
                    sku_key = str(item.sku_id)
                    sku_rows.setdefault(sku_key, {"id": item.sku_id, "label": f"{item.sku.sku} · {item.display_name_snapshot or item.sku.display_name_cn or item.sku.product.name}", "amount": Decimal("0"), "quantity": Decimal("0")})
                    sku_rows[sku_key]["amount"] += item.amount * order.exchange_rate
                    sku_rows[sku_key]["quantity"] += item.quantity
                if can_category_dimension and item.sku.product.category_id:
                    category = item.sku.product.category
                    category_key = str(category.pk)
                    category_rows.setdefault(category_key, {"id": category.pk, "label": category.name, "amount": Decimal("0"), "quantity": Decimal("0")})
                    category_rows[category_key]["amount"] += item.amount * order.exchange_rate
                    category_rows[category_key]["quantity"] += item.quantity
        for key, row in customer_rows.items():
            row["count"] = len(customer_order_ids.get(key, set()))
        payload["sales"] = {
            "order_count": sales_qs.count(), "amount_rmb": total, "quantity": quantity,
            "by_customer": list(customer_rows.values()) if can_sales_customer else [],
            "by_country": list(country_rows.values()) if can_sales_customer else [],
            "by_sku": list(sku_rows.values()) if can_sku_dimension else [],
            "by_category": list(category_rows.values()) if can_category_dimension else [],
        }
    if can_purchase:
        purchase_qs = PurchaseOrder.objects.filter(
            historical_only=True,
            status="historical",
            order_date__range=(start, end),
        ).select_related("supplier").prefetch_related("items__sku__product")
        supplier_rows = {}
        supplier_order_ids = {}
        country_rows = {}
        category_rows = {}
        sku_rows = {}
        total = Decimal("0")
        quantity = Decimal("0")
        for purchase in purchase_qs:
            purchase_amount = purchase.total_amount * purchase.exchange_rate
            total += purchase_amount
            if can_purchase_supplier:
                supplier_key = str(purchase.supplier_id)
                supplier_rows.setdefault(supplier_key, {"id": purchase.supplier_id, "label": purchase.supplier.name, "amount": Decimal("0"), "count": 0})
                supplier_rows[supplier_key]["amount"] += purchase_amount
                supplier_order_ids.setdefault(supplier_key, set()).add(purchase.pk)
                country_key = purchase.supplier.country or ""
                country_rows.setdefault(country_key, {"id": country_key, "label": country_key or "未填写", "amount": Decimal("0"), "count": 0})
                country_rows[country_key]["amount"] += purchase_amount
                country_rows[country_key]["count"] += 1
            for item in purchase.items.all():
                quantity += item.quantity
                if can_sku_dimension:
                    sku_key = str(item.sku_id)
                    sku_rows.setdefault(sku_key, {"id": item.sku_id, "label": f"{item.sku.sku} · {item.display_name_snapshot or item.sku.display_name_cn or item.sku.product.name}", "amount": Decimal("0"), "quantity": Decimal("0")})
                    sku_rows[sku_key]["amount"] += item.amount * purchase.exchange_rate
                    sku_rows[sku_key]["quantity"] += item.quantity
                if can_category_dimension and item.sku.product.category_id:
                    category = item.sku.product.category
                    category_key = str(category.pk)
                    category_rows.setdefault(category_key, {"id": category.pk, "label": category.name, "amount": Decimal("0"), "quantity": Decimal("0")})
                    category_rows[category_key]["amount"] += item.amount * purchase.exchange_rate
                    category_rows[category_key]["quantity"] += item.quantity
        for key, row in supplier_rows.items():
            row["count"] = len(supplier_order_ids.get(key, set()))
        payload["purchase"] = {
            "order_count": purchase_qs.count(), "amount_rmb": total, "quantity": quantity,
            "by_supplier": list(supplier_rows.values()) if can_purchase_supplier else [],
            "by_country": list(country_rows.values()) if can_purchase_supplier else [],
            "by_sku": list(sku_rows.values()) if can_sku_dimension else [],
            "by_category": list(category_rows.values()) if can_category_dimension else [],
        }
    return Response(payload)


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


def _detail_permissions(request, source, group, group_2, filters):
    """Require both report permissions and the permissions needed by raw rows.

    A report aggregate can be useful with a restricted identity dimension, but
    a raw row contains the original document and its business identities.  The
    stricter checks here prevent a detail query from becoming an information
    side channel through a group that the caller could otherwise aggregate.
    """
    for module in SOURCE_MODULES[source]:
        require_finance_permission(request.user, module, "view")
    require_finance_permission(request.user, "reports", "view")

    raw_modules = {
        "sales": ("orders", "customers", "products", "skus"),
        "purchase": ("purchases", "suppliers", "products", "skus"),
    }[source]
    for module in raw_modules:
        require_finance_permission(request.user, module, "view")
    for dimension in {group, *(dimension for dimension in [group_2] if dimension), *filters.keys()}:
        module = DIMENSION_MODULES.get(dimension)
        if module:
            require_finance_permission(request.user, module, "view")


def _detail_group_matches(day, dims, group, group_2, group_value, group_2_value, grain):
    first_key, _ = dimension_value(day, dims, group, grain)
    if str(first_key) != str(group_value):
        return False
    if group_2:
        second_key, _ = dimension_value(day, dims, group_2, grain)
        return str(second_key) == str(group_2_value)
    return True


def _detail_queryset(source, date_field, start, end, user):
    """Return the same formal business-record scope used by ``records``."""
    model = {"sales": Order, "purchase": PurchaseOrder}[source]
    field = date_field + ("__date" if date_field.endswith("_at") else "")
    qs = model.objects.filter(**{field + "__range": (start, end)}).filter(historical_only=False)
    if source == "sales":
        qs = scope_customer_related_queryset(qs, user)
        item_model = OrderItem
        relation = "customer"
    else:
        item_model = PurchaseOrderItem
        relation = "supplier"
    return qs.exclude(status__in=["draft", "cancelled"]).select_related(relation).prefetch_related(
        Prefetch("items", queryset=item_model.objects.select_related("sku__product__category")),
        "contract_changes",
    ).order_by("pk")


def _detail_rows(source, date_field, start, end, group, group_2, grain, filters, group_value, group_2_value, user):
    rows = []
    def add_row(row):
        if len(rows) >= DETAIL_MAX_ROWS:
            raise ValidationError("构成明细记录过多，请缩小日期范围或增加筛选后重试。")
        rows.append(row)

    model_rows = _detail_queryset(source, date_field, start, end, user)
    for document in model_rows:
        day = getattr(document, date_field)
        if isinstance(day, datetime):
            day = timezone.localtime(day).date()
        base_dims = {}
        for key in ["status", "currency"]:
            value = getattr(document, key, "")
            display = getattr(document, f"get_{key}_display", lambda: value)()
            base_dims[key] = (value, display or "未填写")
        if source == "sales":
            base_dims.update(customer_dims(document.customer))
            party_name = document.customer.name if document.customer else "未填写"
            party_id = document.customer_id
            document_no = document.order_no
            document_date = document.order_date
            status_display = document.get_status_display()
        else:
            supplier = document.supplier
            base_dims["supplier"] = identity(supplier, supplier.name if supplier else "")
            base_dims["country"] = (getattr(supplier, "country", ""), getattr(supplier, "country", "") or "未填写")
            party_name = supplier.name if supplier else "未填写"
            party_id = document.supplier_id
            document_no = document.purchase_no
            document_date = document.order_date
            status_display = document.get_status_display()

        items = list(document.items.all())
        for item in items:
            dims = {**base_dims, **product_dims(item.sku)}
            if any(str(dims.get(key, ("", ""))[0]) != str(expected) for key, expected in filters.items()):
                continue
            if not _detail_group_matches(day, dims, group, group_2, group_value, group_2_value, grain):
                continue
            snapshot_name = getattr(item, "display_name_snapshot", "") or item.sku.display_name_cn or item.sku.product.name
            add_row({
                "id": f"{source}-item-{item.pk}",
                "source": source,
                "record_type": "item",
                "document_id": document.pk,
                "document_no": document_no,
                "document_date": document_date,
                "customer_id": party_id if source == "sales" else None,
                "customer_name": party_name if source == "sales" else "",
                "supplier_id": party_id if source == "purchase" else None,
                "supplier_name": party_name if source == "purchase" else "",
                "sku_id": item.sku_id,
                "sku": getattr(item, "sku_code_snapshot", "") or item.sku.sku,
                "product_id": item.sku.product_id,
                "product_name": snapshot_name,
                "quantity": item.quantity,
                "unit": getattr(item, "unit_snapshot", "") or item.sku.unit,
                "amount": item.amount * document.exchange_rate,
                "status": document.status,
                "status_display": status_display,
                "is_adjustment": False,
            })

        contract_changes = sum(document.contract_changes.filter(status="approved").values_list("amount_delta", flat=True), Decimal("0"))
        adjustment = ((document.shipping_fee - document.discount + contract_changes) if source == "sales" else contract_changes) * document.exchange_rate
        if adjustment or not items:
            dims = {**base_dims, **product_dims(None)}
            if not any(str(dims.get(key, ("", ""))[0]) != str(expected) for key, expected in filters.items()) and _detail_group_matches(day, dims, group, group_2, group_value, group_2_value, grain):
                add_row({
                    "id": f"{source}-adjustment-{document.pk}",
                    "source": source,
                    "record_type": "adjustment",
                    "document_id": document.pk,
                    "document_no": document_no,
                    "document_date": document_date,
                    "customer_id": party_id if source == "sales" else None,
                    "customer_name": party_name if source == "sales" else "",
                    "supplier_id": party_id if source == "purchase" else None,
                    "supplier_name": party_name if source == "purchase" else "",
                    "sku_id": None,
                    "sku": "",
                    "product_id": None,
                    "product_name": "订单金额调整",
                    "quantity": Decimal("0"),
                    "unit": "",
                    "amount": adjustment,
                    "status": document.status,
                    "status_display": status_display,
                    "is_adjustment": True,
                })
    return rows


def _detail_sort_key(row, field):
    value = row.get(field)
    if value is None:
        return ""
    return value


@api_view(["GET"])
def report_details(request):
    params = request.query_params
    source = params.get("source", "sales")
    if source not in {"sales", "purchase"}:
        raise ValidationError("当前报表来源不支持原始明细下钻。")
    spec = SOURCES[source]
    group, group_2, grain = params.get("group_by", "time"), params.get("group_by_2") or None, params.get("grain", "month")
    date_field = params.get("date_field") or next(iter(spec["dates"]))
    if group not in spec["dimensions"] or (group_2 and group_2 not in spec["dimensions"]) or group == group_2 or date_field not in spec["dates"] or grain not in ["day", "week", "month", "quarter", "year"]:
        raise ValidationError("无效的明细统计维度、时间粒度或日期口径。")
    try:
        start = date.fromisoformat(params.get("date_from") or timezone.localdate().replace(day=1).isoformat())
        end = date.fromisoformat(params.get("date_to") or timezone.localdate().isoformat())
        if start > end or (end - start).days > 3660 or start.year < 1900 or end.year > 9990:
            raise ValueError
    except ValueError:
        raise ValidationError("明细日期范围无效；开始日期不得晚于结束日期，单次查询最多十年。")
    group_value = params.get("group_value")
    group_2_value = params.get("group_2_value") if group_2 else None
    if group_value in (None, "") or (group_2 and group_2_value in (None, "")):
        raise ValidationError("请提供要查看构成明细的分组值。")
    filters = {}
    for key, value in params.items():
        if key.startswith("filter_"):
            dimension = key[7:]
            if dimension not in spec["dimensions"] or dimension == "time":
                raise ValidationError("该模块不支持此筛选维度。")
            filters[dimension] = value
    _detail_permissions(request, source, group, group_2, filters)

    rows = _detail_rows(source, date_field, start, end, group, group_2, grain, filters, group_value, group_2_value, request.user)
    ordering = params.get("ordering", "-document_date")
    descending = ordering.startswith("-")
    sort_field = ordering[1:] if descending else ordering
    sort_fields = {"document_date": "document_date", "document_no": "document_no", "amount": "amount", "quantity": "quantity", "sku": "sku", "party": "customer_name" if source == "sales" else "supplier_name"}
    if sort_field not in sort_fields:
        raise ValidationError("不支持的明细排序字段。")
    field = sort_fields[sort_field]
    rows.sort(key=lambda row: (_detail_sort_key(row, field), row["id"]), reverse=descending)

    amount = sum((row["amount"] for row in rows), Decimal("0"))
    document_ids = {row["document_id"] for row in rows}
    quantities = {}
    for row in rows:
        if row["unit"]:
            quantities[row["unit"]] = quantities.get(row["unit"], Decimal("0")) + row["quantity"]
    page_size = min(max(int(params.get("page_size", 20)), 1), 50) if str(params.get("page_size", "20")).lstrip("-").isdigit() else 20
    page_number = max(int(params.get("page", 1)), 1) if str(params.get("page", "1")).lstrip("-").isdigit() else 1
    page = Paginator(rows, page_size).get_page(page_number)
    return Response({
        "source": source,
        "group_by": group,
        **({"group_by_2": group_2} if group_2 else {}),
        "date_field": date_field,
        "date_label": spec["dates"][date_field],
        "grain": grain,
        "period": {"date_from": start, "date_to": end},
        "selection": {"group_value": group_value, **({"group_2_value": group_2_value} if group_2 else {}), "filters": filters},
        "count": len(rows),
        "page": page.number,
        "page_size": page_size,
        "page_count": page.paginator.num_pages,
        "totals": {"amount": amount, "count": len(document_ids), "quantities": quantities},
        "rows": list(page.object_list),
    })


@api_view(["GET"])
def report_data(request):
    if request.query_params.get("export", "").lower() in {"1", "true", "csv", "xlsx"} and not user_can(request.user, "reports", "export"):
        return Response({"detail": "你没有报表导出权限。"}, status=403)
    params = request.query_params
    source = params.get("source", "sales")
    if source not in SOURCES: raise ValidationError("不支持的报表模块。")
    for module in SOURCE_MODULES[source]:
        require_finance_permission(request.user, module, "view")
    if source == "actual_cash":
        cash.access(request.user)
    spec = SOURCES[source]
    group, group_2, grain = params.get("group_by", "time"), params.get("group_by_2") or None, params.get("grain", "month")
    date_field = params.get("date_field") or next(iter(spec["dates"]))
    if group not in spec["dimensions"] or (group_2 and group_2 not in spec["dimensions"]) or group == group_2 or date_field not in spec["dates"] or grain not in ["day", "week", "month", "quarter", "year"]:
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
    for dimension in {group, *(dimension for dimension in [group_2] if dimension), *filters.keys()}:
        module = DIMENSION_MODULES.get(dimension)
        if module:
            require_finance_permission(request.user, module, "view")
    rows, totals = aggregate(source, date_field, start, end, group, grain, filters, group_2=group_2, user=request.user)
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
    _, previous = aggregate(source, date_field, previous_start, previous_end, group, grain, filters, group_2=group_2, user=request.user)
    changes = {key: ((totals[key] - previous[key]) / abs(previous[key]) * 100 if previous[key] else None) for key in ["amount", "count"]}
    if params.get("export") == "csv":
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="report-{source}-{start}-{end}.csv"'
        response.write("\ufeff")
        writer = csv.writer(response)
        writer.writerow([spec["label"], start, end, spec["dates"][date_field], spec["note"]])
        writer.writerow(["筛选条件", safe_csv("；".join(f"{item['name']}：{item['label']}" for item in filter_summary(source, filters, user=request.user)))])
        writer.writerow(["比较期间", previous_start, previous_end])
        amount_label = "金额（银行实际人民币净额）" if source == "actual_cash" else ("金额（人民币折算参考）" if source == "cash" else "金额（人民币）") if source not in ["customers", "inventory"] else "金额（不适用）"
        group_headers = [DIMENSIONS[group], *( [DIMENSIONS[group_2]] if group_2 else [])]
        writer.writerow([*group_headers, amount_label, "去重单据/档案数", "数量（按单位）"])
        for row in rows:
            group_values = row.get("groups") or [{"label": row["label"]}]
            writer.writerow([*(safe_csv(value["label"]) for value in group_values), str(row["amount"]) if source not in ["customers", "inventory"] else "", row["count"], safe_csv(" / ".join(f"{qty} {unit}" for unit, qty in row["quantities"].items()))])
        writer.writerow(["合计（单据去重）", *( [""] if group_2 else []), str(totals["amount"]) if source not in ["customers", "inventory"] else "", totals["count"], safe_csv(" / ".join(f"{qty} {unit}" for unit, qty in totals["quantities"].items()))])
        return response
    return Response({**({"basis": spec.get("basis"), "version": spec.get("version")} if source in {"cash", "actual_cash"} else {}), "source": source, "group_by": group, **({"group_by_2": group_2} if group_2 else {}), "date_field": date_field, "date_label": spec["dates"][date_field], "grain": grain, "comparison": comparison, "period": {"date_from": start, "date_to": end}, "comparison_period": {"date_from": previous_start, "date_to": previous_end}, "totals": totals, "previous": previous, "changes": changes, "rows": rows, "note": spec["note"], "filters": filters, "filter_summary": filter_summary(source, filters, user=request.user), "generated_at": timezone.now()})

