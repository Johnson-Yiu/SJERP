Warning: truncated output (original token count: 30158)
Total output lines: 2277

from .trade_units import TradeLineSerializerMixin, TRADE_FIELDS, SKUTradeUnitSerializer, trade_values, validate_document_amount
from decimal import Decimal
import re
from uuid import uuid4

import bleach

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.html import strip_tags
from rest_framework import serializers

from .models import ShipmentItem
from .models import AccessRole, CategoryAttribute, Contact, ContractChangeRequest, Customer, CustomerCodeSequence, EmployeeProfile, FollowUp, FollowUpAttachment, GoodsReceipt, HSCode, InventoryMovement, OperationLog, Order, OrderItem, OrganizationUnit, PackagingTemplate, PackingPlan, PackingPlanCarton, PackingPlanCartonItem, PaymentPlan, Position, Product, ProductCategory, ProductCertificate, ProductCodeSequence, ProductParameter, PurchaseOrder, PurchaseOrderItem, Quote, QuoteImportantNote, QuoteItem, RolePermission, Shipment, ShipmentPackage, ShipmentPackageItem, SKUPackagingProfile, SKU, SKUVersion, Supplier, SupplierSKU, Transaction
from .supplier_display import payment_terms_summary
from .quote_numbers import allocate_revision_quote_no, allocate_root_quote_no
from .document_numbers import allocate_order_no, allocate_purchase_no
from .quote_snapshots import create_quote_items
from .sku_identity import build_sku_identity, category_attributes, complete_sales_model_abbreviations, identity_conflict_messages, identity_signature, normalize_display_name, normalize_sales_model_abbreviations, parameter_pairs, raw_parameter_value
from .sku_numbers import allocate_sku_code
from .services.sku_schema import (
    UNFROZEN_CATEGORY_HIERARCHY_MESSAGE,
    UNFROZEN_PRODUCT_CATEGORY_MESSAGE,
    product_has_unfrozen_sku_schema,
    unfrozen_products_using_category_scope,
    unfrozen_schema_error,
)


def customer_sequence_suffix(value):
    if value <= 9999:
        return f"{value:04d}"
    letter_index, number = divmod(value - 10000, 1000)
    if letter_index >= 26:
        raise serializers.ValidationError({"code": "客户编号流水已超出 Z999，请扩展编号规则。"})
    return f"{chr(ord('A') + letter_index)}{number:03d}"


def allocate_customer_code():
    from django.utils import timezone

    sequence, _ = CustomerCodeSequence.objects.select_for_update().get_or_create(pk=1, defaults={"last_value": -1})
    sequence.last_value += 1
    sequence.save(update_fields=["last_value"])
    return f"{timezone.localdate():%Y%m%d}{customer_sequence_suffix(sequence.last_value)}"


def next_product_code():
    from django.utils import timezone

    today = timezone.localdate()
    sequence = ProductCodeSequence.objects.filter(code_date=today).first()
    value = (sequence.last_value if sequence else 0) + 1
    if value > 999:
        raise serializers.ValidationError({"code": "当日产品编号已超过 999，请联系管理员扩展编号规则。"})
    return f"SPU{today:%y%m%d}{value:03d}"


IMPORTANT_NOTE_TAGS = ["p", "br", "strong", "em", "ul", "ol", "li", "a"]
IMPORTANT_NOTE_ATTRIBUTES = {"a": ["href", "target", "rel"]}
IMPORTANT_NOTE_PROTOCOLS = ["http", "https", "mailto"]


def sanitize_important_note(value):
    content = bleach.clean(
        value or "",
        tags=IMPORTANT_NOTE_TAGS,
        attributes=IMPORTANT_NOTE_ATTRIBUTES,
        protocols=IMPORTANT_NOTE_PROTOCOLS,
        strip=True,
    ).strip()
    if not strip_tags(content).strip():
        raise serializers.ValidationError("备注内容不能为空。")
    return content


def allocate_product_code():
    from django.utils import timezone

    today = timezone.localdate()
    sequence, _ = ProductCodeSequence.objects.select_for_update().get_or_create(code_date=today, defaults={"last_value": 0})
    sequence.last_value += 1
    if sequence.last_value > 999:
        raise serializers.ValidationError({"code": "当日产品编号已超过 999，请联系管理员扩展编号规则。"})
    sequence.save(update_fields=["last_value"])
    return f"SPU{today:%y%m%d}{sequence.last_value:03d}"


class PositionSerializer(serializers.ModelSerializer):
    level_display = serializers.CharField(source="get_level_display", read_only=True)

    class Meta:
        model = Position
        fields = "__all__"


class SupplierSerializer(serializers.ModelSerializer):
    payment_terms_summary = serializers.SerializerMethodField()

    def get_payment_terms_summary(self, obj):
        return payment_terms_summary(obj.payment_terms_config)

    def validate_payment_terms_config(self, value):
        from .payment_terms import validate_payment_terms
        try:
            return validate_payment_terms(value, allow_default=True)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages)

    supply_category_names = serializers.SlugRelatedField(source="supply_categories", slug_field="name", many=True, read_only=True)

    def validate(self, attrs):
        if (self.instance is None or "supply_categories" in attrs) and not attrs.get("supply_categories"):
            raise serializers.ValidationError({"supply_categories": "请选择至少一个可供产品大类或子分类。"})
        return attrs

    purchase_count = serializers.IntegerField(source="purchase_orders.count", read_only=True)
    code = serializers.CharField(min_length=2, max_length=2)

    def validate_code(self, value):
        code = str(value or "").strip().upper()
        if not re.fullmatch(r"[A-Z]{2}", code):
            raise serializers.ValidationError("供应商二字代码必须为两个英文字母。")
        duplicates = Supplier.objects.filter(code__iexact=code)
        if self.instance:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        existing = duplicates.first()
        if existing:
            raise serializers.ValidationError(f"{code} 与 {existing.name}-{existing.code} 重复")
        return code

    class Meta:
        model = Supplier
        fields = "__all__"
        read_only_fields = ["purchase_count", "created_at", "updated_at"]


class SupplierSKUSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)
    internal_sku_code = serializers.CharField(source="sku.sku", read_only=True)
    internal_sku_name = serializers.CharField(source="sku.display_name_cn", read_only=True)
    product_name = serializers.CharField(source="sku.product.name", read_only=True)
    purchase_price = serializers.DecimalField(max_digits=14, decimal_places=4, min_value=Decimal("0"))
    moq = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0"))
    lead_time_days = serializers.IntegerField(min_value=0)

    class Meta:
        model = SupplierSKU
        fields = "__all__"

    def validate(self, attrs):
        if self.instance:
            for field in ("sku", "supplier"):
                if field in attrs and attrs[field].pk != getattr(self.instance, f"{field}_id"):
                    raise serializers.ValidationError({field: "供货档案不能改挂其他 SKU 或供应商，请新增档案。"})
        if "characteristics" in attrs and not isinstance(attrs["characteristics"], dict):
            raise serializers.ValidationError({"characteristics": "供货特点须为名称和取值。"})
        return attrs

    def create(self, validated_data):
        from .services.supplier_sku import create_supplier_sku
        return create_supplier_sku(validated_data)

    def update(self, instance, validated_data):
        from .services.supplier_sku import update_supplier_sku
        return update_supplier_sku(instance, validated_data)


class OperationLogSerializer(serializers.ModelSerializer):
    entity_display = serializers.CharField(source="entity_label", read_only=True)
    action_display = serializers.CharField(source="action_label", read_only=True)
    operator_name = serializers.SerializerMethodField()

    class Meta:
        model = OperationLog
        fields = [
            "id", "entity", "entity_display", "object_id", "object_label", "action", "action_display",
            "operator_name", "changed_fields", "before_data", "after_data", "metadata",
            "request_method", "request_path", "created_at",
        ]
        read_only_fields = fields

    def get_operator_name(self, obj):
        return obj.operator.get_username() if obj.operator else "系统"


class GoodsReceiptSerializer(serializers.ModelSerializer):
    overage_quantity = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    overage_reason_display = serializers.CharField(source="get_overage_reason_display", read_only=True)
    overage_summary = serializers.SerializerMethodField()

    def get_overage_summary(self, obj):
        if not obj.is_overage or obj.overage_quantity <= 0:
            return ""
        return f"超到 {obj.overage_quantity}（{obj.get_overage_reason_display()}）"

    class Meta:
        model = GoodsReceipt
        fields = ["id", "receipt_date", "quantity", "unit_cost", "notes", "is_overage", "overage_reason", "overage_reason_display", "overage_quantity", "overage_summary", "inventory_movement", "reversal_inventory_movement", "reversed_at", "reversal_reason"]
        read_only_fields = fields


class ReceiptReversalInputSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500, allow_blank=False, trim_whitespace=True)


class InventoryMovementReversalInputSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500, allow_blank=False, trim_whitespace=True)


class TransactionVoidInputSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500, allow_blank=False, trim_whitespace=True)


class ProcurementDraftItemInputSerializer(serializers.Serializer):
    order_item = serializers.IntegerField()
    quantity = serializers.DecimalField(max_digits=18, decimal_places=2, min_value=Decimal("0"))
    unit_price = serializers.DecimalField(max_digits=24, decimal_places=12, min_value=Decimal("0"))


class ProcurementDraftGroupInputSerializer(serializers.Serializer):
    supplier = serializers.IntegerField()
    currency = serializers.CharField(max_length=10)
    exchange_rate = serializers.DecimalField(max_digits=12, decimal_places=6, required=False, allow_null=True)
    expected_arrival_date = serializers.DateField(required=False, allow_null=True)
    items = ProcurementDraftItemInputSerializer(many=True)


class ProcurementDraftInputSerializer(serializers.Serializer):
    groups = ProcurementDraftGroupInputSerializer(many=True)


class PurchaseOrderItemSerializer(TradeLineSerializerMixin, serializers.ModelSerializer):
    amount = serializers.DecimalField(max_digits=28, decimal_places=4, read_only=True)
    sku_code = serializers.CharField(source="sku_code_snapshot", read_only=True)
    display_name = serializers.CharField(source="display_name_snapshot", read_only=True)
    sales_model = serializers.CharField(source="sales_model_snapshot", read_only=True)
    supplier_name = serializers.CharField(source="supplier_name_snapshot", read_only=True)
    supplier_model = serializers.CharField(source="supplier_model_snapshot", read_only=True)
    supplier_sku_code = serializers.CharField(source="supplier_sku_code_snapshot", read_only=True)
    supplier_barcode = serializers.CharField(source="supplier_barcode_snapshot", read_only=True)
    received_quantity = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    remaining_quantity = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    overage_quantity = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    receipts = serializers.SerializerMethodField()

    def get_receipts(self, obj):
        return GoodsReceiptSerializer(obj.receipts.all(), many=True).data

    class Meta:
        model = PurchaseOrderItem
        fields = ["id", "sku", "supplier_sku", "sku_code", "display_name", "sales_model", "supplier_name", "supplier_model", "supplier_sku_code", "supplier_barcode", "supplier_characteristics_snapshot", "quantity", "unit_price", "received_quantity", "remaining_quantity", "overage_quantity", "amount", "receipts"] + TRADE_FIELDS
        read_only_fields = ["supplier_characteristics_snapshot"]


def normalized_contract_item_signature(item, *, include_supplier_sku=False):
    def related_id(value):
        return value.pk if hasattr(value, "pk") else value

    signature = (
        related_id(item["sku"]),
        Decimal(item["quantity"]),
        Decimal(item["unit_price"]),
        Decimal(item.get("cost_price", 0)),
        item.get("notes", ""),
        related_id(item.get("trade_unit")),
        item.get("trade_quantity"),
        item.get("trade_unit_price"),
    )
    if include_supplier_sku:
        signature += (related_id(item.get("supplier_sku")),)
    return signature


def contract_items_match(instance, items):
    include_supplier_sku = isinstance(instance, PurchaseOrder)
    incoming_items = [
        normalized_contract_item_signature(item, include_supplier_sku=include_supplier_sku)
        for item in items
    ]
    existing_items = []
    for item in instance.items.order_by("id"):
        signature = (
            item.sku_id,
            Decimal(item.quantity),
            Decimal(item.unit_price),
            Decimal(getattr(item, "cost_price", 0)),
            getattr(item, "notes", ""),
            item.trade_unit_id,
            item.trade_quantity,
            item.trade_unit_price,
        )
        if include_supplier_sku:
            signature += (item.supplier_sku_id,)
        existing_items.append(signature)
    return incoming_items == existing_items


def validate_contract_edit(instance, attrs, *, purchase=False):
    validate_document_amount(attrs, instance)
    if attrs.get("exchange_rate", Decimal("1")) <= 0:
        raise serializers.ValidationError({"exchange_rate": "汇率必须大于零。"})
    if "items" in attrs and not attrs["items"]:
        raise serializers.ValidationError({"items": "合同至少需要一条商品明细。"})
    for item in attrs.get("items", []):
        if item["quantity"] <= 0 or item["unit_price"] < 0:
            raise serializers.ValidationError({"items": "数量必须大于零，单价不能为负。"})
    if not instance:
        if attrs.get("status") in {"completed", "shipped", "partial"}:
            raise serializers.ValidationError("新合同请从草稿或已确认/已下单开始。")
        return
    history = (instance.items.filter(receipts__isnull=False).exists() if purchase else
        instance.shipments.exists() or instance.purchase_orders.exclude(status="cancelled").exists())
    financial = instance.transactions.exists() or instance.payment_plans.filter(settled_amount__gt=0).exists() or instance.payment_plans.filter(advance_allocations__isnull=False).exists()
    sensitive = {"items", "currency", "exchange_rate", "shipping_fee", "discount", "supplier" if purchase else "customer", "order" if purchase else "quote"}
    if purchase:
        sensitive.add("payment_terms_snapshot")
    if not purchase:
        sensitive.add("tail_goods_policy")
    items_changed = "items" in attrs and not contract_items_match(instance, attrs["items"])
    scalar_contract_changed = any(
        key in attrs and attrs[key] != getattr(instance, key, None)
        for key in ("currency", "exchange_rate", "order", "supplier")
    )
    if purchase and instance.cost_allocation_version and (scalar_contract_changed or items_changed):
        raise serializers.ValidationError("采购单已有成本分配，不能改写明细、币种、汇率或原始归属；请通过成本分配调整归属。")
    changed = items_changed or any(
        key in attrs and attrs[key] != getattr(instance, key, None)
        for key in sensitive - {"items"}
    )
    if instance.status != "draft" and changed:
        raise serializers.ValidationError("正式合同不能直接改写商品、往来方、币种或金额依据；请在确认前编辑草稿，或使用对应的正式业务流程。")
    if changed and (history or financial):
        raise serializers.ValidationError("合同已有采购、出入库或收付款记录，不能改写商品、往来方及金额依据。请使用追加单或退款记录处理后续变化。")
    new_status = attrs.get("status", instance.status)
    if new_status != instance.status and new_status in {"cancelled", "draft"} and (history or financial):
        raise serializers.ValidationError("合同已有业务记录，不能直接取消或退回草稿。")
    if new_status != instance.status and new_status in ({"partial", "completed"} if purchase else {"shipped", "completed"}):
        if purchase or new_status == "shipped":
            raise serializers.ValidationError("到货、发货状态由实际出入库记录自动更新。")
        if instance.status != "shipped":
            raise serializers.ValidationError("订单尚未全部发货，不能标记为已完成。")
        from .services.fulfillment import order_item_metrics
        if not instance.items.exists() or any(
            order_item_metrics(item)["shipped_quantity"] < item.quantity
            for item in instance.items.all()
        ):
            raise serializers.ValidationError("订单尚未全部发货，不能标记为已完成。")


def sync_unsettled_contract_plans(instance, changed):
    from .services.finance import ensure_default_payment_plans
    if instance.status in {"draft", "cancelled"}:
        instance.payment_plans.filter(settled_amount=0).update(status="cancelled")
        return
    if changed and not instance.transactions.exists() and not instance.payment_plans.filter(advance_allocations__isnull=False).exists():
        instance.payment_plans.all().delete()
    ensure_default_payment_plans(instance)


class PurchaseOrderSerializer(serializers.ModelSerializer):
    payment_plans = serializers.SerializerMethodField()

    def get_payment_plans(self, obj):
        return PaymentPlanSerializer(obj.payment_plans.all().order_by("id"), many=True).data

    def validate_payment_terms_snapshot(self, value):
        from .payment_terms import validate_payment_terms
        try:
            return validate_payment_terms(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages)

    status_display = serializers.CharField(source="get_status_display", read_only=True)
    items = PurchaseOrderItemSerializer(many=True)
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)
    order_no = serializers.CharField(source="order.order_no", read_only=True)
    related_orders = serializers.SerializerMethodField()
    total_amount = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    base_amount = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    approved_change_amount = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    paid_amount = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    unpaid_amount = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = "__all__"
        read_only_fields = ["purchase_no", "status", "cancelled_at", "cancellation_reason"]

    def get_related_orders(self, obj):
        prefetched_items = getattr(obj, "_prefetched_objects_cache", {}).get("items")
        allocations_are_prefetched = prefetched_items is not None and all(
            "cost_allocations" in item._prefetched_objects_cache for item in prefetched_items
        )
        if allocations_are_prefetched:
            allocations = (
                allocation
                for item in prefetched_items
                for allocation in item.cost_allocations.all()
            )
        else:
            from .models import PurchaseCostAllocation

            allocations = PurchaseCostAllocation.objects.filter(
                purchase_item__purchase_order_id=obj.pk,
                target_type="order",
                order__isnull=False,
            ).select_related("order").order_by("order_id", "id")

        unique_orders = {}
        for allocation in allocations:
            if allocation.target_type == "order" and allocation.order_id and allocation.order_id not in unique_orders:
                unique_orders[allocation.order_id] = allocation.order
        return [
            {"id": order_id, "order_no": unique_orders[order_id].order_no}
            for order_id in sorted(unique_orders)
        ]

    def validate(self, attrs):
        if "purchase_no" in self.initial_data:
            raise serializers.ValidationError({"purchase_no": "采购单号由系统自动生成，不能手工指定。"})
        validate_contract_edit(self.instance, attrs, purchase=True)
        currency = attrs.get("currency", getattr(self.instance, "currency", None))
        rate = attrs.get("exchange_rate", getattr(self.instance, "exchange_rate", None))
        if rate is None or rate <= 0:
            raise serializers.ValidationError({"exchange_rate": "请输入大于 0 的采购单对人民币汇率。"})
        if currency == "CNY" and rate != Decimal("1"):
            raise serializers.ValidationError({"exchange_rate": "人民币采购单的对人民币汇率必须为 1。"})
        supplier = attrs.get("supplier", getattr(self.instance, "supplier", None))
        if "payment_terms_snapshot" not in attrs and (self.instance is None or (
            self.instance.status == "draft" and supplier != self.instance.supplier
        )):
            from .payment_terms import default_payment_terms, validate_payment_terms
            try:
                attrs["payment_terms_snapshot"] = validate_payment_terms(supplier.payment_terms_config or default_payment_terms())
            except DjangoValidationError as exc:
                raise serializers.ValidationError({"payment_terms_snapshot": exc.messages})
        unit_rows = attrs.get("items")
        if (
            self.instance is not None
            and self.instance.status == "draft"
            and "supplier" in attrs
            and attrs["supplier"] != self.instance.supplier
            and unit_rows is None
        ):
            raise serializers.ValidationError({"items": "更换采购供应商时必须同时提交采购明细，以重新确认各 SKU 的供应商来源。"})
        units = ([row.get("trade_unit") for row in unit_rows] if unit_rows is not None else
                 [row.trade_unit for row in self.instance.items.select_related("trade_unit")] if self.instance else [])
        if any(unit and unit.supplier_id and (not supplier or unit.supplier_id != supplier.pk) for unit in units):
            raise serializers.ValidationError({"items": "包装规格的供应商必须与采购单供应商一致。"})
        errors = []
        for index, item in enumerate(attrs.get("items", [])):
            if self.instance is None and item.get("sku") and item["sku"].candidate_overrides.filter(supplier=supplier, is_allowed=False).exists():
                raise serializers.ValidationError({"supplier": "该 SKU 已排除此供应商，请先恢复候选资格。"})
            source = item.get("supplier_sku")
            if source is None:
                continue
            if supplier and source.supplier_id != supplier.pk:
                errors.append({"items": {index: {"supplier_sku": "供应商来源必须属于当前采购单供应商。"}}})
            if item.get("sku") and source.sku_id != item["sku"].pk:
                errors.append({"items": {index: {"supplier_sku": "供应商来源必须对应当前采购明细 SKU。"}}})
            if (self.instance is None or self.instance.status == "draft") and not source.is_active:
                errors.append({"items": {index: {"supplier_sku": "新建或编辑采购草稿只能选择启用中的供应商来源。"}}})
        if errors:
            raise serializers.ValidationError(errors[0])
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        items = validated_data.pop("items")
        validated_data.pop("purchase_no", None)
        from .services.supplier_candidates import resolve_purchase_item_sources
        for item in items:
            if not item["sku"].active:
                raise serializers.ValidationError({"sku": "新采购不能选择停用或已归档的 SKU。"})
        resolve_purchase_item_sources(
            items, validated_data["supplier"], order=validated_data.get("order"),
            purchase_currency=validated_data.get("currency"),
        )
        purchase = PurchaseOrder.objects.create(
            purchase_no=allocate_purchase_no(),
            **validated_data,
        )
        PurchaseOrderItem.objects.bulk_create([
            PurchaseOrderItem(
                purchase_order=purchase,
                sku_code_snapshot=item["sku"].sku,
                sales_model_snapshot=item["sku"].sales_model or "",
                display_name_snapshot=item["sku"].display_name_cn or item["sku"].product.name,
                description_snapshot=item["sku"].description_en or item["sku"].description_cn or item["sku"].display_name_cn or item["sku"].product.name,
                supplier_name_snapshot=(
                    item["supplier_sku"].supplier.name
                    if item.get("supplier_sku") else purchase.supplier.name
                ),
                supplier_model_snapshot=item["supplier_sku"].supplier_model if item.get("supplier_sku") else "",
                supplier_sku_code_snapshot=item["supplier_sku"].supplier_sku_code if item.get("supplier_sku") else "",
                supplier_barcode_snapshot=item["supplier_sku"].supplier_barcode if item.get("supplier_sku") else "",
                supplier_characteristics_snapshot=item["supplier_sku"].characteristics if item.get("supplier_sku") else {},
                **item,
            ) for item in items
        ])
        from .services.purchase_costs import rebuild_default_cost_allocations
        rebuild_default_cost_allocations(purchase)
        return purchase

    @transaction.atomic
    def update(self, instance, validated_data):
        instance = PurchaseOrder.objects.select_for_update().get(pk=instance.pk)
        validate_contract_edit(instance, validated_data, purchase=True)
        items = validated_data.pop("items", None)
        target_supplier = validated_data.get("supplier", instance.supplier)
        if items is not None and instance.status == "draft":
            from .services.supplier_candidates import resolve_purchase_item_sources
            resolve_purchase_item_sources(
                items,
                target_supplier,
                order=validated_data.get("order", instance.order),
                purchase_currency=validated_data.get("currency", instance.currency),
            )
        items_match = items is not None and contract_items_match(instance, items)
        if items is not None and (instance.status == "draft" or not items_match):
            instance.items.all().delete()
            for item in items:
                item_data = dict(item)
                if item_data.get("supplier_sku") is None:
                    item_data["supplier_name_snapshot"] = target_supplier.name
                PurchaseOrderItem.objects.create(purchase_order=instance, **item_data)
        for key, value in validated_data.items():
            setattr(instance, key, value)
        instance.save()
        if instance.status == "draft" and instance.cost_allocation_version == 0:
            from .services.purchase_costs import rebuild_default_cost_allocations
            rebuild_default_cost_allocations(instance)
        return instance


class ReceiptInputSerializer(serializers.Serializer):
    trade_unit = serializers.IntegerField(required=False, allow_null=True)
    trade_quantity = serializers.DecimalField(max_digits=14, decimal_places=2, required=False)
    trade_unit_price = serializers.DecimalField(max_digits=16, decimal_places=4, required=False)

    purchase_item = serializers.IntegerField()
    receipt_date = serializers.DateField()
    quantity = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.01"), required=False)
    unit_cost = serializers.DecimalField(max_digits=24, decimal_places=12, min_value=Decimal("0"), required=False, default=0)
    is_overage = serializers.BooleanField(required=False, default=False)
    overage_reason = serializers.CharField(required=False, allow_blank=True, max_length=30)
    notes = serializers.CharField(required=False, allow_blank=True)


class SupplierPaymentInputSerializer(serializers.Serializer):
    transaction_date = serializers.DateField()
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.01"))
    currency = serializers.CharField(max_length=10, required=False)
    exchange_rate = serializers.DecimalField(max_digits=12, decimal_places=6, min_value=Decimal("0"), required=False)
    payment_method = serializers.CharField(max_length=100, required=False, allow_blank=True)
    reference = serializers.CharField(max_length=100, required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)


class ShipmentLineInputSerializer(serializers.Serializer):
    trade_unit = serializers.IntegerField(required=False, allow_null=True)
    trade_quantity = serializers.DecimalField(max_digits=14, decimal_places=2, required=False)
    trade_unit_price = serializers.DecimalField(max_digits=16, decimal_places=4, required=False)

    order_item = serializers.IntegerField(min_value=1)
    quantity = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.01"), required=False)
    overage_reason = serializers.ChoiceField(choices=["", "customer_addon", "gift_or_sample", "packing_variance"], required=False, allow_blank=True)


class ShipmentInputSerializer(serializers.Serializer):
    shipment_no = serializers.CharField(max_length=40, required=False, allow_blank=True)
    shipment_date = serializers.DateField()
    logistics_provider = serializers.CharField(max_length=100, required=False, allow_blank=True)
    waybill_no = serializers.CharField(max_length=100, required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    items = ShipmentLineInputSerializer(many=True, allow_empty=False)


class ShipmentReversalInputSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500, allow_blank=False, trim_whitespace=True)


class CancellationInputSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500, allow_blank=False, trim_whitespace=True)


class OrganizationUnitSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source="get_type_display", read_only=True)
    positions = PositionSerializer(many=True, read_only=True)
    employee_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = OrganizationUnit
        fields = "__all__"


class RolePermissionSerializer(serializers.ModelSerializer):
    module_display = serializers.CharField(source="get_module_display", read_only=True)

    class Meta:
        model = RolePermission
        fields = "__all__"


class AccessRoleSerializer(serializers.ModelSerializer):
    permissions = RolePermissionSerializer(many=True, read_only=True)
    default_data_scope_display = serializers.CharField(source="get_default_data_scope_display", read_only=True)
    employee_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = AccessRole
        fields = "__all__"


class EmployeeProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    unit_name = serializers.CharField(source="unit.name", read_only=True)
    position_name = serializers.CharField(source="position.name", read_only=True)
    role_names = serializers.SerializerMethodField()

    class Meta:
        model = EmployeeProfile
        fields = "__all__"

    def get_role_names(self, obj):
        return list(obj.roles.values_list("name", flat=True))


class CustomerContactInputSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ["name", "title", "email", "phone", "whatsapp", "is_primary", "notes"]


class CustomerSerializer(serializers.ModelSerializer):
    contact_count = serializers.IntegerField(read_only=True, default=0)
    order_count = serializers.IntegerField(read_only=True, default=0)
    sales_amount = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True, default=0)
    contacts = CustomerContactInputSerializer(many=True, write_only=True, required=False)

    class Meta:
        model = Customer
        fields = "__all__"
        # Customer status is a persisted projection of follow-ups, quotes and
        # formal orders, rather than a manually maintained customer attribute.
        read_only_fields = ["code", "status", "owner"]

    def validate(self, attrs):
        from .sales_scope import allowed_employee_ids, effective_data_scope, employee_profile_for
        from .permissions import user_can

        if self.instance is None and not attrs.get("contacts") and not self.context.get("allow_import_without_contacts"):
            raise serializers.ValidationError({"contacts": "新建客户时请至少填写一位联系人。"})
        request = self.context.get("request")
        user = request.user if request else self.context.get("user")
        if "owner_profile" in attrs:
            owner_profile = attrs["owner_profile"]
            if owner_profile is None:
                if effective_data_scope(user) != "all":
                    raise PermissionDenied("当前账号必须为客户指定数据范围内的负责人。")
            elif owner_profile.pk not in set(allowed_employee_ids(user)):
                raise PermissionDenied("所选负责人不在当前账号的数据范围内。")
            if self.instance and owner_profile != self.instance.owner_profile:
                if not user_can(user, "customers", "update"):
                    raise PermissionDenied("你没有修改客户负责人的权限。")
            if owner_profile:
                attrs["owner"] = owner_profile.display_name
        elif self.instance is None and user is not None:
            profile = employee_profile_for(user)
            if profile and not getattr(user, "is_superuser", False):
                attrs["owner_profile"] = profile
                attrs["owner"] = profile.display_name
            elif effective_data_scope(user) != "all":
                raise PermissionDenied("当前账号没有可用的客户负责人资料。")
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        contacts = validated_data.pop("contacts", [])
        imported_code = validated_data.pop("imported_code", None) if self.context.get("allow_import_code") else None
        customer = Customer.objects.create(code=imported_code or allocate_customer_code(), **validated_data)
        primary_index = next((index for index, row in enumerate(contacts) if row.get("is_primary")), 0)
        for index, row in enumerate(contacts):
            row["is_primary"] = index == primary_index
            Contact.objects.create(customer=customer, **row)
        return customer


class ContactSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.name", read_only=True)

    class Meta:
        model = Contact
        fields = "__all__"


    def validate_customer(self, customer):
        from .sales_scope import customer_in_scope
        request = self.context.get("request")
        if request and not customer_in_scope(customer.pk, request.user):
            raise PermissionDenied("所选客户不在当前账号的数据范围内。")
        return customer

class FollowUpSerializer(serializers.ModelSerializer):
    next_follow_up_mode_display = serializers.CharField(source="get_next_follow_up_mode_display", read_only=True)
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    contact_name = serializers.CharField(source="contact.name", read_only=True, default="")
    type = serializers.CharField()
    type_display = serializers.SerializerMethodField()
    attachments = serializers.SerializerMethodField()

    class Meta:
        model = FollowUp
        fields = "__all__"

    def get_type_display(self, obj):
        return obj.get_type_display()

    def get_attachments(self, obj):
        return FollowUpAttachmentSerializer(obj.attachments.all(), many=True, context=self.context).data

    def validate(self, attrs):
        from .sales_scope import customer_in_scope
        request = self.context.get("request")
        customer = attrs.get("customer", getattr(self.instance, "customer", None))
        contact = attrs.get("contact", getattr(self.instance, "contact", None))
        if request and customer and not customer_in_scope(customer.pk, request.user):
            raise PermissionDenied("所选客户不在当前账号的数据范围内。")
        if contact and customer and contact.customer_id != customer.id:
            raise serializers.ValidationError({"contact": "所选联系人不属于当前客户。"})
        content = attrs.get("content", getattr(self.instance, "content", ""))
        result = attrs.get("result", getattr(self.instance, "result", ""))
        if not str(content or "").strip() and not str(result or "").strip():
            raise serializers.ValidationError("请至少填写跟进记录或客户回复，避免保存空白跟进。")
        mode = attrs.get("next_follow_up_mode", getattr(self.instance, "next_follow_up_mode", "keep"))
        next_date = attrs.get("next_follow_up", getattr(self.instance, "next_follow_up", None))
        if mode == "set" and not next_date:
            raise serializers.ValidationError({"next_follow_up": "请填写新的跟进日期。"})
        if mode == "clear" and attrs.get("next_follow_up"):
            raise serializers.ValidationError({"next_follow_up": "取消跟进计划时，下次跟进日期必须为空。"})
        if mode != "set":
            attrs["next_follow_up"] = None
        return attrs


class FollowUpAttachmentSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = FollowUpAttachment
        fields = ["id", "name", "file", "url", "content_type", "size", "created_at"]
        read_only_fields = fields

    def get_url(self, obj):
        if not obj.file:
            return ""
        request = self.context.get("request")
        return request.build_absolute_uri(obj.file.url) if request else obj.file.url


class CategoryAttributeSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = CategoryAttribute
        fields = "__all__"
        extra_kwargs = {"key": {"required": False}}

    def validate(self, attrs):
        if self.instance:
            if "key" in attrs and attrs["key"] != self.instance.key:
                raise serializers.ValidationError({
                    "key": "参数标识创建后不可修改；如业务含义发生变化，请新增参数并通过 SKU 参数方案处理。"
                })
            if "category" in attrs and attrs["category"].pk != self.instance.category_id:
                raise serializers.ValidationError({"category": "参数创建后不能更换所属分类；如需调整请新建参数。"})
            if "sort_order" in attrs and attrs["sort_order"] != self.instance.sort_order:
                raise serializers.ValidationError({"sort_order": "参数排序请使用正式排序操作。"})
        if not attrs.get("key"):
            attrs["key"] = attrs.get("name", getattr(self.instance, "key", "")).strip()
        include_in_sku = attrs.get("include_in_sku", getattr(self.instance, "include_in_sku", False))
        include_in_sales_model = attrs.get("include_in_sales_model", getattr(self.instance, "include_in_sales_model", False))
        required = attrs.get("required", getattr(self.instance, "required", False))
        if required and not (include_in_sku or include_in_sales_model):
            raise serializers.ValidationError({"required": "开启“必填”需要先开启“生成中文SKU”或“生成销售型号”。"})
        structural_fields = {
            "include_in_sku", "include_in_sales_model", "uppercase", "required", "unit", "default_value",
        }
        is_structural_change = (
            any(field in attrs and attrs[field] != getattr(self.instance, field) for field in structural_fields)
            if self.instance else any(bool(attrs.get(field)) for field in ("include_in_sku", "include_in_sales_model", "required"))
        )
        if is_structural_change:
            category = attrs.get("category", getattr(self.instance, "category", None))
            unsafe_products = unfrozen_products_using_category_scope(category)
            if unsafe_products:
                raise serializers.ValidationError(unfrozen_schema_error(unsafe_products))
        return attrs


class ProductCategorySerializer(serializers.ModelSerializer):
    product_count = serializers.IntegerField(read_only=True, default=0)
    child_count = serializers.IntegerField(read_only=True, default=0)
    parent_name = serializers.CharField(source="parent.name", read_only=True, default="")
    attributes = CategoryAttributeSerializer(many=True, read_only=True)
    effective_attributes = serializers.SerializerMethodField()
    sku_name_preview = serializers.SerializerMethodField()

    class Meta:
        model = ProductCategory
        fields = "__all__"

    def validate(self, attrs):
        if self.instance and "parent" in attrs and attrs["parent"] != self.instance.parent:
            unsafe_products = unfrozen_products_using_category_scope(self.instance)
            if unsafe_products:
                raise serializers.ValidationError(unfrozen_schema_error(
                    unsafe_products,
                    UNFROZEN_CATEGORY_HIERARCHY_MESSAGE,
                ))
        parent = attrs.get("parent", self.instance.parent if self.instance else None)
        cursor = parent
        while cursor:
            if self.instance and cursor.pk == self.instance.pk:
                raise serializers.ValidationError({"parent": "上级分类不能是当前分类或其子分类。"})
            cursor = cursor.parent
        return attrs

    def get_effective_attributes(self, obj):
        lineage, current = [], obj
        while current:
            lineage.append(current)
            current = current.parent
        merged = {}
        for category in reversed(lineage):
            for attribute in category.attributes.all():
                row = CategoryAttributeSerializer(attribute).data
                row.update({"inherited": category.pk != obj.pk, "source_category": category.name})
                merged[attribute.key.lower()] = row
        return list(merged.values())

    def get_sku_name_preview(self, obj):
        parts = []
        for row in self.get_effective_attributes(obj):
            if row["include_in_sku"]:
                value = row["default_value"] or f"[{row['name']}]"
                value = value.upper() if row["uppercase"] and row["default_value"] else value
                parts.append(value)
        return "-".join(parts)


class ProductSerializer(serializers.ModelS…8158 tokens truncated…  validate_document_amount(attrs, source)
        validate_sales_exchange_rate(attrs, source)
        quote_date = attrs.get("quote_date", source.quote_date if source else None)
        valid_until = attrs.get("valid_until", source.valid_until if source else None)
        if quote_date and valid_until and valid_until < quote_date:
            raise serializers.ValidationError({"valid_until": "有效期不能早于报价日期。"})
        return attrs

    def get_root_quote_no(self, obj):
        return obj.root_quote.quote_no if obj.root_quote_id else obj.quote_no

    def get_revision_label(self, obj):
        return f"Revision {obj.revision_no}" if obj.revision_no else "Original"

    def get_parent_quote_no(self, obj):
        return obj.parent_quote.quote_no if obj.parent_quote_id else ""

    @transaction.atomic
    def create(self, validated_data):
        validated_data["status"] = "draft"
        validated_data.setdefault("deposit_ratio", Decimal("0.30"))
        items = validated_data.pop("items", [])
        customer = validated_data["customer"]
        primary_contact = customer.contacts.order_by("-is_primary", "name").first()
        snapshots = {
            "recipient_name": primary_contact.name if primary_contact else customer.name,
            "buyer_address": customer.address,
            "buyer_email": primary_contact.email if primary_contact else "",
            "buyer_phone": primary_contact.phone if primary_contact else "",
        }
        for field, value in snapshots.items():
            if not validated_data.get(field):
                validated_data[field] = value
        try:
            validated_data["quote_no"] = allocate_root_quote_no(validated_data["quote_date"], customer.country)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(getattr(exc, "message_dict", exc.messages)) from exc
        quote = Quote.objects.create(**validated_data)
        create_quote_items(quote, items)
        return quote

    def update(self, instance, validated_data):
        raise serializers.ValidationError("已保存报价请创建迭代版本")


class OrderItemSerializer(TradeLineSerializerMixin, serializers.ModelSerializer):
    sku_code = serializers.CharField(source="sku_code_snapshot", read_only=True)
    sales_model = serializers.CharField(source="sales_model_snapshot", read_only=True)
    model = serializers.CharField(source="sales_model_snapshot", read_only=True)
    product_name = serializers.CharField(source="display_name_snapshot", read_only=True)
    display_name = serializers.CharField(source="display_name_snapshot", read_only=True)
    description = serializers.CharField(source="description_snapshot", read_only=True)
    unit = serializers.CharField(source="unit_snapshot", read_only=True)
    amount = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    supplier_sku = serializers.PrimaryKeyRelatedField(read_only=True)
    supplier_name = serializers.CharField(source="supplier_name_snapshot", read_only=True)
    supplier_model = serializers.CharField(source="supplier_model_snapshot", read_only=True)
    supplier_sku_code = serializers.CharField(source="supplier_sku_code_snapshot", read_only=True)
    supplier_barcode = serializers.CharField(source="supplier_barcode_snapshot", read_only=True)
    supplier_allocation = serializers.SerializerMethodField()

    def get_supplier_allocation(self, obj):
        from .services.supplier_allocation import supplier_allocation_payload
        return supplier_allocation_payload(obj) if obj.supplier_sku_id else None

    class Meta:
        model = OrderItem
        fields = ["id", "sku", "sku_code", "sales_model", "model", "product_name", "display_name", "description", "unit", "quantity", "unit_price", "cost_price", "amount", "notes", "supplier_sku", "supplier_name", "supplier_model", "supplier_sku_code", "supplier_barcode", "supplier_allocation"] + TRADE_FIELDS


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    customer_country = serializers.CharField(source="customer.country", read_only=True, default="")
    quote_no = serializers.CharField(source="quote.quote_no", read_only=True, default="")
    source_quote_no = serializers.CharField(source="quote.quote_no", read_only=True, default="")
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    total_amount = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    base_amount = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    approved_change_amount = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    paid_amount = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    balance_amount = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = "__all__"
        read_only_fields = ["order_no", "status", "cancelled_at", "cancellation_reason"]

    def get_balance_amount(self, obj):
        return obj.outstanding_amount.quantize(Decimal("0.01"))

    def validate(self, attrs):
        if "order_no" in self.initial_data:
            raise serializers.ValidationError({"order_no": "订单号由系统自动生成，不能手工指定。"})
        validate_contract_edit(self.instance, attrs)
        validate_sales_exchange_rate(attrs, self.instance)
        if self.instance is None and not attrs.get("items"):
            raise serializers.ValidationError({"items": "订单至少需要一条商品明细。"})
        for item in attrs.get("items", []):
            if not item["sku"].active and (self.instance is None or not self.instance.items.filter(sku=item["sku"]).exists()):
                raise serializers.ValidationError({"items": "新订单行不能选择停用或已归档的 SKU。"})
        source_quote = attrs.get("quote", getattr(self.instance, "quote", None))
        customer = attrs.get("customer", getattr(self.instance, "customer", None))
        from .sales_scope import customer_in_scope
        request = self.context.get("request")
        if request and customer and not customer_in_scope(customer.pk, request.user):
            raise PermissionDenied("所选客户不在当前账号的数据范围内。")
        if request and source_quote and not customer_in_scope(source_quote.customer_id, request.user):
            raise PermissionDenied("来源报价不在当前账号的数据范围内。")
        if source_quote and customer and source_quote.customer_id != customer.id:
            raise serializers.ValidationError({"customer": "从报价创建订单时，客户必须与来源报价一致。"})
        # A terminal quote is historical context only.  It cannot seed a new
        # order or replace the source quote of an existing draft order.
        quote_is_being_bound = self.instance is None or "quote" in attrs
        if quote_is_being_bound and source_quote and source_quote.status in {"rejected", "expired"}:
            raise serializers.ValidationError({"quote": "该报价已拒绝或过期，请先创建新的修订版后再转为订单。"})
        return attrs

    @staticmethod
    def _item_signature(items):
        return [
            (item["sku"].pk, Decimal(item["quantity"]), Decimal(item["unit_price"]), item.get("notes", ""), item.get("trade_unit").pk if item.get("trade_unit") else None, item.get("trade_quantity"), item.get("trade_unit_price"))
            for item in items
        ]

    @staticmethod
    def _order_item_signature(items):
        return [
            (
                item["sku"].pk,
                Decimal(item["quantity"]),
                Decimal(item["unit_price"]),
                Decimal(item.get("cost_price", 0)),
                item.get("notes", ""),
                item.get("trade_unit").pk if item.get("trade_unit") else None,
                item.get("trade_quantity"),
                item.get("trade_unit_price"),
            )
            for item in items
        ]

    @staticmethod
    def _persisted_order_item_signature(items):
        return [
            (
                item.sku_id,
                Decimal(item.quantity),
                Decimal(item.unit_price),
                Decimal(item.cost_price),
                item.notes,
                item.trade_unit_id,
                item.trade_quantity,
                item.trade_unit_price,
            )
            for item in items
        ]

    @staticmethod
    def _item_snapshots(sku, source=None):
        if source is not None:
            return {
                "sku_code_snapshot": source.sku_code_snapshot,
                "sales_model_snapshot": source.sales_model_snapshot,
                "display_name_snapshot": getattr(source, "product_name_snapshot", getattr(source, "display_name_snapshot", "")),
                "description_snapshot": getattr(source, "description", getattr(source, "description_snapshot", "")),
                "unit_snapshot": source.unit_snapshot,
            }
        return {
            "sku_code_snapshot": sku.sku,
            "sales_model_snapshot": sku.sales_model or "",
            "display_name_snapshot": sku.display_name_cn or sku.product.name,
            "description_snapshot": sku.description_en or sku.description_cn or sku.display_name_cn or sku.product.name,
            "unit_snapshot": sku.unit,
        }

    @staticmethod
    def _supplier_snapshots(source=None):
        if source is None or not source.supplier_sku_id:
            return {}
        return {
            "supplier_sku": source.supplier_sku,
            "supplier_name_snapshot": source.supplier_name_snapshot,
            "supplier_model_snapshot": source.supplier_model_snapshot,
            "supplier_sku_code_snapshot": source.supplier_sku_code_snapshot,
            "supplier_barcode_snapshot": source.supplier_barcode_snapshot,
            "supplier_characteristics_snapshot": source.supplier_characteristics_snapshot,
            "supplier_price_snapshot": source.supplier_price_snapshot,
            "supplier_currency_snapshot": source.supplier_currency_snapshot,
            "supplier_moq_snapshot": source.supplier_moq_snapshot,
            "supplier_lead_time_days_snapshot": source.supplier_lead_time_days_snapshot,
            "supplier_allocation_source": source.supplier_allocation_source,
            "supplier_allocation_sources_snapshot": source.supplier_allocation_sources_snapshot,
            "supplier_allocation_scope": source.supplier_allocation_scope,
            "supplier_allocation_note": source.supplier_allocation_note,
            "supplier_allocated_at": source.supplier_allocated_at,
        }

    def _create_quote_revision_if_needed(self, source_quote, order_data, order_items):
        source_items = list(source_quote.items.order_by("id"))
        changed_parts = []
        if self._item_signature(order_items) != [
            (item.sku_id, item.quantity, item.unit_price, item.notes, item.trade_unit_id, item.trade_quantity, item.trade_unit_price)
            for item in source_items
        ]:
            changed_parts.append("产品明细")

        for field, label in [
            ("currency", "币种"),
            ("exchange_rate", "汇率"),
            ("shipping_fee", "运费"),
            ("discount", "折扣"),
            ("notes", "条款/备注"),
        ]:
            if order_data.get(field, getattr(source_quote, field)) != getattr(source_quote, field):
                changed_parts.append(label)

        if not changed_parts:
            return source_quote

        root_quote = source_quote.root_quote or source_quote
        try:
            quote_no, revision_no = allocate_revision_quote_no(source_quote)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(getattr(exc, "message_dict", exc.messages)) from exc

        copied_fields = [
            "customer", "quote_date", "valid_until", "currency", "exchange_rate", "shipping_fee", "discount",
            "notes", "recipient_name", "buyer_address", "buyer_email", "buyer_phone", "lead_time_days",
            "deposit_ratio", "trading_terms", "shipping_details", "buyer_company_name",
        ]
        revision_values = {field: getattr(source_quote, field) for field in copied_fields}
        revision_values.update({
            field: order_data[field]
            for field in ("currency", "exchange_rate", "shipping_fee", "discount", "notes")
            if field in order_data
        })
        revision = Quote.objects.create(
            quote_no=quote_no,
            root_quote=root_quote,
            parent_quote=source_quote,
            revision_no=revision_no,
            revision_summary=f"订单确认时调整：{'、'.join(changed_parts)}",
            status="accepted",
            **revision_values,
        )
        create_quote_items(
            revision,
            [
                {
                    "sku": item["sku"],
                    "quantity": item["quantity"],
                    "unit_price": item["unit_price"],
                    "notes": item.get("notes", ""),
                    "description": source_items[index].description if index < len(source_items) else "",
                    **{key: item[key] for key in TRADE_FIELDS if key in item},
                }
                for index, item in enumerate(order_items)
            ],
            source_items=source_items,
        )
        return revision

    @staticmethod
    def _existing_order_items_for_quote_revision(order):
        """Use the persisted order lines when a partial edit changes only header terms."""
        return [
            {
                "sku": item.sku,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "notes": item.notes,
                **trade_values(item),
            }
            for item in order.items.select_related("sku").order_by("id")
        ]

    @transaction.atomic
    def create(self, validated_data):
        items = validated_data.pop("items", [])
        # Draft creation deliberately has no lifecycle side effects.  Quote
        # acceptance/revision, reservations and payment plans occur only in
        # order_lifecycle.confirm_order().
        validated_data.pop("status", None)
        validated_data.pop("order_no", None)
        order = Order.objects.create(order_no=allocate_order_no(), **validated_data)
        source_items = list(order.quote.items.order_by("id")) if order.quote_id else []
        rows = []
        for index, item in enumerate(items):
            if not item.get("cost_price"):
                item["cost_price"] = item["sku"].cost_price
            source = source_items[index] if index < len(source_items) and source_items[index].sku_id == item["sku"].pk else None
            rows.append(OrderItem(order=order, **item, **self._item_snapshots(item["sku"], source)))
        OrderItem.objects.bulk_create(rows)
        return order

    @transaction.atomic
    def update(self, instance, validated_data):
        instance = Order.objects.select_for_update().get(pk=instance.pk)
        validate_contract_edit(instance, validated_data)
        items = validated_data.pop("items", None)
        previous_items = list(instance.items.order_by("id"))
        items_changed = items is not None and self._order_item_signature(items) != self._persisted_order_item_signature(previous_items)
        # A draft may change freely.  For a formal order, retain the existing
        # contract-edit validation but never create a quote revision from PATCH;
        # revisions are created atomically by the confirm action only.
        for key, value in validated_data.items():
            setattr(instance, key, value)
        instance.save()
        if items_changed:
            instance.items.all().delete()
            rows = []
            for index, item in enumerate(items):
                if not item.get("cost_price"):
                    item["cost_price"] = item["sku"].cost_price
                source = previous_items[index] if index < len(previous_items) and previous_items[index].sku_id == item["sku"].pk else None
                rows.append(OrderItem(order=instance, **item, **self._item_snapshots(item["sku"], source), **self._supplier_snapshots(source)))
            OrderItem.objects.bulk_create(rows)
        return instance


class TransactionSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source="supplier.name", read_only=True, default="")
    purchase_no = serializers.CharField(source="purchase_order.purchase_no", read_only=True, default="")
    allocations = serializers.SerializerMethodField()
    customer_name = serializers.CharField(source="customer.name", read_only=True, default="")
    order_no = serializers.CharField(source="order.order_no", read_only=True, default="")
    direction_display = serializers.CharField(source="get_direction_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    rmb_amount = serializers.SerializerMethodField()

    class Meta:
        model = Transaction
        fields = "__all__"
        extra_kwargs = {"transaction_no": {"required": False}}
        read_only_fields = ["status", "allocated_amount", "split_from", "voided_at", "void_reason"]

    def get_allocations(self, obj):
        allocations = getattr(obj, "_prefetched_objects_cache", {}).get("allocations")
        if allocations is None:
            allocations = obj.allocations.select_related("plan__order", "plan__purchase_order")
        return [{
            "id": row.id,
            "plan": row.plan_id,
            "contract_no": row.plan.order.order_no if row.plan.order_id else row.plan.purchase_order.purchase_no,
            "order": row.plan.order_id,
            "purchase_order": row.plan.purchase_order_id,
            "amount": row.amount,
            "is_active": row.is_active,
        } for row in allocations]

    def get_rmb_amount(self, obj):
        return obj.rmb_amount or (obj.amount * obj.exchange_rate).quantize(Decimal("0.0001"))

    def validate(self, attrs):
        for field in ("amount", "exchange_rate"):
            value = attrs.get(field, getattr(self.instance, field, Decimal("1")))
            if value <= 0:
                raise serializers.ValidationError({field: "必须大于零。"})
        kind = attrs.get("kind", getattr(self.instance, "kind", "other"))
        direction = attrs.get("direction", getattr(self.instance, "direction", None))
        income_kinds = {"customer_receipt", "supplier_refund", "other_income"}
        either_kinds = {"other", "unallocated_advance", "exchange_difference"}
        if kind not in either_kinds and direction != ("income" if kind in income_kinds else "expense"):
            raise serializers.ValidationError("业务类型与收支方向不一致。")
        order = attrs.get("order", getattr(self.instance, "order", None))
        customer = attrs.get("customer", getattr(self.instance, "customer", None))
        purchase_order = attrs.get("purchase_order", getattr(self.instance, "purchase_order", None))
        supplier = attrs.get("supplier", getattr(self.instance, "supplier", None))
        if order and customer and order.customer_id != customer.id:
            raise serializers.ValidationError("流水选择的客户必须与订单客户一致。")
        if order and not customer:
            attrs["customer"] = order.customer
        if purchase_order and supplier and purchase_order.supplier_id != supplier.id:
            raise serializers.ValidationError("流水选择的供应商必须与采购单供应商一致。")
        if purchase_order and not supplier:
            attrs["supplier"] = purchase_order.supplier
        if order and purchase_order:
            raise serializers.ValidationError("一笔流水只能关联销售订单或采购单之一。")
        if kind in {"unallocated_advance", "unallocated_payment"}:
            if order or purchase_order or attrs.get("plan"):
                raise serializers.ValidationError("未分配预收预付请只选择往来方，之后再核销计划。")
            if not (customer if direction == "income" else supplier):
                raise serializers.ValidationError("预收款请选择客户，预付款请选择供应商。")
        contract = order or purchase_order
        if contract and kind in {"customer_receipt", "supplier_payment", "refund", "supplier_refund"} and attrs.get("currency", "USD") != contract.currency:
            raise serializers.ValidationError("合同收付款及退款币种必须与合同一致。")
        return attrs


class PaymentPlanSerializer(serializers.ModelSerializer):
    customer_id = serializers.IntegerField(source="order.customer_id", read_only=True, default=None)
    supplier_id = serializers.IntegerField(source="purchase_order.supplier_id", read_only=True, default=None)
    exchange_rate = serializers.SerializerMethodField()
    remaining_rmb = serializers.SerializerMethodField()
    remaining_amount = serializers.DecimalField(max_digits=14, decimal_places=4, read_only=True)
    contract_no = serializers.SerializerMethodField()
    counterparty_name = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()

    class Meta:
        model = PaymentPlan
        fields = "__all__"
        read_only_fields = ["settled_amount", "status"]

    def get_exchange_rate(self, obj):
        return (obj.order or obj.purchase_order).exchange_rate

    def get_remaining_rmb(self, obj):
        return obj.remaining_amount * self.get_exchange_rate(obj)

    @transaction.atomic
    def update(self, instance, validated_data):
        self.instance = PaymentPlan.objects.select_for_update().get(pk=instance.pk)
        self.validate(validated_data)
        return super().update(self.instance, validated_data)

    def validate(self, attrs):
        values = {field: attrs.get(field, getattr(self.instance, field, None)) for field in ("order", "purchase_order", "direction", "currency", "planned_amount")}
        order, purchase = values["order"], values["purchase_order"]
        if bool(order) == bool(purchase):
            raise serializers.ValidationError("计划必须且只能关联一个合同。")
        contract = order or purchase
        if values["direction"] != ("receivable" if order else "payable") or values["currency"] != contract.currency:
            raise serializers.ValidationError("计划方向和币种必须与合同一致。")
        if not values["planned_amount"] or values["planned_amount"] <= 0:
            raise serializers.ValidationError("计划金额必须大于零。")
        if contract.status in {"draft", "cancelled"}:
            raise serializers.ValidationError("草稿或已取消合同不能设置收付款计划。")
        others = contract.payment_plans.exclude(status="cancelled")
        if self.instance:
            others = others.exclude(pk=self.instance.pk)
        planned = sum(others.values_list("planned_amount", flat=True), Decimal("0"))
        if planned + values["planned_amount"] > contract.total_amount:
            raise serializers.ValidationError("计划合计不能超过当前合同金额。调整分期比例时，请先调低原计划再调高另一笔。")
        if self.instance and (self.instance.settled_amount or self.instance.transactions.exists() or self.instance.advance_allocations.exists()):
            if any(key in attrs for key in ("order", "purchase_order", "direction", "currency", "planned_amount")):
                raise serializers.ValidationError("已有收付款记录的计划只能修改预计日期和备注。")
        return attrs

    def get_contract_no(self, obj):
        return obj.order.order_no if obj.order_id else obj.purchase_order.purchase_no

    def get_counterparty_name(self, obj):
        return obj.order.customer.name if obj.order_id else obj.purchase_order.supplier.name

    def get_is_overdue(self, obj):
        from django.utils import timezone
        return bool(obj.due_date and obj.due_date < timezone.localdate() and obj.status == "open")


class ContractChangeRequestSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = ContractChangeRequest
        fields = "__all__"
        read_only_fields = ["status"]

    def validate(self, attrs):
        if self.instance and self.instance.status != "pending":
            raise serializers.ValidationError("已处理的合同变更不能修改。")
        order = attrs.get("order", getattr(self.instance, "order", None))
        purchase = attrs.get("purchase_order", getattr(self.instance, "purchase_order", None))
        from .sales_scope import customer_in_scope
        request = self.context.get("request")
        if request and order and not customer_in_scope(order.customer_id, request.user):
            raise PermissionDenied("所选订单不在当前账号的数据范围内。")
        amount = attrs.get("amount_delta", getattr(self.instance, "amount_delta", Decimal("0")))
        if bool(order) == bool(purchase) or amount == 0:
            raise serializers.ValidationError("变更必须关联一个合同，且金额不能为零。")
        return attrs


class PackagingTemplateSerializer(serializers.ModelSerializer):
    cbm = serializers.DecimalField(max_digits=16, decimal_places=6, read_only=True)
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)
    linked_sku_count = serializers.IntegerField(source="sku_profiles.count", read_only=True)

    class Meta:
        model = PackagingTemplate
        fields = "__all__"
        read_only_fields = ["code"]

    def validate(self, attrs):
        checks = {
            "carton_length": ("箱长必须大于 0。", lambda value: value > 0),
            "carton_width": ("箱宽必须大于 0。", lambda value: value > 0),
            "carton_height": ("箱高必须大于 0。", lambda value: value > 0),
            "qty_per_carton": ("每箱数量必须大于 0。", lambda value: value > 0),
            "carton_tare_weight": ("纸箱皮重不能为负。", lambda value: value >= 0),
        }
        for field, (message, valid) in checks.items():
            value = attrs.get(field)
            if value is not None and not valid(value):
                raise serializers.ValidationError({field: message})
        return attrs

    def update(self, instance, validated_data):
        physical_fields = {
            "carton_length", "carton_width", "carton_height", "qty_per_carton",
            "carton_tare_weight", "partial_carton_policy",
        }
        with transaction.atomic():
            template = PackagingTemplate.objects.select_for_update().get(pk=instance.pk)
            physical_changed = any(
                field in validated_data and validated_data[field] != getattr(template, field)
                for field in physical_fields
            )
            for field, value in validated_data.items():
                setattr(template, field, value)
            template.save()
            if physical_changed:
                profiles = list(
                    SKUPackagingProfile.objects.select_for_update().filter(
                        packaging_template=template,
                        verified_at__isnull=False,
                    )
                )
                for profile in profiles:
                    profile.verified_at = None
                    profile.verified_by = None
                    profile.save(update_fields=["verified_at", "verified_by", "updated_at"])
        return template


class SKUPackagingProfileSerializer(serializers.ModelSerializer):
    sku_code = serializers.CharField(source="sku.sku", read_only=True)
    product_name = serializers.CharField(source="sku.product.name", read_only=True)
    packaging_status = serializers.SerializerMethodField()
    effective_packaging = serializers.SerializerMethodField()

    class Meta:
        model = SKUPackagingProfile
        fields = "__all__"
        read_only_fields = ["verified_at", "verified_by"]

    def validate(self, attrs):
        if self.instance and "sku" in attrs and attrs["sku"].pk != self.instance.sku_id:
            raise serializers.ValidationError({"sku": "SKU 包装配置创建后不能更换 SKU。"})

        template = attrs.get("packaging_template", getattr(self.instance, "packaging_template", None))
        current_template_id = getattr(self.instance, "packaging_template_id", None)
        if template and not template.active and (self.instance is None or template.pk != current_template_id):
            raise serializers.ValidationError({"packaging_template": "停用包装模板不能用于新的 SKU 包装配置。"})

        checks = {
            "qty_per_carton_override": ("每箱数量必须大于 0。", lambda value: value > 0),
            "carton_length_override": ("箱长必须大于 0。", lambda value: value > 0),
            "carton_width_override": ("箱宽必须大于 0。", lambda value: value > 0),
            "carton_height_override": ("箱高必须大于 0。", lambda value: value > 0),
            "unit_net_weight": ("单件净重不能为负。", lambda value: value >= 0),
            "carton_tare_weight_override": ("纸箱皮重不能为负。", lambda value: value >= 0),
            "gross_weight_override": ("整箱预计毛重不能为负。", lambda value: value >= 0),
        }
        for field, (message, valid) in checks.items():
            value = attrs.get(field)
            if value is not None and not valid(value):
                raise serializers.ValidationError({field: message})
        return attrs

    def update(self, instance, validated_data):
        effective_fields = {
            "packaging_template", "unit_net_weight", "qty_per_carton_override",
            "carton_length_override", "carton_width_override", "carton_height_override",
            "carton_tare_weight_override", "gross_weight_override",
        }
        effective_changed = any(
            field in validated_data and validated_data[field] != getattr(instance, field)
            for field in effective_fields
        )
        if effective_changed:
            validated_data["verified_at"] = None
            validated_data["verified_by"] = None
        return super().update(instance, validated_data)

    def get_packaging_status(self, obj):
        from .services.packaging import resolve_packaging
        return resolve_packaging(obj.sku).status

    def get_effective_packaging(self, obj):
        from .services.packaging import packaging_summary
        return packaging_summary(obj.sku)


class PackingPlanCartonItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PackingPlanCartonItem
        fields = "__all__"


class PackingPlanCartonSerializer(serializers.ModelSerializer):
    items = PackingPlanCartonItemSerializer(many=True, read_only=True)
    class Meta:
        model = PackingPlanCarton
        fields = "__all__"


class PackingPlanSerializer(serializers.ModelSerializer):
    cartons = PackingPlanCartonSerializer(many=True, read_only=True)
    class Meta:
        model = PackingPlan
        fields = "__all__"
        read_only_fields = ["quote", "order", "total_cartons", "total_net_weight", "total_gross_weight", "total_cbm", "warnings", "status"]


class ShipmentPackageItemSerializer(serializers.ModelSerializer):
    sku_code = serializers.CharField(source="sku.sku", read_only=True)
    class Meta:
        model = ShipmentPackageItem
        fields = ["id", "sku", "sku_code", "quantity"]


class ShipmentPackageSerializer(serializers.ModelSerializer):
    items = ShipmentPackageItemSerializer(many=True)
    actual_cbm = serializers.DecimalField(max_digits=16, decimal_places=6, read_only=True)
    class Meta:
        model = ShipmentPackage
        fields = ["id", "shipment", "carton_no", "packaging_template", "length", "width", "height", "actual_net_weight", "actual_gross_weight", "actual_cbm", "notes", "items"]
        read_only_fields = ["shipment"]

    def validate(self, attrs):
        shipment = self.context.get("shipment") or (self.instance.shipment if self.instance else attrs.get("shipment"))
        ZERO = Decimal("0")
        if shipment is None:
            raise serializers.ValidationError("实际箱单必须属于发货单。")
        if shipment.status != "confirmed":
            raise serializers.ValidationError("只有已确认的发货单可以修改实际箱单。")
        def value(name, default=None):
            return attrs.get(name, getattr(self.instance, name, default))
        carton_no = value("carton_no")
        if carton_no is None or carton_no <= 0:
            raise serializers.ValidationError({"carton_no": "箱号必须大于零。"})
        other_packages = shipment.packages.all()
        if self.instance:
            other_packages = other_packages.exclude(pk=self.instance.pk)
        if other_packages.filter(carton_no=carton_no).exists():
            raise serializers.ValidationError({"carton_no": "该发货单已存在此箱号，请使用其他箱号。"})
        dimensions = [value(name) for name in ("length", "width", "height")]
        if any(d is not None for d in dimensions) and not all(d is not None and d > 0 for d in dimensions):
            raise serializers.ValidationError("箱长、宽、高须同时填写且大于零，或全部留空。")
        net, gross = value("actual_net_weight", ZERO), value("actual_gross_weight", ZERO)
        if net < 0 or gross < 0 or gross < net:
            raise serializers.ValidationError("净重、毛重不得为负，且毛重不得低于净重。")
        items = attrs.get("items")
        if items is None and self.instance:
            items = [{"sku": item.sku, "quantity": item.quantity} for item in self.instance.items.all()]
        if not items:
            raise serializers.ValidationError({"items": "请填写至少一条箱内 SKU 明细。"})
        shipped = {}
        for item in shipment.items.all():
            shipped[item.sku_id] = shipped.get(item.sku_id, ZERO) + item.quantity
        packed = {}
        for item in ShipmentPackageItem.objects.filter(shipment_package__in=other_packages):
            packed[item.sku_id] = packed.get(item.sku_id, ZERO) + item.quantity
        seen = set()
        for item in items:
            sku_id, quantity = item["sku"].pk, item["quantity"]
            if quantity <= 0:
                raise serializers.ValidationError({"items": "实际装箱数量必须大于零。"})
            if sku_id not in shipped:
                raise serializers.ValidationError({"items": "箱内 SKU 必须属于本次发货。"})
            if sku_id in seen:
                raise serializers.ValidationError({"items": "同一箱内不能重复填写同一 SKU。"})
            seen.add(sku_id)
            if packed.get(sku_id, ZERO) + quantity > shipped[sku_id]:
                raise serializers.ValidationError({"items": f"SKU {item['sku'].sku} 累计装箱数量不能超过本次发货数量 {shipped[sku_id]}。"})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        self.context["shipment"] = Shipment.objects.select_for_update().get(pk=validated_data["shipment"].pk)
        self.validate(validated_data)
        items = validated_data.pop("items", [])
        package = ShipmentPackage.objects.create(**validated_data)
        ShipmentPackageItem.objects.bulk_create([ShipmentPackageItem(shipment_package=package, **item) for item in items])
        return package

    @transaction.atomic
    def update(self, instance, validated_data):
        self.context["shipment"] = Shipment.objects.select_for_update().get(pk=instance.shipment_id)
        self.validate(validated_data)
        items = validated_data.pop("items", None)
        for key, value in validated_data.items(): setattr(instance, key, value)
        instance.save()
        if items is not None:
            instance.items.all().delete()
            ShipmentPackageItem.objects.bulk_create([ShipmentPackageItem(shipment_package=instance, **item) for item in items])
        return instance

class InventoryMovementSerializer(TradeLineSerializerMixin, serializers.ModelSerializer):
    movement_no = serializers.CharField(read_only=True)
    related_orders = serializers.PrimaryKeyRelatedField(many=True, queryset=Order.objects.all(), required=False)
    related_order_nos = serializers.SerializerMethodField()
    sku_code = serializers.CharField(source="sku.sku", read_only=True)
    display_name = serializers.CharField(source="sku.display_name_cn", read_only=True)
    sales_model = serializers.CharField(source="sku.sales_model", read_only=True)
    product_name = serializers.CharField(source="sku.display_name_cn", read_only=True)
    order_no = serializers.CharField(source="order.order_no", read_only=True, default="")
    type_display = serializers.CharField(source="get_type_display", read_only=True)
    signed_quantity = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    overage_quantity = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    overage_summary = serializers.SerializerMethodField()
    reversal_movement = serializers.SerializerMethodField()
    is_reversed = serializers.SerializerMethodField()
    reversal_status = serializers.SerializerMethodField()

    def get_overage_summary(self, obj):
        if not obj.is_overage or obj.overage_quantity <= 0:
            return ""
        return f"超到 {obj.overage_quantity}（{obj.get_overage_reason_display()}）"

    def _reversal_movement(self, obj):
        if not hasattr(obj, "_reversal_movement_cache"):
            obj._reversal_movement_cache = InventoryMovement.objects.filter(
                source_type="reversal", source_no=obj.movement_no
            ).order_by("id").first()
            if obj._reversal_movement_cache is None:
                receipt = GoodsReceipt.objects.filter(inventory_movement=obj).select_related("reversal_inventory_movement").first()
                if receipt and receipt.reversal_inventory_movement_id:
                    obj._reversal_movement_cache = receipt.reversal_inventory_movement
                else:
                    shipment_item = ShipmentItem.objects.filter(inventory_movement=obj).select_related("reversal_inventory_movement").first()
                    if shipment_item and shipment_item.reversal_inventory_movement_id:
                        obj._reversal_movement_cache = shipment_item.reversal_inventory_movement
        return obj._reversal_movement_cache

    def get_reversal_movement(self, obj):
        reversal = self._reversal_movement(obj)
        if not reversal:
            return None
        return {
            "id": reversal.id,
            "movement_no": reversal.movement_no,
            "movement_date": reversal.movement_date,
            "reason": reversal.notes,
        }

    def get_is_reversed(self, obj):
        return self._reversal_movement(obj) is not None

    def get_reversal_status(self, obj):
        if obj.source_type == "reversal":
            return "冲销流水"
        reversal = self._reversal_movement(obj)
        return f"已冲销 · {reversal.movement_no}" if reversal else ""

    class Meta:
        model = InventoryMovement
        fields = "__all__"
        read_only_fields = ["source_type", "source_no", "is_automatic", "sku_code_snapshot", "sales_model_snapshot", "display_name_snapshot", "is_overage", "overage_reason"]

    def validate(self, attrs):
        from .services.fulfillment import OUTGOING_MOVEMENT_TYPES
        quantity = attrs.get("quantity", getattr(self.instance, "quantity", Decimal("0")))
        if quantity <= 0 or attrs.get("unit_cost", Decimal("0")) < 0:
            raise serializers.ValidationError("数量必须大于零，单位成本不能为负。")
        movement_type = attrs.get("type", getattr(self.instance, "type", ""))
        if movement_type in {"purchase_in", "sale_out"}:
            raise serializers.ValidationError("采购入库和销售出库请从采购到货、订单发货登记，确保业务同步。")
        if self.instance and any(key in attrs and attrs[key] != getattr(self.instance, key) for key in ("sku", "type")):
            raise serializers.ValidationError("库存流水不能更换 SKU 或出入库类型，请使用调整流水纠正。")
        related_orders = attrs.get("related_orders", None)
        order = attrs.get("order", getattr(self.instance, "order", None))
        sku = attrs.get("sku", getattr(self.instance, "sku", None))
        supplier_sku = attrs.get("supplier_sku", getattr(self.instance, "supplier_sku", None))
        orders = list(related_orders) if related_orders is not None else ([order] if order else [])
        if related_orders is not None:
            attrs["order"] = orders[0] if orders else None
        if sku and orders and not any(related_order.items.filter(sku=sku).exists() for related_order in orders):
            raise serializers.ValidationError("选择的 SKU 不在任一关联订单明细中。")
        if supplier_sku and sku and supplier_sku.sku_id != sku.pk:
            raise serializers.ValidationError("供应商来源必须对应当前库存流水 SKU。")
        return attrs

    def get_related_order_nos(self, instance):
        order_nos = list(instance.related_orders.values_list("order_no", flat=True))
        return order_nos or ([instance.order.order_no] if instance.order_id else [])

    def check_stock(self, sku, delta):
        from .services.fulfillment import sku_metrics
        SKU.objects.select_for_update().get(pk=sku.pk)
        if delta < 0 and sku_metrics(sku)["available_quantity"] + delta < 0:
            raise serializers.ValidationError("可用库存不足，不能扣减或占用订单已预留的库存。")

    @transaction.atomic
    def create(self, validated_data):
        from .services.fulfillment import OUTGOING_MOVEMENT_TYPES
        delta = validated_data["quantity"] * (-1 if validated_data["type"] in OUTGOING_MOVEMENT_TYPES else 1)
        self.check_stock(validated_data["sku"], delta)
        related_orders = validated_data.pop("related_orders", [])
        if related_orders:
            validated_data["order"] = related_orders[0]
        validated_data.setdefault("movement_no", f"IM-{uuid4().hex[:16].upper()}")
        instance = super().create(validated_data)
        if related_orders:
            instance.related_orders.set(related_orders)
        elif instance.order_id:
            instance.related_orders.set([instance.order_id])
        from .services.fulfillment import rebalance_sku_reservations
        rebalance_sku_reservations(instance.sku)
        return instance

    @transaction.atomic
    def update(self, instance, validated_data):
        instance = InventoryMovement.objects.select_for_update().get(pk=instance.pk)
        quantity = validated_data.get("quantity", instance.quantity)
        sign = -1 if instance.signed_quantity < 0 else 1
        self.check_stock(instance.sku, (quantity - instance.quantity) * sign)
        related_orders = validated_data.pop("related_orders", None)
        if related_orders is not None:
            validated_data["order"] = related_orders[0] if related_orders else None
        instance = super().update(instance, validated_data)
        if related_orders is not None:
            instance.related_orders.set(related_orders)
        from .services.fulfillment import rebalance_sku_reservations
        rebalance_sku_reservations(instance.sku)
        return instance

