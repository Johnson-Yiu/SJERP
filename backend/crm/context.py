from .finance_scope import scope_transaction_queryset
from .trade_units import amount_expression, trade_values
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Case, Count, DecimalField, ExpressionWrapper, F, Sum, When
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from .models import Contact, Customer, FollowUp, InventoryMovement, Order, OrderItem, Product, ProductCategory, ProductCertificate, ProductParameter, PurchaseOrder, Quote, SKU, SKUVersion, Supplier, SupplierSKU, Transaction
from .country_registry import display_country
from .customer_status import customer_status_display
from .error_messages import CUSTOMER_NOT_FOUND_MESSAGE
from .querysets import prefetch_purchase_related_orders
from .serializers import ContactSerializer, CustomerSerializer, FollowUpAttachmentSerializer, FollowUpSerializer, InventoryMovementSerializer, OrderSerializer, ProductCertificateSerializer, ProductParameterSerializer, ProductSerializer, PurchaseOrderSerializer, QuoteSerializer, SKUSerializer, SupplierSerializer, SupplierSKUSerializer, TransactionSerializer, protected_media_url
from .permissions import CONTEXT_MODULES, user_can
from .sales_scope import scope_customer_queryset, scope_customer_related_queryset

MONEY = DecimalField(max_digits=20, decimal_places=2)


def _target(rows, entity, id_key="id"):
    result = []
    for row in rows:
        item = dict(row)
        item["_target_entity"] = entity
        item["_target_id"] = item.get(id_key)
        result.append(item)
    return result


def _hide_supplier_payment_rules(rows):
    """Keep fixed supplier rules out of regular context/detail payloads."""
    for row in rows:
        row.pop("payment_terms_config", None)
        row.pop("payment_terms_summary", None)
    return rows


def _section(key, title, entity, columns, rows, description=""):
    return {"key": key, "title": title, "entity": entity, "columns": columns, "rows": rows, "description": description}


def _stock_skus(queryset):
    return queryset.select_related("product").annotate(
        stock_quantity=Coalesce(Sum(Case(
            When(inventory_movements__type__in=["sale_out", "adjust_out", "sample_out", "transfer_out", "production_out", "other_out"], then=-F("inventory_movements__quantity")),
            default=F("inventory_movements__quantity"), output_field=MONEY,
        )), Decimal("0"), output_field=MONEY)
    )


@api_view(["GET"])
def entity_context(request, entity, pk):
    handlers = {
        "customers": _customer_context,
        "suppliers": _supplier_context,
        "contacts": _contact_context,
        "follow-ups": _follow_up_context,
        "categories": _category_context,
        "products": _product_context,
        "skus": _sku_context,
        "sku-versions": _sku_version_context,
        "supplier-skus": _supplier_sku_context,
        "product-parameters": _parameter_context,
        "product-certificates": _certificate_context,
        "quotes": _quote_context,
        "orders": _order_context,
        "purchase-orders": _purchase_order_context,
        "transactions": _transaction_context,
        "inventory-movements": _inventory_context,
    }
    handler = handlers.get(entity)
    if not handler:
        return Response({"detail": "未知的数据类型。"}, status=404)
    if entity == "products":
        payload = handler(pk, include_inactive=request.query_params.get("include_inactive") == "1", user=request.user)
    elif entity in {"skus", "supplier-skus", "customers", "contacts", "follow-ups", "quotes", "orders", "inventory-movements", "transactions", "purchase-orders", "suppliers", "sku-versions", "categories", "product-parameters", "product-certificates"}:
        payload = handler(pk, request.user)
    else:
        payload = handler(pk)
    # A detail context can contain several related modules. Keep the primary
    # record visible while omitting related sections the operator cannot view.
    payload["sections"] = [
        section for section in payload.get("sections", [])
        if user_can(request.user, CONTEXT_MODULES.get(section.get("entity")), "view")
        and (section.get("entity") != "sales-periods" or user_can(request.user, "orders", "view"))
    ]
    for section in payload["sections"]:
        if section.get("entity") == "transactions":
            rows = section.get("rows", [])
            visible = set(scope_transaction_queryset(
                Transaction.objects.filter(pk__in=[row["id"] for row in rows]), request.user
            ).values_list("pk", flat=True))
            section["rows"] = [row for row in rows if row["id"] in visible]
    metric_modules = {
        "customers": {"累计销售额": "orders", "订单": "orders", "报价": "quotes", "下次跟进": "followups"},
        "contacts": {"跟进次数": "followups"},
        "categories": {"产品数量": "products"},
        "suppliers": {"合作产品": "products", "采购单记录": "purchases", "正式采购金额（人民币）": "purchases", "已付采购款（人民币）": ["purchases", "finance", "transactions"]},
        "purchase-orders": {"已付款": ["finance", "transactions"], "待付款": ["finance", "transactions"]},
        "products": {"SKU": "skus", "供应商": "suppliers", "当前库存": "inventory", "参数": "parameters"},
        "skus": {"当前库存": "inventory", "订单记录": "orders", "历史版本": "skus"},
        "supplier-skus": {"销售订单行": "orders", "采购明细行": "purchases"},
        "quotes": {"转订单": "orders"},
        "orders": {"已收款": ["finance", "transactions"], "当前待收款": ["finance", "transactions"]},
    }
    required = metric_modules.get(entity, {})
    payload["metrics"] = [
        metric for metric in payload.get("metrics", [])
        if metric[0] not in required or all(user_can(request.user, module, "view") for module in (required[metric[0]] if isinstance(required[metric[0]], list) else [required[metric[0]]]))
    ]
    return Response(payload)


def _customer_context(pk, user=None):
    queryset = Customer.objects.all()
    if user is not None:
        queryset = scope_customer_queryset(queryset, user)
    obj = queryset.filter(pk=pk).first()
    if obj is None:
        raise NotFound(CUSTOMER_NOT_FOUND_MESSAGE)
    formal_statuses = ["confirmed", "production", "shipped", "completed"]
    formal_orders = list(obj.orders.filter(status__in=formal_statuses).prefetch_related("items", "contract_changes"))
    sales_rmb = sum((order.total_amount * order.exchange_rate for order in formal_orders), Decimal("0"))
    valid_items = OrderItem.objects.filter(order__customer=obj, order__status__in=formal_statuses)
    context = {"user": user}
    contacts = _target(ContactSerializer(obj.contacts.all(), many=True, context=context).data, "contacts")
    orders = _target(OrderSerializer(obj.orders.prefetch_related("items__sku__product", "transactions"), many=True, context=context).data, "orders")
    quotes = _target(QuoteSerializer(obj.quotes.prefetch_related("items__sku__product"), many=True, context=context).data, "quotes")
    followups = _target(FollowUpSerializer(obj.follow_ups.select_related("contact"), many=True, context=context).data, "follow-ups")
    cash = _target(TransactionSerializer(obj.transactions.select_related("order"), many=True, context=context).data, "transactions")
    purchases = _target([{
        "id": item.order_id, "order_no": item.order.order_no, "order_date": item.order.order_date,
        "sku_code": item.sku.sku if user_can(user, "skus", "view") else "",
        "product_name": item.sku.product.name if user_can(user, "products", "view") else "", "quantity": item.quantity,
        "unit_price": item.unit_price, "currency": item.order.currency, "amount": item.amount,
    } for item in valid_items.select_related("order", "sku__product").order_by("-order__order_date")], "orders")
    return {
        "entity": "customers", "title": obj.name, "subtitle": f"{obj.code} · {display_country(obj.country) or '未填写国家/地区'}", "badge": customer_status_display(obj.status),
        "info": [["负责人", obj.owner or "—"], ["业务区域", obj.region or "—"], ["来源", obj.source or "—"], ["网站", obj.website or "—"], ["地址", obj.address or "—"], ["备注", obj.notes or "—"]],
        "metrics": [["累计销售额", sales_rmb, "rmb"], ["订单", len(formal_orders), "number"], ["报价", len(quotes), "number"], ["下次跟进", obj.next_follow_up or "未安排", "date"]],
        "sections": [
            _section("followups", "跟进记录", "follow-ups", [["followed_at", "时间", "datetime"], ["subject", "主题"], ["content", "跟进记录 / 解决方案", "excerpt"], ["result", "客户回复 / 客户疑问", "excerpt"], ["type_display", "方式"], ["next_follow_up", "下次跟进", "date"]], followups),
            _section("quotes", "报价记录", "quotes", [["quote_no", "报价单号"], ["quote_date", "日期", "date"], ["status_display", "状态", "status"], ["total_amount", "金额", "money"], ["currency", "币种"]], quotes),
            _section("orders", "订单", "orders", [["order_no", "订单号"], ["order_date", "日期", "date"], ["status_display", "履约状态", "status"], ["total_amount", "金额", "money"], ["currency", "币种"]], orders),
            _section("contacts", "联系人", "contacts", [["name", "姓名"], ["title", "职位"], ["email", "邮箱"], ["phone", "电话"], ["is_primary", "主联系人", "boolean"]], contacts),
            _section("purchases", "成交商品记录", "orders", [["order_date", "日期", "date"], ["order_no", "订单"], ["sku_code", "SKU"], ["product_name", "产品"], ["quantity", "数量", "number"], ["amount", "金额", "money"]], purchases),
            _section("cash", "财务流水", "transactions", [["transaction_date", "日期", "date"], ["transaction_no", "流水号"], ["direction_display", "方向"], ["category", "分类"], ["amount", "金额", "money"], ["currency", "币种"]], cash),
        ],
    }


def _contact_context(pk, user=None):
    queryset = Contact.objects.select_related("customer")
    if user is not None:
        queryset = scope_customer_related_queryset(queryset, user)
    obj = get_object_or_404(queryset, pk=pk)
    context = {"user": user}
    company = _target([CustomerSerializer(obj.customer, context=context).data], "customers")
    followups = _target(FollowUpSerializer(obj.follow_ups.select_related("customer"), many=True, context=context).data, "follow-ups")
    customer_name = obj.customer.name if user_can(user, "customers", "view") else ""
    metrics = [["跟进次数", len(followups), "number"]] if user_can(user, "followups", "view") else []
    return {"entity": "contacts", "title": obj.name, "subtitle": f"{obj.title or '联系人'} · {customer_name}" if customer_name else (obj.title or "联系人"), "badge": "主联系人" if obj.is_primary else "联系人", "info": [["关联企业", customer_name or "—"], ["邮箱", obj.email or "—"], ["电话", obj.phone or "—"], ["WhatsApp", obj.whatsapp or "—"], ["备注", obj.notes or "—"]], "metrics": metrics, "sections": [
        _section("followups", "跟进记录", "follow-ups", [["followed_at", "时间", "datetime"], ["subject", "主题"], ["content", "跟进记录 / 解决方案", "excerpt"], ["result", "客户回复 / 客户疑问", "excerpt"], ["type_display", "方式"], ["next_follow_up", "下次跟进", "date"]], followups),
        _section("company", "关联企业", "customers", [["code", "客户编号"], ["name", "企业名称"], ["country", "国家"], ["status_display", "状态", "status"], ["owner", "负责人"]], company),
    ]}


def _product_context(pk, include_inactive=False, user=None):
    obj = get_object_or_404(Product.objects.select_related("category"), pk=pk)
    sku_queryset = obj.skus.all() if include_inactive else obj.skus.filter(active=True)
    context = {"user": user}
    skus = _target(SKUSerializer(_stock_skus(sku_queryset), many=True, context=context).data, "skus")
    params = _target(ProductParameterSerializer(obj.parameters.all(), many=True, context=context).data, "product-parameters")
    certs = _target(ProductCertificateSerializer(obj.certificates.all(), many=True, context=context).data, "product-certificates")
    suppliers = _hide_supplier_payment_rules(_target(SupplierSerializer(obj.suppliers.all(), many=True, context={"user": user}).data, "suppliers"))
    inventory = _target(InventoryMovementSerializer(InventoryMovement.objects.filter(sku__product=obj).select_related("sku__product", "order"), many=True, context={"user": user}).data, "inventory-movements")
    formal_statuses = ["confirmed", "production", "shipped", "completed"]
    sales_orders = scope_customer_related_queryset(Order.objects.filter(status__in=formal_statuses), user) if user is not None and user_can(user, "orders", "view") else Order.objects.none()
    sales_items = OrderItem.objects.filter(sku__product=obj, order__in=sales_orders).select_related("order__customer", "sku")
    sales = _target([{"id": item.order_id, "order_no": item.order.order_no, "order_date": item.order.order_date, "customer_name": item.order.customer.name if user_can(user, "customers", "view") else "", "sku_code": item.sku.sku if user_can(user, "skus", "view") else "", "sales_model": (item.sales_model_snapshot or item.sku.sales_model) if user_can(user, "skus", "view") else "", "unit": (item.unit_snapshot or item.sku.unit) if user_can(user, "skus", "view") else "", "status_label": item.order.get_status_display(), "quantity": item.quantity, "amount": item.amount, "currency": item.order.currency} for item in sales_items.order_by("-order__order_date")], "orders")
    today = timezone.localdate()
    quarter_start_month = ((today.month - 1) // 3) * 3 + 1
    current_quarter_start = date(today.year, quarter_start_month, 1)
    previous_quarter_end = current_quarter_start - timedelta(days=1)
    previous_quarter_start = date(previous_quarter_end.year, ((previous_quarter_end.month - 1) // 3) * 3 + 1, 1)
    periods = [("当年", date(today.year, 1, 1), today), ("上年", date(today.year - 1, 1, 1), date(today.year - 1, 12, 31)), ("上一季度", previous_quarter_start, previous_quarter_end), ("最近 3 个月", today - timedelta(days=89), today)]
    sales_periods = []
    for label, start, end in periods:
        aggregate = sales_items.filter(order__order_date__range=(start, end)).aggregate(order_count=Count("order", distinct=True), sold_quantity=Sum("quantity"), sales=Sum(ExpressionWrapper(amount_expression("") * F("order__exchange_rate"), output_field=MONEY)))
        sales_periods.append({"id": label, "period": label, "order_count": aggregate["order_count"], "quantity": aggregate["sold_quantity"] or 0, "sales": aggregate["sales"] or Decimal("0")})
    stock = sum((Decimal(row["stock_quantity"]) for row in skus if row.get("stock_quantity") is not None), Decimal("0"))
    category_name = obj.category.name if obj.category and user_can(user, "categories", "view") else "未分类"
    hs_code = obj.hs_code.code if obj.hs_code and user_can(user, "hs_codes", "view") else "—"
    return {"entity": "products", "title": obj.name, "subtitle": f"{obj.code} · {category_name}", "badge": obj.get_status_display(), "info": [["产品编号", obj.code], ["英文名称", obj.name_en or "—"], ["HS 编码", hs_code], ["分类", category_name], ["描述", obj.description or "—"]], "metrics": [["SKU", len(skus), "number"], ["供应商", len(suppliers), "number"], ["当前库存", stock, "number"], ["参数", len(params), "number"]], "sections": [
        _section("suppliers", "供应商", "suppliers", [["name", "供应商"], ["code", "二字代码"], ["country", "国家/地区"], ["main_products", "主要产品"], ["contact_name", "联系人"], ["phone", "电话"], ["email", "邮箱"], ["store_url", "店铺链接"], ["payment_terms", "付款条款说明（备注）"]], suppliers),
        _section("skus", "SKU 管理", "skus", [["sku", "SKU Code"], ["sales_model", "销售型号"], ["display_name_cn", "中文 SKU 名称"], ["specification", "规格"], ["stock_quantity", "库存", "number"], ["cost_price", "成本", "money"], ["default_price", "售价", "money"], ["currency", "币种"], ["active", "状态", "sku-active"]], skus),
        _section("sales-summary", "销售统计", "sales-periods", [["period", "统计周期"], ["order_count", "订单数", "number"], ["quantity", "销量", "number"], ["sales", "商品销售额（人民币）", "rmb"]], sales_periods),
        _section("sales", "订单记录", "orders", [["order_date", "日期", "date"], ["order_no", "订单"], ["customer_name", "客户"], ["sku_code", "SKU"], ["quantity", "数量", "number"], ["amount", "原币金额", "money"], ["currency", "币种"]], sales),
        _section("inventory", "出入库流水", "inventory-movements", [["movement_date", "日期", "date"], ["movement_no", "流水号"], ["type_display", "类型"], ["sku_code", "SKU"], ["signed_quantity", "变动", "signed"], ["warehouse", "仓库"]], inventory),
        _section("parameters", "产品参数", "product-parameters", [["group", "分组"], ["name", "参数"], ["value", "参数值"], ["unit", "单位"]], params),
        _section("certificates", "证书档案", "product-certificates", [["name", "证书"], ["certificate_no", "编号"], ["issuer", "签发机构"], ["expires_on", "有效期至", "date"], ["expiry_status", "有效状态", "certificate-expiry"]], certs),
    ]}


def _sku_context(pk, user=None):
    obj = get_object_or_404(_stock_skus(SKU.objects.all()), pk=pk)
    product = _target([ProductSerializer(obj.product, context={"user": user}).data], "products")
    inventory = _target(InventoryMovementSerializer(obj.inventory_movements.select_related("sku__product", "order"), many=True, context={"user": user}).data, "inventory-movements")
    order_items = obj.order_items.select_related("order__customer")
    if user is not None:
        order_items = scope_customer_related_queryset(order_items, user, relation="order__customer")
    orders = _target([{"id": item.order_id, "order_no": item.order.order_no, "order_date": item.order.order_date, "customer_name": item.order.customer.name if user_can(user, "customers", "view") else "", "quantity": item.quantity, "unit_price": item.unit_price, "amount": item.amount, "currency": item.order.currency} for item in order_items], "orders")
    versions = _target([{
        "id": version.pk,
        "version_no": version.version_no,
        "changed_at": version.changed_at,
        "sku_code": version.sku_code_snapshot,
        "display_name_cn": version.display_name_cn_snapshot,
        "sales_model": version.sales_model_snapshot,
        "changed_fields": "、".join(version.changed_fields or []) or "—",
        "change_reason": version.change_reason or "—",
        "changed_by_name": version.changed_by.get_username() if version.changed_by and user_can(user, "employees", "view") else "",
    } for version in obj.versions.select_related("changed_by").order_by("-version_no", "-changed_at")], "sku-versions")
    cost_price = obj.cost_price if user_can(user, "purchases", "view") else None
    stock_quantity = obj.stock_quantity if user_can(user, "inventory", "view") else None
    info = [["销售型号", obj.sales_model or "未设置"], ["SKU Code", obj.sku], ["单位", obj.unit]]
    if user_can(user, "purchases", "view"):
        info.append(["成本价", cost_price])
    info.extend([["默认售价", obj.default_price], ["币种", obj.currency]])
    title = obj.display_name_cn or (obj.product.name if user_can(user, "products", "view") else obj.sku)
    return {"entity": "skus", "title": title, "subtitle": f"{obj.sales_model or '未设置销售型号'} · {obj.sku}", "badge": "启用" if obj.active else "停用", "info": info, "metrics": [["当前库存", stock_quantity, "number"], ["订单记录", len(orders), "number"], ["历史版本", len(versions), "number"]], "sections": [
        _section("product", "所属产品", "products", [["code", "产品编号"], ["name", "产品名称"], ["category_name", "分类"], ["status", "状态", "status"]], product),
        _section("inventory", "出入库流水", "inventory-movements", [["movement_date", "日期", "date"], ["movement_no", "流水号"], ["type_display", "类型"], ["signed_quantity", "变动", "signed"], ["warehouse", "仓库"], ["order_no", "订单"]], inventory),
        _section("orders", "销售订单", "orders", [["order_date", "日期", "date"], ["order_no", "订单"], ["customer_name", "客户"], ["quantity", "数量", "number"], ["unit_price", "单价", "money"], ["currency", "币种"]], orders),
        _section("versions", "历史名称 / 历史版本", "sku-versions", [["version_no", "版本", "number"], ["changed_at", "变更时间", "datetime"], ["display_name_cn", "历史内部名称"], ["sales_model", "历史 Sales Model"], ["changed_fields", "变更字段"], ["change_reason", "变更说明"], ["changed_by_name", "操作人"]], versions),
    ]}


def _sku_version_context(pk, user=None):
    obj = get_object_or_404(SKUVersion.objects.select_related("sku__product", "changed_by"), pk=pk)
    current_sku = _target([SKUSerializer(obj.sku, context={"user": user}).data], "skus")
    parameters = "；".join(f"{key}：{value}" for key, value in (obj.parameter_values_snapshot or {}).items()) or "—"
    return {
        "entity": "sku-versions",
        "title": f"{obj.display_name_cn_snapshot or (obj.sku.product.name if user_can(user, 'products', 'view') else obj.sku_code_snapshot)} · v{obj.version_no}",
        "subtitle": f"{obj.sku.sku} · 历史 SKU 版本",
        "badge": "历史快照",
        "info": [
            ["版本号", obj.version_no], ["变更时间", obj.changed_at], ["SKU Code", obj.sku_code_snapshot],
            ["历史内部名称", obj.display_name_cn_snapshot or "—"], ["历史 Sales Model", obj.sales_model_snapshot or "—"],
            ["历史中文描述", obj.description_cn_snapshot or "—"], ["历史英文描述", obj.description_en_snapshot or "—"],
            ["历史参数", parameters], ["变更字段", "、".join(obj.changed_fields or []) or "—"],
            ["变更说明", obj.change_reason or "—"], ["操作人", obj.changed_by.get_username() if obj.changed_by and user_can(user, "employees", "view") else ""],
        ],
        "metrics": [],
        "sections": [
            _section("sku", "当前 SKU", "skus", [["sku", "SKU Code"], ["display_name_cn", "当前内部名称"], ["sales_model", "当前 Sales Model"], ["active", "状态", "sku-active"]], current_sku),
        ],
    }


def _supplier_sku_context(pk, user=None):
    obj = get_object_or_404(SupplierSKU.objects.select_related("supplier", "sku", "sku__product"), pk=pk)
    sales_order_items = obj.sales_order_items.select_related("order__customer")
    if user is not None:
        sales_order_items = scope_customer_related_queryset(sales_order_items, user, relation="order__customer") if user_can(user, "orders", "view") else sales_order_items.none()
    orders = _target([{
        "id": item.order_id,
        "order_no": item.order.order_no,
        "order_date": item.order.order_date,
        "customer_name": item.order.customer.name if user_can(user, "customers", "view") else "",
        "quantity": item.quantity,
        "supplier_name": item.supplier_name_snapshot,
        "supplier_sku_code": item.supplier_sku_code_snapshot,
    } for item in sales_order_items], "orders")
    purchase_items = list(obj.purchase_items.select_related("purchase_order__order"))
    purchase_order_ids = {item.purchase_order.order_id for item in purchase_items if item.purchase_order.order_id}
    if user is None:
        visible_purchase_order_ids = purchase_order_ids
    elif user_can(user, "orders", "view"):
        visible_purchase_order_ids = set(scope_customer_related_queryset(
            Order.objects.filter(pk__in=purchase_order_ids), user,
        ).values_list("pk", flat=True))
    else:
        visible_purchase_order_ids = set()
    purchases = _target([{
        "id": item.purchase_order_id,
        "purchase_no": item.purchase_order.purchase_no,
        "order_no": item.purchase_order.order.order_no if item.purchase_order.order_id in visible_purchase_order_ids else "",
        "order_date": item.purchase_order.order_date,
        "quantity": item.quantity,
        "unit_price": item.unit_price,
    } for item in purchase_items], "purchase-orders")
    internal_name = obj.sku.display_name_cn or (obj.sku.product.name if user_can(user, "products", "view") else obj.sku.sku)
    can_view_skus = user_can(user, "skus", "view")
    can_view_purchases = user_can(user, "purchases", "view")
    return {
        "entity": "supplier-skus",
        "title": obj.supplier_sku_code,
        "subtitle": f"{obj.supplier.name} · {internal_name if can_view_skus else '供应商来源'}",
        "badge": "首选" if obj.is_preferred else ("启用" if obj.is_active else "停用"),
        "info": [
            ["供应商", obj.supplier.name], ["内部 SKU", obj.sku.sku if can_view_skus else "—"], ["内部名称", internal_name if can_view_skus else "—"],
            ["供应商型号", obj.supplier_model or "—"], ["供应商产品名", obj.supplier_product_name or "—"],
            ["供应商条码", obj.supplier_barcode or "—"], ["参考采购价", obj.purchase_price if can_view_purchases else None], ["币种", obj.currency],
            ["MOQ", obj.moq], ["交期（天）", obj.lead_time_days], ["备注", obj.remarks or "—"],
        ],
        "metrics": [["销售订单行", len(orders), "number"], ["采购明细行", len(purchases), "number"]],
        "sections": [
            _section("orders", "销售订单引用", "orders", [["order_no", "订单"], ["order_date", "日期", "date"], ["customer_name", "客户"], ["quantity", "数量", "number"], ["supplier_sku_code", "供应商 SKU"]], orders),
            _section("purchases", "采购明细", "purchase-orders", [["purchase_no", "采购单"], ["order_no", "关联订单"], ["order_date", "日期", "date"], ["quantity", "数量", "number"], ["unit_price", "采购价", "money"]], purchases),
        ],
    }


def _quote_context(pk, user=None):
    queryset = Quote.objects.select_related("customer", "root_quote").prefetch_related("items")
    if user is not None:
        queryset = scope_customer_related_queryset(queryset, user)
    obj = get_object_or_404(queryset, pk=pk)
    context = {"user": user}
    customer = _target([CustomerSerializer(obj.customer, context=context).data], "customers")
    items = _target([{"id": item.sku_id, "sku_code": item.sku_code_snapshot if user_can(user, "skus", "view") else "", "sales_model": item.sales_model_snapshot if user_can(user, "skus", "view") else "", "product_name": item.product_name_snapshot if user_can(user, "products", "view") else "", "quantity": item.quantity, "unit_price": item.unit_price, "amount": item.amount, "notes": item.notes} for item in obj.items.all()], "skus")
    order_queryset = obj.orders.prefetch_related("items__sku__product", "transactions")
    if user is not None:
        order_queryset = scope_customer_related_queryset(order_queryset, user) if user_can(user, "orders", "view") else order_queryset.none()
    orders = _target(OrderSerializer(order_queryset, many=True, context=context).data, "orders")
    root = obj.root_quote or obj
    revision_label = f"Revision {obj.revision_no}" if obj.revision_no else "Original"
    buyer_name = obj.buyer_company_name if user_can(user, "customers", "view") else "报价"
    return {"entity": "quotes", "title": obj.quote_no, "subtitle": f"{buyer_name} · {obj.quote_date}", "badge": obj.get_status_display(), "lineage": {"root_quote_id": root.id, "root_quote_no": root.quote_no, "revision_no": obj.revision_no, "revision_label": revision_label}, "info": [["报价日期", obj.quote_date], ["有效期至", obj.valid_until or "—"], ["原始报价", root.quote_no], ["当前版本", revision_label], ["币种", obj.currency], ["汇率", obj.exchange_rate], ["备注", obj.notes or "—"]], "metrics": [["报价总额", obj.total_amount, "money"], ["明细", len(items), "number"], ["转订单", len(orders), "number"]], "sections": [
        _section("items", "报价明细", "skus", [["sales_model", "Model"], ["sku_code", "SKU Code"], ["product_name", "内部名称"], ["quantity", "数量", "number"], ["unit_price", "单价", "money"], ["amount", "小计", "money"]], items),
        _section("orders", "关联订单", "orders", [["order_no", "订单号"], ["order_date", "日期", "date"], ["status_display", "状态", "status"], ["total_amount", "金额", "money"]], orders),
        _section("customer", "客户", "customers", [["code", "客户编号"], ["name", "客户名称"], ["country", "国家"], ["owner", "负责人"]], customer),
    ]}


def _order_context(pk, user=None):
    queryset = Order.objects.select_related("customer", "quote").prefetch_related("items__sku__product", "items__supplier_sku__supplier", "transactions")
    if user is not None:
        queryset = scope_customer_related_queryset(queryset, user)
    obj = get_object_or_404(queryset, pk=pk)
    context = {"user": user}
    customer = _target([CustomerSerializer(obj.customer, context=context).data], "customers")
    quote = _target([QuoteSerializer(obj.quote, context=context).data], "quotes") if obj.quote else []
    items = _target([{"id": item.sku_id, "order_item_id": item.pk, "sku_code": (item.sku_code_snapshot or item.sku.sku) if user_can(user, "skus", "view") else "", "sales_model": item.sales_model_snapshot if user_can(user, "skus", "view") else "", "product_name": (item.display_name_snapshot or item.sku.display_name_cn or item.sku.product.name) if user_can(user, "products", "view") else "", "quantity": item.quantity, "unit_price": item.unit_price, "cost_price": item.cost_price if user_can(user, "purchases", "view") else None, "amount": item.amount, "supplier_name": (item.supplier_name_snapshot or "") if user_can(user, "suppliers", "view") else "", "supplier_sku_code": (item.supplier_sku_code_snapshot or "") if user_can(user, "suppliers", "view") else ""} for item in obj.items.all()], "skus")
    payments = _target(TransactionSerializer(obj.transactions.all(), many=True, context=context).data, "transactions")
    inventory = _target(InventoryMovementSerializer(obj.inventory_movements.select_related("sku__product"), many=True, context={"user": user}).data, "inventory-movements")
    quote_no = obj.quote.quote_no if obj.quote and user_can(user, "quotes", "view") else "—"
    customer_name = obj.customer.name if user_can(user, "customers", "view") else "销售订单"
    return {"entity": "orders", "title": obj.order_no, "subtitle": f"{customer_name} · {obj.order_date}", "badge": obj.get_status_display(), "info": [["订单日期", obj.order_date], ["预计交期", obj.expected_ship_date or "—"], ["币种", obj.currency], ["汇率", obj.exchange_rate], ["来源报价", quote_no], ["备注", obj.notes or "—"]], "metrics": [["订单金额", obj.total_amount, "money"], ["已收款", obj.paid_amount, "money"], ["当前待收款", obj.outstanding_amount, "money"], ["明细", len(items), "number"]], "sections": [
        _section("items", "订单明细", "skus", [["sales_model", "Model"], ["sku_code", "SKU Code"], ["product_name", "内部名称"], ["supplier_name", "本次供应商"], ["supplier_sku_code", "供应商 SKU"], ["quantity", "数量", "number"], ["unit_price", "售价", "money"], ["cost_price", "成本", "money"], ["amount", "小计", "money"]], items),
        _section("payments", "收付款流水", "transactions", [["transaction_date", "日期", "date"], ["transaction_no", "流水号"], ["direction_display", "方向"], ["category", "分类"], ["amount", "金额", "money"], ["currency", "币种"]], payments),
        _section("inventory", "出入库流水", "inventory-movements", [["movement_date", "日期", "date"], ["movement_no", "流水号"], ["type_display", "类型"], ["sku_code", "SKU"], ["signed_quantity", "变动", "signed"], ["warehouse", "仓库"]], inventory),
        _section("quote", "来源报价", "quotes", [["quote_no", "报价单号"], ["quote_date", "日期", "date"], ["status_display", "状态", "status"], ["total_amount", "金额", "money"]], quote),
        _section("customer", "客户", "customers", [["code", "客户编号"], ["name", "客户名称"], ["country", "国家"], ["owner", "负责人"]], customer),
    ]}


def _supplier_context(pk, user=None):
    obj = get_object_or_404(Supplier, pk=pk)
    products = _target(ProductSerializer(obj.products.select_related("category"), many=True, context={"user": user}).data, "products")
    supplier_skus = _target(SupplierSKUSerializer(obj.supplier_skus.select_related("supplier", "sku", "sku__product"), many=True, context={"user": user}).data, "supplier-skus")
    purchases = _target(PurchaseOrderSerializer(prefetch_purchase_related_orders(obj.purchase_orders.select_related("supplier", "order").prefetch_related("items__sku", "items__receipts", "transactions")), many=True, context={"user": user}).data, "purchase-orders")
    payments = _target(TransactionSerializer(obj.transactions.select_related("customer", "order", "purchase_order"), many=True, context={"user": user}).data, "transactions")
    formal_purchases = [row for row in purchases if row["status"] in {"ordered", "partial", "completed"}]
    total_purchases_rmb = sum((Decimal(row["total_amount"]) * Decimal(row["exchange_rate"]) for row in formal_purchases), Decimal("0"))
    total_paid_rmb = sum((Decimal(row.get("paid_amount", "0")) * Decimal(row["exchange_rate"]) for row in formal_purchases), Decimal("0"))
    return {"entity": "suppliers", "title": obj.name, "subtitle": obj.contact_name or "供应商", "badge": obj.code,
        "info": [["二字代码", obj.code], ["国家/地区", obj.country or "—"], ["主要产品", obj.main_products or "—"], ["店铺链接", obj.store_url or "—"], ["联系人", obj.contact_name or "—"], ["电话", obj.phone or "—"], ["邮箱", obj.email or "—"], ["付款条款说明（备注）", obj.payment_terms or "—"], ["备注", obj.notes or "—"]],
        "metrics": [["合作产品", len(products), "number"], ["供货档案", len(supplier_skus), "number"], ["采购单记录", len(formal_purchases), "number"], ["正式采购金额（人民币）", total_purchases_rmb, "rmb"], ["已付采购款（人民币）", total_paid_rmb, "rmb"]],
        "sections": [
            _section("products", "合作产品", "products", [["code", "产品编号"], ["name", "产品名称"], ["category_name", "分类"], ["status", "状态", "status"]], products),
            _section("supplier-skus", "供应商 SKU 档案", "supplier-skus", [["internal_sku_code", "内部 SKU"], ["internal_sku_name", "内部名称"], ["supplier_sku_code", "供应商 SKU"], ["supplier_model", "供应商型号"], ["purchase_price", "参考采购价", "money"], ["currency", "币种"], ["moq", "MOQ", "number"], ["lead_time_days", "交期（天）", "number"], ["is_preferred", "首选", "boolean"], ["is_active", "启用", "boolean"]], supplier_skus),
            _section("purchases", "采购单", "purchase-orders", [["purchase_no", "采购单号"], ["order_no", "关联订单"], ["order_date", "下单日期", "date"], ["expected_arrival_date", "预计到货", "date"], ["status", "状态", "status"], ["total_amount", "金额", "money"], ["currency", "币种"]], purchases),
            _section("payments", "付款流水", "transactions", [["transaction_date", "日期", "date"], ["transaction_no", "流水号"], ["category", "分类"], ["amount", "金额", "money"], ["currency", "币种"], ["status", "状态", "status"]], payments),
        ]}


def _purchase_order_context(pk, user=None):
    obj = get_object_or_404(PurchaseOrder.objects.select_related("supplier", "order").prefetch_related("items__sku__product", "transactions"), pk=pk)
    supplier = _hide_supplier_payment_rules(_target([SupplierSerializer(obj.supplier, context={"user": user}).data], "suppliers"))
    visible_order = scope_customer_related_queryset(Order.objects.filter(pk=obj.order_id), user).first() if obj.order_id else None
    order = _target([OrderSerializer(visible_order, context={"user": user}).data], "orders") if visible_order and user_can(user, "orders", "view") else []
    items = _target([{"id": item.sku_id if user_can(user, "skus", "view") else None, "sku_code": item.sku.sku if user_can(user, "skus", "view") else "", "product_name": item.sku.product.name if user_can(user, "products", "view") else "", "quantity": item.quantity, "unit_price": item.unit_price, "amount": item.amount} for item in obj.items.all()], "skus")
    payments = _target(TransactionSerializer(obj.transactions.all(), many=True, context={"user": user}).data, "transactions")
    supplier_name = obj.supplier.name if user_can(user, "suppliers", "view") else "采购单"
    return {"entity": "purchase-orders", "title": obj.purchase_no, "subtitle": f"{supplier_name} · {obj.order_date}", "badge": obj.get_status_display(),
        "info": [["下单日期", obj.order_date], ["预计到货", obj.expected_arrival_date or "—"], ["币种", obj.currency], ["汇率", obj.exchange_rate], ["关联订单", visible_order.order_no if order else "—"], ["备注", obj.notes or "—"]],
        "metrics": [["采购金额", obj.total_amount, "money"], ["已付款", obj.paid_amount, "money"], ["待付款", obj.unpaid_amount, "money"], ["明细", len(items), "number"]],
        "sections": [
            _section("items", "采购明细", "skus", [["sku_code", "SKU"], ["product_name", "产品"], ["quantity", "数量", "number"], ["unit_price", "单价", "money"], ["amount", "小计", "money"]], items),
            _section("supplier", "供应商", "suppliers", [["name", "供应商"], ["code", "二字代码"], ["store_url", "店铺链接"], ["contact_name", "联系人"], ["phone", "电话"]], supplier),
            _section("order", "关联订单", "orders", [["order_no", "订单号"], ["order_date", "日期", "date"], ["status_display", "状态", "status"], ["total_amount", "金额", "money"]], order),
            _section("payments", "付款流水", "transactions", [["transaction_date", "日期", "date"], ["transaction_no", "流水号"], ["amount", "金额", "money"], ["currency", "币种"], ["status", "状态", "status"]], payments),
        ]}


def _follow_up_context(pk, user=None):
    queryset = FollowUp.objects.select_related("customer", "contact")
    if user is not None:
        queryset = scope_customer_related_queryset(queryset, user)
    obj = get_object_or_404(queryset, pk=pk)
    customer = _target([CustomerSerializer(obj.customer, context={"user": user}).data], "customers")
    contact = _target([ContactSerializer(obj.contact, context={"user": user}).data], "contacts") if obj.contact else []
    followed_at = obj.followed_at
    if followed_at and timezone.is_aware(followed_at):
        followed_at = timezone.localtime(followed_at)
    customer_name = obj.customer.name if user_can(user, "customers", "view") else "跟进记录"
    return {"entity": "follow-ups", "title": obj.subject or "跟进记录", "subtitle": f"{customer_name} · {followed_at:%Y-%m-%d %H:%M}" if followed_at else customer_name, "badge": obj.get_type_display(), "info": [["跟进人", obj.owner or "—"], ["跟进记录 / 解决方案", obj.content or "—", "richtext"], ["客户回复 / 客户疑问", obj.result or "—", "richtext"], ["下一步", obj.next_action or "—"], ["下次跟进安排", obj.get_next_follow_up_mode_display()], ["下次跟进", obj.next_follow_up or "—"]], "attachments": FollowUpAttachmentSerializer(obj.attachments.all(), many=True, context={"user": user}).data, "metrics": [], "sections": [
        _section("customer", "客户", "customers", [["code", "客户编号"], ["name", "客户名称"], ["country", "国家"], ["owner", "负责人"]], customer),
        _section("contact", "联系人", "contacts", [["name", "姓名"], ["title", "职位"], ["email", "邮箱"], ["phone", "电话"]], contact),
    ]}


def _category_context(pk, user=None):
    obj = get_object_or_404(ProductCategory, pk=pk)
    products = _target(ProductSerializer(obj.products.select_related("category"), many=True, context={"user": user}).data, "products")
    can_view_products = user_can(user, "products", "view")
    return {"entity": "categories", "title": obj.name, "subtitle": "产品分类", "badge": f"{len(products)} 个产品" if can_view_products else "产品分类", "info": [["说明", obj.description or "—"]], "metrics": [["产品数量", len(products), "number"]] if can_view_products else [], "sections": [_section("products", "分类产品", "products", [["code", "产品编号"], ["name", "产品名称"], ["status", "状态", "status"]], products)]}


def _transaction_context(pk, user=None):
    obj = get_object_or_404(scope_transaction_queryset(Transaction.objects.select_related("customer", "supplier", "order", "purchase_order"), user), pk=pk)
    customer = _target([CustomerSerializer(obj.customer, context={"user": user}).data], "customers") if obj.customer else []
    supplier = _hide_supplier_payment_rules(_target([SupplierSerializer(obj.supplier, context={"user": user}).data], "suppliers")) if obj.supplier else []
    order = _target([OrderSerializer(obj.order, context={"user": user}).data], "orders") if obj.order else []
    purchase_order = _target([{"id": obj.purchase_order_id, "purchase_no": obj.purchase_order.purchase_no, "supplier_name": obj.purchase_order.supplier.name if user_can(user, "suppliers", "view") else "", "status_display": obj.purchase_order.get_status_display(), "total_amount": obj.purchase_order.total_amount, "currency": obj.purchase_order.currency}], "purchase-orders") if obj.purchase_order else []
    return {"entity": "transactions", "title": obj.transaction_no, "subtitle": f"{obj.transaction_date} · {obj.category}", "badge": obj.get_direction_display(), "info": [["金额", f"{obj.currency} {obj.amount}"], ["人民币折算参考", obj.amount * obj.exchange_rate], ["支付方式", obj.payment_method or "—"], ["参考号", obj.reference or "—"], ["状态", obj.get_status_display()], ["备注", obj.notes or "—"]], "metrics": [], "sections": [
        _section("customer", "关联客户", "customers", [["code", "客户编号"], ["name", "客户名称"], ["country", "国家"], ["owner", "负责人"]], customer),
        _section("supplier", "关联供应商", "suppliers", [["name", "供应商"], ["code", "二字代码"], ["store_url", "店铺链接"], ["contact_name", "联系人"], ["phone", "电话"]], supplier),
        _section("order", "关联订单", "orders", [["order_no", "订单号"], ["order_date", "日期", "date"], ["status_display", "状态", "status"], ["total_amount", "金额", "money"]], order),
        _section("purchase-order", "关联采购单", "purchase-orders", [["purchase_no", "采购单号"], ["order_no", "关联订单"], ["supplier_name", "供应商"], ["status_display", "状态", "status"], ["total_amount", "金额", "money"], ["currency", "币种"]], purchase_order),
    ]}


def _inventory_context(pk, user=None):
    obj = get_object_or_404(InventoryMovement.objects.select_related("sku__product", "order"), pk=pk)
    context = {"user": user}
    sku = _target([SKUSerializer(obj.sku, context=context).data], "skus")
    product = _target([ProductSerializer(obj.sku.product, context=context).data], "products")
    order_queryset = Order.objects.filter(pk=obj.order_id) if obj.order_id else Order.objects.none()
    if user is not None:
        order_queryset = scope_customer_related_queryset(order_queryset, user)
    order = _target(OrderSerializer(order_queryset, many=True, context=context).data, "orders")
    info = [["SKU", obj.sku.sku if user_can(user, "skus", "view") else "—"], ["基础数量", f"{obj.quantity} {obj.trade_snapshot.get('base_unit', obj.sku.unit)}"], ["交易规格", obj.trade_snapshot.get("name") or "基础单位登记"], ["交易数量", f"{obj.trade_quantity} {obj.trade_snapshot.get('unit', '')}" if obj.trade_unit_id else "—"], ["仓库", obj.warehouse]]
    if user_can(user, "purchases", "view"):
        info.append(["单位成本", obj.unit_cost])
    info.extend([["参考号", obj.reference or "—"], ["备注", obj.notes or "—"]])
    return {"entity": "inventory-movements", "title": obj.movement_no, "subtitle": f"{obj.movement_date} · {obj.get_type_display()}", "badge": f"{obj.signed_quantity:+}", "info": info, "metrics": [], "sections": [
        _section("sku", "关联 SKU", "skus", [["sku", "SKU"], ["product_name", "产品"], ["specification", "规格"], ["unit", "单位"]], sku),
        _section("product", "所属产品", "products", [["code", "产品编号"], ["name", "产品名称"], ["status", "状态", "status"]], product),
        _section("order", "关联订单", "orders", [["order_no", "订单号"], ["order_date", "日期", "date"], ["status_display", "状态", "status"]], order),
    ]}


def _parameter_context(pk, user=None):
    obj = get_object_or_404(ProductParameter.objects.select_related("product"), pk=pk)
    product = _target([ProductSerializer(obj.product, context={"user": user}).data], "products")
    product_name = obj.product.name if user_can(user, "products", "view") else "产品"
    return {"entity": "product-parameters", "title": obj.name, "subtitle": f"{obj.group} · {product_name}", "badge": f"{obj.value} {obj.unit}".strip(), "info": [["参数值", obj.value], ["单位", obj.unit or "—"], ["排序", obj.sort_order]], "metrics": [], "sections": [_section("product", "所属产品", "products", [["code", "产品编号"], ["name", "产品名称"], ["status", "状态", "status"]], product)]}


def _certificate_context(pk, user=None):
    obj = get_object_or_404(ProductCertificate.objects.select_related("product"), pk=pk)
    product = _target([ProductSerializer(obj.product, context={"user": user}).data], "products")
    product_name = obj.product.name if user_can(user, "products", "view") else "产品"
    return {"entity": "product-certificates", "title": obj.name, "subtitle": f"{product_name} · {obj.certificate_no or '未填写编号'}", "badge": obj.issuer or "证书", "info": [["签发机构", obj.issuer or "—"], ["签发日期", obj.issued_date or "—"], ["有效期至", obj.expires_on or "—"], ["文件链接", protected_media_url(obj.file) or "—"], ["备注", obj.notes or "—"]], "metrics": [], "sections": [_section("product", "所属产品", "products", [["code", "产品编号"], ["name", "产品名称"], ["status", "状态", "status"]], product)]}

