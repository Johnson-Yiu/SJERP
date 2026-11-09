from .permissions import user_can
from .finance_scope import validate_finance_relations
from .trade_units import TradeLineSerializerMixin, TRADE_FIELDS, SKUTradeUnitSerializer, trade_values, validate_document_amount
from decimal import Decimal, ROUND_HALF_UP
import re
from uuid import uuid4
from urllib.parse import quote as urlquote

import bleach

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone
from django.utils.html import strip_tags
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from .models import ShipmentItem
from .models import AccessRole, CategoryAttribute, Contact, ContractChangeRequest, Customer, CustomerCodeSequence, EmployeeProfile, FinancePlanWriteoff, FollowUp, FollowUpAttachment, GoodsReceipt, HSCode, InventoryMovement, OperationLog, Order, OrderItem, OrganizationUnit, PackagingTemplate, PackingPlan, PackingPlanCarton, PackingPlanCartonItem, PaymentPlan, Position, Product, ProductCategory, ProductCertificate, ProductCodeSequence, ProductParameter, PurchaseMOQException, PurchaseOrder, PurchaseOrderItem, Quote, QuoteImportantNote, QuoteItem, RolePermission, Shipment, ShipmentPackage, ShipmentPackageItem, SKUPackagingProfile, SKU, SKUVersion, Supplier, SupplierSKU, Transaction
from .country_registry import AmbiguousCountryError, CountryNotFoundError, display_country, resolve_country_code
from .customer_status import customer_status_display
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


def serializer_user(context):
    request = context.get("request")
    return request.user if request is not None else context.get("user")


def protected_media_url(file_field):
    if not file_field:
        return ""
    return f"/api/media/{urlquote(file_field.name, safe='/')}"


class ProtectedImageField(serializers.ImageField):
    """Keep image uploads writable while returning an authorization-aware URL."""

    def to_representation(self, value):
        return protected_media_url(value) if value else None


def redact_snapshot(value, hidden_fields):
    if isinstance(value, dict):
        return {
            key: redact_snapshot(item, hidden_fields)
            for key, item in value.items()
            if key not in hidden_fields
        }
    if isinstance(value, list):
        return [redact_snapshot(item, hidden_fields) for item in value]
    return value


class SupplierSerializer(serializers.ModelSerializer):
    payment_terms_summary = serializers.SerializerMethodField()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if not user_can(serializer_user(self.context), "purchases", "view"):
            data.pop("purchase_count", None)
        return data

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
        if "is_active" in self.initial_data:
            raise serializers.ValidationError({"is_active": "请使用供应商的停用或启用操作。"})
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

    def to_representation(self, instance):
        data = super().to_representation(instance)
        user = serializer_user(self.context)
        if not user_can(user, "skus", "view"):
            data.update(sku=None, internal_sku_code="", internal_sku_name="", product_name="")
        elif not user_can(user, "products", "view"):
            data["product_name"] = ""
        if not user_can(user, "purchases", "view"):
            data["purchase_price"] = None
        return data

    def validate(self, attrs):
        user = serializer_user(self.context)
        sku = attrs.get("sku", getattr(self.instance, "sku", None))
        if user is not None and sku and not user_can(user, "skus", "view"):
            raise PermissionDenied("供应商来源需要 SKU 查看权限。")
        if user is not None and "purchase_price" in attrs and not user_can(user, "purchases", "update"):
            current_price = self.instance.purchase_price if self.instance else Decimal("0")
            if attrs["purchase_price"] != current_price:
                raise PermissionDenied("修改供应商采购价需要采购修改权限。")
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

    def to_representation(self, instance):
        data = super().to_representation(instance)
        user = serializer_user(self.context)
        if instance.entity == "crm.purchaseorder":
            from .sales_scope import effective_data_scope
            # Raw audit snapshots include sales IDs and payment totals. Retain the
            # shared action history, never alter the stored historical snapshot.
            if effective_data_scope(user) != "all" or not all(user_can(user, module, "view") for module in ("orders", "finance", "transactions", "suppliers", "skus")):
                for field in ("before_data", "after_data", "metadata", "changed_fields"):
                    data[field] = [] if field == "changed_fields" else {}
        elif instance.entity == "crm.transaction":
            hidden_fields = set()
            if not user_can(user, "customers", "view"):
                hidden_fields.update({"customer", "customer_id", "customer_name"})
            if not user_can(user, "orders", "view"):
                hidden_fields.update({"order", "order_id", "order_no"})
            if not user_can(user, "purchases", "view"):
                hidden_fields.update({"purchase_order", "purchase_order_id", "purchase_no"})
            if not user_can(user, "suppliers", "view"):
                hidden_fields.update({"supplier", "supplier_id", "supplier_name"})
            if not user_can(user, "finance", "view"):
                hidden_fields.update({"plan", "plan_id", "allocations", "advance_allocations", "allocated_amount"})
            for field in ("before_data", "after_data", "metadata"):
                if isinstance(data.get(field), dict):
                    data[field] = redact_snapshot(data[field], hidden_fields)
            data["changed_fields"] = [key for key in data.get("changed_fields", []) if key not in hidden_fields]
        elif instance.entity == "crm.order" and instance.action_label == "调整销售订单数量":
            finance_visible = user_can(user, "finance", "view") and user_can(user, "transactions", "view")
            procurement_visible = user_can(user, "purchases", "view")
            hidden_financial = {
                "total_amount", "before_total_amount", "after_total_amount", "amount_delta",
                "payment_plan_delta", "planned_amount", "settled_amount", "paid_amount",
                "outstanding_before", "outstanding_after", "outstanding_amount", "balance_amount",
            }
            for field in ("before_data", "after_data"):
                data[field] = redact_snapshot(data.get(field), hidden_financial if not finance_visible else set())
            metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
            metadata = redact_snapshot(metadata, hidden_financial if not finance_visible else set())
            if not finance_visible:
                metadata["summary"] = "数量变更金额影响受权限保护。"
            raw_warnings = metadata.get("warnings") if isinstance(metadata.get("warnings"), list) else []
            visible_warnings = []
            for warning in raw_warnings:
                text = str(warning)
                if "采购" in text:
                    if procurement_visible:
                        visible_warnings.append(text)
                    else:
                        visible_warnings.append("采购影响信息受权限保护。")
                elif finance_visible:
                    visible_warnings.append(text)
                else:
                    visible_warnings.append("财务影响信息受权限保护。")
            metadata["warnings"] = list(dict.fromkeys(visible_warnings))
            data["metadata"] = metadata
            data["changed_fields"] = [
                key for key in data.get("changed_fields", [])
                if finance_visible or key not in hidden_financial
            ]
        elif instance.entity in {"crm.order", "crm.quote"}:
            hidden_fields = set()
            if not user_can(user, "customers", "view"):
                hidden_fields.update({"customer", "customer_id", "customer_name", "buyer_company_name", "buyer_country_snapshot", "buyer_tax_id", "tax_id", "recipient_name", "buyer_address", "buyer_email", "buyer_phone"})
            if not user_can(user, "skus", "view"):
                hidden_fields.update({"sku", "sku_id", "sku_code", "sku_code_snapshot", "sales_model", "sales_model_snapshot", "product_name", "display_name", "description"})
            if not user_can(user, "suppliers", "view"):
                hidden_fields.update({"supplier", "supplier_id", "supplier_name", "supplier_sku", "supplier_sku_id", "supplier_sku_code", "supplier_model", "supplier_barcode", "supplier_allocation"})
            if not user_can(user, "purchases", "view"):
                hidden_fields.update({"cost_price", "unit_cost", "purchase_price", "supplier_price_snapshot"})
            if not user_can(user, "quotes", "view"):
                hidden_fields.update({"quote", "quote_id", "quote_no"})
            if not (user_can(user, "finance", "view") and user_can(user, "transactions", "view")):
                hidden_fields.update({"paid_amount", "outstanding_amount", "balance_amount", "settled_amount", "allocations", "plan_id"})
            for field in ("before_data", "after_data", "metadata"):
                data[field] = redact_snapshot(data.get(field), hidden_fields)
            data["changed_fields"] = [key for key in data.get("changed_fields", []) if key not in hidden_fields]
        elif instance.entity == "crm.sku":
            hidden_fields = set()
            if not user_can(user, "purchases", "view"):
                hidden_fields.update({"cost_price"})
            if not user_can(user, "suppliers", "view"):
                hidden_fields.update({"supplier", "supplier_id", "supplier_name", "supplier_sku", "supplier_sku_id", "supplier_sku_code"})
            for field in ("before_data", "after_data", "metadata"):
                data[field] = redact_snapshot(data.get(field), hidden_fields)
            data["changed_fields"] = [key for key in data.get("changed_fields", []) if key not in hidden_fields]
        elif instance.entity == "crm.skutradeunit" and not user_can(user, "suppliers", "view"):
            hidden_fields = {"supplier", "supplier_id", "supplier_name"}
            for field in ("before_data", "after_data", "metadata"):
                if isinstance(data.get(field), dict):
                    data[field] = redact_snapshot(data[field], hidden_fields)
            data["changed_fields"] = [key for key in data.get("changed_fields", []) if key not in hidden_fields]
        elif instance.entity == "crm.inventorymovement":
            hidden_fields = {"order", "order_id", "order_no", "related_orders", "related_order_ids", "related_order_nos"}
            if not user_can(user, "suppliers", "view"):
                hidden_fields.update({"supplier_sku", "supplier_sku_id"})
            if not user_can(user, "purchases", "view"):
                hidden_fields.add("unit_cost")
            if user_can(user, "orders", "view"):
                from .sales_scope import scope_customer_related_queryset
                visible_order_ids = set(scope_customer_related_queryset(
                    Order.objects.all(), user,
                ).values_list("pk", flat=True))
                for field in ("before_data", "after_data", "metadata"):
                    payload = data.get(field)
                    if isinstance(payload, dict):
                        order_id = payload.get("order") or payload.get("order_id")
                        if order_id and str(order_id) not in {str(pk) for pk in visible_order_ids}:
                            payload = redact_snapshot(payload, hidden_fields)
                        elif isinstance(payload.get("related_orders"), list):
                            related = payload["related_orders"]
                            if related and isinstance(related[0], dict):
                                payload["related_orders"] = [row for row in related if str(row.get("id")) in {str(value) for value in visible_order_ids}]
                            else:
                                payload["related_orders"] = [pk for pk in related if str(pk) in {str(value) for value in visible_order_ids}]
                            payload.pop("related_order_nos", None)
                        elif isinstance(payload.get("related_order_ids"), list):
                            payload["related_order_ids"] = [pk for pk in payload["related_order_ids"] if str(pk) in {str(value) for value in visible_order_ids}]
                            payload.pop("related_order_nos", None)
                        data[field] = payload
            else:
                for field in ("before_data", "after_data", "metadata"):
                    payload = data.get(field)
                    if isinstance(payload, dict):
                        data[field] = redact_snapshot(payload, hidden_fields)
            data["changed_fields"] = [key for key in data.get("changed_fields", []) if key not in hidden_fields]
        elif instance.entity == "crm.sharedreporttemplate" and not user_can(user, "reports", "update"):
            data["before_data"] = {}
            data["after_data"] = {}
            data["metadata"] = {}
            data["changed_fields"] = []
        return data

    def get_operator_name(self, obj):
        if not user_can(serializer_user(self.context), "employees", "view"):
            return ""
        return obj.operator.get_username() if obj.operator else "系统"


class GoodsReceiptSerializer(serializers.ModelSerializer):
    overage_quantity = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    overage_reason_display = serializers.CharField(source="get_overage_reason_display", read_only=True)
    overage_summary = serializers.SerializerMethodField()

    def get_overage_summary(self, obj):
        if not obj.is_overage or obj.overage_quantity <= 0:
            return ""
        return f"超到 {obj.overage_quantity}（{obj.get_overage_reason_display()}）"

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if not user_can(serializer_user(self.context), "inventory", "view"):
            data["inventory_movement"] = None
            data["reversal_inventory_movement"] = None
        return data

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


class FinancePlanWriteoffInputSerializer(serializers.Serializer):
    plan = serializers.IntegerField(min_value=1)
    amount = serializers.DecimalField(max_digits=14, decimal_places=4, min_value=Decimal("0.0001"))
    reason = serializers.CharField(min_length=5, max_length=500, allow_blank=False, trim_whitespace=True)
    request_key = serializers.CharField(min_length=1, max_length=128, allow_blank=False, trim_whitespace=True)


class FinancePlanWriteoffCorrectionInputSerializer(serializers.Serializer):
    writeoff = serializers.IntegerField(min_value=1)
    amount = serializers.DecimalField(max_digits=14, decimal_places=4, min_value=Decimal("0.0001"))
    reason = serializers.CharField(min_length=5, max_length=500, allow_blank=False, trim_whitespace=True)
    request_key = serializers.CharField(min_length=1, max_length=128, allow_blank=False, trim_whitespace=True)


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
        return GoodsReceiptSerializer(obj.receipts.all(), many=True, context=self.context).data

    class Meta:
        model = PurchaseOrderItem
        fields = ["id", "sku", "supplier_sku", "sku_code", "display_name", "sales_model", "supplier_name", "supplier_model", "supplier_sku_code", "supplier_barcode", "supplier_characteristics_snapshot", "quantity", "unit_price", "received_quantity", "remaining_quantity", "overage_quantity", "amount", "receipts"] + TRADE_FIELDS
        read_only_fields = ["supplier_characteristics_snapshot"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        user = serializer_user(self.context)
        if not user_can(user, "skus", "view"):
            data.update(sku=None, sku_code="", display_name="", sales_model="")
        if not user_can(user, "suppliers", "view"):
            data.update(
                supplier_sku=None, supplier_name="", supplier_model="", supplier_sku_code="",
                supplier_barcode="", supplier_characteristics_snapshot={},
            )
        return data


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
    moq_exception = serializers.SerializerMethodField()

    def get_payment_plans(self, obj):
        if not user_can(serializer_user(self.context), "finance", "view"):
            return []
        return PaymentPlanSerializer(obj.payment_plans.all().order_by("id"), many=True, context=self.context).data

    def get_moq_exception(self, obj):
        try:
            exception = obj.moq_exception
        except PurchaseMOQException.DoesNotExist:
            return None
        user = serializer_user(self.context)
        details = []
        for detail in exception.details or []:
            row = dict(detail)
            if not user_can(user, "skus", "view"):
                row.update(sku_code="", display_name="")
            if not user_can(user, "suppliers", "view"):
                row["supplier_sku_code"] = ""
            details.append(row)
        operator = exception.operator
        operator_name = ""
        if operator is not None and user_can(user, "employees", "view"):
            operator_name = operator.get_full_name() or operator.get_username()
        return {
            "id": exception.id,
            "purchase_order": exception.purchase_order_id,
            "reason": exception.reason,
            "details": details,
            "created_at": serializers.DateTimeField().to_representation(exception.created_at),
            "operator_id": operator.pk if operator is not None and user_can(user, "employees", "view") else None,
            "operator_name": operator_name,
        }

    def to_representation(self, instance):
        data = super().to_representation(instance)
        user = serializer_user(self.context)
        from .sales_scope import scope_customer_related_queryset
        data['effective_party'] = None
        if user_can(user, 'suppliers', 'view') and instance.status not in {'draft', 'cancelled'}:
            from .party_document_version import effective_snapshot
            try:
                data['effective_party'] = effective_snapshot(instance)
            except DjangoValidationError as exc:
                raise serializers.ValidationError({'effective_party': exc.messages}) from exc
        associated_ids = {row["id"] for row in data["related_orders"]}
        if instance.order_id:
            associated_ids.add(instance.order_id)
        visible = scope_customer_related_queryset(Order.objects.filter(pk__in=associated_ids), user) if user_can(user, "orders", "view") else Order.objects.none()
        visible_ids = set(visible.values_list("pk", flat=True))
        if not user_can(user, "suppliers", "view"):
            data.update(
                supplier=None,
                supplier_name="",
                supplier_name_snapshot="",
                supplier_address_snapshot="",
                supplier_contact_name_snapshot="",
                supplier_phone_snapshot="",
                supplier_email_snapshot="",
            )
        if instance.order_id not in visible_ids:
            data["order"] = None
            data["order_no"] = ""
        data["sales_link_restricted"] = bool(instance.order_id and instance.order_id not in visible_ids)
        data["related_orders"] = [row for row in data["related_orders"] if row["id"] in visible_ids]
        if not (user_can(user, "finance", "view") and user_can(user, "transactions", "view")):
            data.pop("paid_amount", None)
            data.pop("unpaid_amount", None)
        return data

    def validate_payment_terms_snapshot(self, value):
        from .payment_terms import validate_payment_terms
        try:
            # A draft may intentionally have no negotiated payment stages yet.
            # Formal POs keep the saved snapshot, and finance only creates plans
            # from a non-empty snapshot; never fill one from the supplier rule.
            return validate_payment_terms(value, allow_default=True)
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
        read_only_fields = [
            "purchase_no", "status", "cancelled_at", "cancellation_reason",
            "supplier_name_snapshot", "supplier_address_snapshot",
            "supplier_contact_name_snapshot", "supplier_phone_snapshot",
            "supplier_email_snapshot",
        ]

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
        historical_mode = bool(self.context.get("historical_mode"))
        if historical_mode and attrs.get("order"):
            raise serializers.ValidationError({"order": "历史采购订单不能关联正式销售订单。"})
        if "order" in attrs and (self.instance is None or attrs["order"] != self.instance.order):
            from .procurement_scope import require_order_writes
            require_order_writes(serializer_user(self.context), [getattr(self.instance, "order_id", None), getattr(attrs["order"], "pk", None)])
        if self.instance is not None and self.instance.status == "draft":
            cost_changed = any(key in attrs and attrs[key] != getattr(self.instance, key) for key in ("supplier", "currency", "exchange_rate"))
            cost_changed = cost_changed or ("items" in attrs and not contract_items_match(self.instance, attrs["items"]))
            if cost_changed:
                from .procurement_scope import require_order_writes
                require_order_writes(serializer_user(self.context), self.instance.items.values_list("cost_allocations__order_id", flat=True))
        validate_contract_edit(self.instance, attrs, purchase=True)
        currency = attrs.get("currency", getattr(self.instance, "currency", None))
        rate = attrs.get("exchange_rate", getattr(self.instance, "exchange_rate", None))
        if rate is None or rate <= 0:
            raise serializers.ValidationError({"exchange_rate": "请输入大于 0 的采购单对人民币汇率。"})
        if currency == "CNY" and rate != Decimal("1"):
            raise serializers.ValidationError({"exchange_rate": "人民币采购单的对人民币汇率必须为 1。"})
        supplier = attrs.get("supplier", getattr(self.instance, "supplier", None))
        user = serializer_user(self.context)
        if not historical_mode and supplier and not supplier.is_active:
            raise serializers.ValidationError({"supplier": "停用供应商不能用于新采购，请先启用供应商或更换供应商。"})
        if user is not None and supplier and (self.instance is None or supplier.pk != self.instance.supplier_id) and not user_can(user, "suppliers", "view"):
            raise PermissionDenied("关联供应商需要供应商查看权限。")
        if user is not None and attrs.get("items") and not user_can(user, "skus", "view"):
            raise PermissionDenied("采购明细需要 SKU 查看权限。")
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
            if not historical_mode and self.instance is None and item.get("sku") and item["sku"].candidate_overrides.filter(supplier=supplier, is_allowed=False).exists():
                raise serializers.ValidationError({"supplier": "该 SKU 已排除此供应商，请先恢复候选资格。"})
            source = item.get("supplier_sku")
            if source is None:
                continue
            if supplier and source.supplier_id != supplier.pk:
                errors.append({"items": {index: {"supplier_sku": "供应商来源必须属于当前采购单供应商。"}}})
            if item.get("sku") and source.sku_id != item["sku"].pk:
                errors.append({"items": {index: {"supplier_sku": "供应商来源必须对应当前采购明细 SKU。"}}})
            if not historical_mode and (self.instance is None or self.instance.status == "draft") and not source.is_active:
                errors.append({"items": {index: {"supplier_sku": "新建或编辑采购草稿只能选择启用中的供应商来源。"}}})
        if errors:
            raise serializers.ValidationError(errors[0])
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        items = validated_data.pop("items")
        validated_data.pop("purchase_no", None)
        historical_mode = bool(self.context.get("historical_mode"))
        from .services.supplier_candidates import resolve_purchase_item_sources
        for item in items:
            if not historical_mode and not item["sku"].active:
                raise serializers.ValidationError({"sku": "新采购不能选择停用或已归档的 SKU。"})
        if not historical_mode:
            resolve_purchase_item_sources(
                items, validated_data["supplier"], order=validated_data.get("order"),
                purchase_currency=validated_data.get("currency"),
            )
        else:
            validated_data["order"] = None
            validated_data["status"] = "historical"
            validated_data["historical_only"] = True
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
        if not historical_mode:
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
    warehouse = serializers.CharField(max_length=100, required=False)
    warehouse_type = serializers.ChoiceField(choices=["自有仓", "第三方仓"], required=False)
    lot_reference = serializers.CharField(max_length=160, required=False, allow_blank=True)
    request_key = serializers.CharField(max_length=100, required=False, allow_blank=False)
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
    warehouse = serializers.CharField(max_length=100, required=False)
    warehouse_type = serializers.ChoiceField(choices=["自有仓", "第三方仓"], required=False)
    lot_reference = serializers.CharField(max_length=160, required=False, allow_blank=True)
    trade_unit = serializers.IntegerField(required=False, allow_null=True)
    trade_quantity = serializers.DecimalField(max_digits=14, decimal_places=2, required=False)
    trade_unit_price = serializers.DecimalField(max_digits=16, decimal_places=4, required=False)

    order_item = serializers.IntegerField(min_value=1)
    quantity = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.01"), required=False)
    overage_reason = serializers.ChoiceField(choices=["", "customer_addon", "gift_or_sample", "packing_variance"], required=False, allow_blank=True)


class ShipmentInputSerializer(serializers.Serializer):
    request_key = serializers.CharField(max_length=100, required=False, allow_blank=False)
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
    effective_permissions = serializers.SerializerMethodField()
    has_all_permissions = serializers.SerializerMethodField()
    default_data_scope_display = serializers.CharField(source="get_default_data_scope_display", read_only=True)
    employee_count = serializers.IntegerField(read_only=True, default=0)

    def get_has_all_permissions(self, obj):
        """Expose the server-defined highest business role contract.

        The stored matrix remains an editable template for ordinary roles.  The
        built-in superadmin is intentionally locked and is authorized by the
        server as an effective all-module role, so clients must not infer its
        access from possibly older/incomplete stored rows.
        """
        return obj.code == "superadmin"

    def get_effective_permissions(self, obj):
        if self.get_has_all_permissions(obj):
            return [
                {
                    "module": module,
                    "module_display": label,
                    "can_view": True,
                    "can_create": True,
                    "can_update": True,
                    "can_delete": True,
                    "can_export": True,
                    "can_import": True,
                }
                for module, label in RolePermission.MODULE_CHOICES
            ]
        return RolePermissionSerializer(obj.permissions.all(), many=True).data

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
    country_display = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()
    contacts = CustomerContactInputSerializer(many=True, write_only=True, required=False)

    class Meta:
        model = Customer
        fields = "__all__"
        # Customer status is a persisted projection of follow-ups, quotes and
        # formal orders, rather than a manually maintained customer attribute.
        read_only_fields = ["code", "status", "owner"]

    def get_country_display(self, obj):
        return display_country(obj.country)

    def get_status_display(self, obj):
        return customer_status_display(obj.status)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if not user_can(serializer_user(self.context), "orders", "view"):
            data["order_count"] = None
            data["sales_amount"] = None
        return data

    def validate(self, attrs):
        from .sales_scope import allowed_employee_ids, effective_data_scope, employee_profile_for
        from .permissions import user_can

        if "country" in attrs:
            raw_country = str(attrs.get("country") or "").strip()
            if raw_country:
                # Bulk/history imports are deliberately lossless: even a
                # recognizable legacy label stays as entered so importing an
                # old customer file cannot rewrite the existing country text.
                # Interactive create/edit requests must choose a canonical
                # alpha-2 value from the local picker.
                if not self.context.get("allow_import_without_contacts"):
                    try:
                        attrs["country"] = resolve_country_code(raw_country)
                    except AmbiguousCountryError:
                        raise serializers.ValidationError({"country": f"国家/地区“{raw_country}”存在歧义，请从候选中明确选择。"})
                    except CountryNotFoundError:
                        raise serializers.ValidationError({"country": f"无法识别国家/地区“{raw_country}”，请从国家选择框中选择标准国家后再保存。"})
        if self.instance is None and not attrs.get("contacts") and not self.context.get("allow_import_without_contacts"):
            raise serializers.ValidationError({"contacts": "新建客户时请至少填写一位联系人。"})
        request = self.context.get("request")
        user = request.user if request else self.context.get("user")
        if self.instance is None and attrs.get("contacts") and user is not None and not user_can(user, "contacts", "create"):
            raise PermissionDenied("创建客户联系人需要联系人创建权限。")
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
            else:
                # Keep the legacy display name in sync when an all-scope user
                # explicitly clears the structured owner field.
                attrs["owner"] = ""
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

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if not user_can(serializer_user(self.context), "customers", "view"):
            data.update(customer=None, customer_name="")
        return data


    def validate_customer(self, customer):
        from .sales_scope import customer_in_scope
        request = self.context.get("request")
        user = request.user if request else serializer_user(self.context)
        if not user_can(user, "customers", "view"):
            raise PermissionDenied("关联客户需要客户查看权限。")
        if user and not customer_in_scope(customer.pk, user):
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

    def to_representation(self, instance):
        data = super().to_representation(instance)
        user = serializer_user(self.context)
        if not user_can(user, "customers", "view"):
            data.update(customer=None, customer_name="")
        if not user_can(user, "contacts", "view"):
            data.update(contact=None, contact_name="")
        return data

    def validate(self, attrs):
        from .sales_scope import customer_in_scope
        request = self.context.get("request")
        customer = attrs.get("customer", getattr(self.instance, "customer", None))
        contact = attrs.get("contact", getattr(self.instance, "contact", None))
        user = request.user if request else serializer_user(self.context)
        if customer and not user_can(user, "customers", "view"):
            raise PermissionDenied("关联客户需要客户查看权限。")
        if contact and not user_can(user, "contacts", "view"):
            raise PermissionDenied("关联联系人需要联系人查看权限。")
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
    file = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()

    class Meta:
        model = FollowUpAttachment
        fields = ["id", "name", "file", "url", "content_type", "size", "created_at"]
        read_only_fields = fields

    def get_url(self, obj):
        if not obj.file:
            return ""
        return self.get_file(obj)

    def get_file(self, obj):
        return protected_media_url(obj.file)


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


class ProductSerializer(serializers.ModelSerializer):
    sku_definitions = serializers.SerializerMethodField()

    def get_sku_definitions(self, obj):
        plan = obj.sku_parameter_plans.filter(status="published").order_by("-version").first()
        return plan.definitions if plan else None

    category_name = serializers.CharField(source="category.name", read_only=True, default="未分类")
    hs_code_value = serializers.CharField(source="hs_code.code", read_only=True, default="")
    sku_count = serializers.IntegerField(read_only=True, default=0)
    parameter_count = serializers.IntegerField(read_only=True, default=0)
    certificate_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Product
        fields = "__all__"
        read_only_fields = ["code", "hs_code", "combination_rules"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        user = serializer_user(self.context)
        if not user_can(user, "categories", "view"):
            data.update(category=None, category_name="", additional_categories=[])
        if not user_can(user, "hs_codes", "view"):
            data.update(hs_code=None, hs_code_value="")
        if not user_can(user, "suppliers", "view"):
            data["suppliers"] = []
        if not user_can(user, "skus", "view"):
            data["sku_count"] = None
        if not user_can(user, "parameters", "view"):
            data["parameter_count"] = None
            data["sku_definitions"] = None
        if not user_can(user, "certificates", "view"):
            data["certificate_count"] = None
        return data

    def validate_sales_model_prefix(self, value):
        if value is None or not str(value).strip():
            return None
        value = str(value).strip().upper()
        if not re.fullmatch(r"[A-Z0-9]+", value):
            raise serializers.ValidationError("销售型号只能包含字母和数字，例如 BTY、COB320 或 SMD120。")
        return value

    def validate(self, attrs):
        user = serializer_user(self.context)
        if user is not None and any(field in attrs for field in ("category", "additional_categories")) and not user_can(user, "categories", "view"):
            raise PermissionDenied("产品分类关联需要分类查看权限。")
        if user is not None and "suppliers" in attrs and not user_can(user, "suppliers", "update"):
            raise PermissionDenied("修改产品供应商关联需要供应商修改权限。")
        if "hs_code" in self.initial_data:
            raise serializers.ValidationError({"hs_code": "HS 编码请通过“HS 编码维护”页面统一分配。"})
        if not self.instance and not attrs.get("sales_model_prefix"):
            raise serializers.ValidationError({"sales_model_prefix": "新建产品时必须填写销售型号。"})
        if self.instance:
            category_changed = "category" in attrs and attrs["category"] != self.instance.category
            additional_changed = (
                "additional_categories" in attrs
                and {category.pk for category in attrs["additional_categories"]}
                != set(self.instance.additional_categories.values_list("pk", flat=True))
            )
            if (category_changed or additional_changed) and product_has_unfrozen_sku_schema(self.instance):
                raise serializers.ValidationError({"category": UNFROZEN_PRODUCT_CATEGORY_MESSAGE})
            if (
                "sales_model_prefix" in attrs
                and attrs["sales_model_prefix"] != self.instance.sales_model_prefix
                and self.instance.skus.exists()
            ):
                raise serializers.ValidationError({
                    "sales_model_prefix": "该产品已有 SKU，销售型号前缀请使用预览并确认流程修改。"
                })
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        validated_data.pop("code", None)
        imported_code = validated_data.pop("imported_code", None) if self.context.get("allow_import_code") else None
        additional_categories = validated_data.pop("additional_categories", [])
        suppliers = validated_data.pop("suppliers", [])
        product = Product.objects.create(code=imported_code or allocate_product_code(), **validated_data)
        product.additional_categories.set(additional_categories)
        product.suppliers.set(suppliers)
        return product


class HSCodeSerializer(serializers.ModelSerializer):
    product_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = HSCode
        fields = "__all__"

    def validate_code(self, value):
        value = str(value or "").strip()
        if not re.fullmatch(r"[0-9A-Za-z.-]+", value):
            raise serializers.ValidationError("HS 编码只能包含字母、数字、点号或连字符。")
        return value


class SKUSerializer(serializers.ModelSerializer):
    trade_units = SKUTradeUnitSerializer(many=True, read_only=True)
    image_thumbnail = serializers.SerializerMethodField()
    image = ProtectedImageField(required=False, allow_null=True)

    def get_image_thumbnail(self, obj):
        if not obj.image:
            return ""
        from django.urls import reverse
        from hashlib import sha256
        version = sha256(obj.image.name.encode()).hexdigest()[:16]
        url = reverse("sku-thumbnail", args=[obj.pk]) + f"?v={version}"
        request = self.context.get("request")
        return request.build_absolute_uri(url) if request else url

    sku_code = serializers.CharField(source="sku", read_only=True)
    identity_change_confirmed = serializers.BooleanField(write_only=True, required=False, default=False)
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_code = serializers.CharField(source="product.code", read_only=True)
    category_names = serializers.SerializerMethodField()
    status_label = serializers.SerializerMethodField()
    quote_count = serializers.IntegerField(read_only=True, default=0)
    order_count = serializers.IntegerField(read_only=True, default=0)
    sales_model_missing = serializers.SerializerMethodField()
    stock_quantity = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True, default=0)
    actual_quantity = serializers.SerializerMethodField()
    reserved_quantity = serializers.SerializerMethodField()
    available_quantity = serializers.SerializerMethodField()
    in_transit_quantity = serializers.SerializerMethodField()
    to_procure_quantity = serializers.SerializerMethodField()
    has_anomaly = serializers.SerializerMethodField()
    packaging = serializers.SerializerMethodField()
    packaging_profile_input = serializers.DictField(write_only=True, required=False, allow_null=True)
    historical_matches = serializers.SerializerMethodField()

    class Meta:
        model = SKU
        fields = "__all__"
        extra_kwargs = {"sku": {"required": False, "read_only": True}, "identity_signature": {"read_only": True}, "schema_version": {"read_only": True}}

    def to_representation(self, instance):
        data = super().to_representation(instance)
        user = serializer_user(self.context)
        if not user_can(user, "products", "view"):
            data["product"] = None
        if not user_can(user, "inventory", "view"):
            for field in ("stock_quantity", "actual_quantity", "reserved_quantity", "available_quantity", "in_transit_quantity", "has_anomaly"):
                if field in data:
                    data[field] = None
        if not (user_can(user, "inventory", "view") and user_can(user, "orders", "view")):
            data["to_procure_quantity"] = None
        if not user_can(user, "orders", "view"):
            data["order_count"] = None
        if not user_can(user, "quotes", "view"):
            data["quote_count"] = None
        if not user_can(user, "packaging", "view"):
            data["packaging"] = None
        if not user_can(user, "purchases", "view"):
            data["cost_price"] = None
        return data

    def _packaging_serializer(self, data, sku=None):
        profile = SKUPackagingProfile.objects.filter(sku=sku).first() if sku else None
        serializer = SKUPackagingProfileSerializer(profile, data=data, partial=True, context=self.context)
        # The parent SKU owns this association; nested input cannot redirect it.
        if "sku" in data:
            raise serializers.ValidationError({"packaging_profile_input": "包装配置不能指定其他 SKU。"})
        try:
            serializer.is_valid(raise_exception=True)
        except serializers.ValidationError as error:
            raise serializers.ValidationError({"packaging_profile_input": error.detail})
        return serializer

    def validate_packaging_profile_input(self, value):
        if value is not None:
            self._packaging_serializer(value, self.instance)
        return value

    def _save_packaging(self, sku, data):
        if data is not None:
            self._packaging_serializer(data, sku).save(sku=sku)

    def _generated_identity(self, values):
        product = values.get("product", getattr(self.instance, "product", None))
        if not product:
            return {}
        return build_sku_identity(
            product,
            values.get("specification", getattr(self.instance, "specification", "")),
            values.get("parameter_values", getattr(self.instance, "parameter_values", {})),
            values.get("product_details", getattr(self.instance, "product_details", [])),
            values.get("sales_model_abbreviations", getattr(self.instance, "sales_model_abbreviations", {})),
        )

    def _complete_abbreviations(self, product, parameters, abbreviations):
        return complete_sales_model_abbreviations(abbreviations, parameter_pairs(product, parameters))

    def _ensure_unique_display_name(self, value):
        normalized = normalize_display_name(value)
        if not normalized:
            return normalized
        # Compare the normalized Python value as well as the indexed key so
        # legacy rows which predate this field are also covered.
        candidates = SKU.objects.exclude(pk=self.instance.pk if self.instance else None).values_list("display_name_cn", flat=True)
        duplicate = next((name for name in candidates if normalize_display_name(name) == normalized), None)
        if duplicate is not None:
            # An unchanged legacy duplicate may still be edited for unrelated
            # fields; only a new name or a name change is rejected here.
            if not self.instance or normalize_display_name(self.instance.display_name_cn) != normalized:
                raise serializers.ValidationError({"display_name_cn": f"内部识别名称已存在（不区分大小写）：{duplicate}"})
        return normalized

    def validate_display_name_cn(self, value):
        self._ensure_unique_display_name(value)
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        user = serializer_user(self.context)
        if "cost_price" in attrs and user is not None and not user_can(user, "purchases", "update"):
            current_cost = self.instance.cost_price if self.instance else Decimal("0")
            if attrs["cost_price"] != current_cost:
                raise PermissionDenied("修改 SKU 成本需要采购修改权限。")
        if self.instance:
            if attrs.get("active") and self.instance.successors.exists():
                raise serializers.ValidationError({"active": "已拆分或合并的历史 SKU 不可重新启用。"})
            if "product" in attrs and attrs["product"].pk != self.instance.product_id:
                raise serializers.ValidationError({"product": "已有 SKU 不能更换所属产品，请新建 SKU。"})
            if "unit" in attrs and attrs["unit"] != self.instance.unit and any(
                getattr(self.instance, relation).exists() for relation in ("quote_items", "order_items", "purchase_order_items", "inventory_movements", "trade_units")
            ):
                raise serializers.ValidationError({"unit": "已有业务记录的 SKU 不能更换计量单位。"})
        identity_change_confirmed = bool(attrs.get("identity_change_confirmed"))
        identity_fields = {"product", "parameter_values", "specification", "display_name_cn", "sales_model"}
        if self.instance:
            changed_identity_fields = {
                field for field in identity_fields
                if field in attrs and getattr(self.instance, field) != attrs[field]
            }
            if "parameter_values" in changed_identity_fields and identity_signature(self.instance.product, self.instance.parameter_values) == identity_signature(self.instance.product, attrs["parameter_values"]):
                changed_identity_fields.discard("parameter_values")
            has_business_history = any(
                getattr(self.instance, relation).exists()
                for relation in ("quote_items", "order_items", "purchase_order_items", "inventory_movements")
            )
            if has_business_history and changed_identity_fields.intersection({"parameter_values", "specification"}):
                raise serializers.ValidationError(
                    "该 SKU 已存在业务历史，不能直接修改身份参数；如产品规格发生实质变化，请新建 SKU 或通过正式 SKU 参数演化流程处理。"
                )
            if changed_identity_fields and not identity_change_confirmed:
                labels = {
                    "product": "所属产品",
                    "parameter_values": "SKU 参数",
                    "specification": "规格顺序/内容",
                    "display_name_cn": "内部识别名称",
                    "sales_model": "Sales Model",
                }
                changed_labels = "、".join(labels[field] for field in sorted(changed_identity_fields))
                raise serializers.ValidationError({
                    "identity_change_confirmed": f"检测到身份字段变化（{changed_labels}）。请确认这是一次 SKU 身份变更；系统将保留旧版本快照。若只是批次或资料差异，请使用备注/版本信息，不要修改 SKU 身份。"
                })
        product = attrs.get("product", getattr(self.instance, "product", None))
        parameters = attrs.get("parameter_values", getattr(self.instance, "parameter_values", {}))
        if product and ("parameter_values" in attrs or "sales_model_abbreviations" in attrs):
            attrs["sales_model_abbreviations"] = self._complete_abbreviations(
                product,
                parameters,
                attrs.get("sales_model_abbreviations", getattr(self.instance, "sales_model_abbreviations", {})),
            )
        elif "sales_model_abbreviations" in attrs:
            attrs["sales_model_abbreviations"] = normalize_sales_model_abbreviations(attrs["sales_model_abbreviations"])
        if "product_details" in attrs:
            # 销售型号属于 SKU 本身；包装尺寸统一来自包装模板。
            attrs["product_details"] = [
                {key: value for key, value in detail.items() if key not in {"model", "length", "width", "height"}}
                for detail in attrs["product_details"]
                if isinstance(detail, dict)
            ]
        if self.instance and not any(field in attrs and attrs[field] != getattr(self.instance, field)
                                     for field in ("parameter_values", "product", "sales_model_abbreviations")):
            return attrs
        if product:
            from .services.sku_combination_rules import validate_combination
            validate_combination(product, parameters)
            normalized_parameters = {
                str(key).strip().casefold(): value
                for key, value in (parameters or {}).items()
            }
            missing_required = []
            for attribute in category_attributes(product):
                if not attribute.required:
                    continue
                keys = [
                    f"{attribute.category_id}:{attribute.key}",
                    attribute.key,
                    attribute.name,
                ]
                value = next(
                    (normalized_parameters.get(str(key).strip().casefold()) for key in keys if str(key).strip().casefold() in normalized_parameters),
                    "",
                )
                # Older clients used the selected category ID for inherited
                # attributes.  Accept that key shape as well, so a filled value
                # is never rejected merely because the attribute originates
                # from a parent category.
                if not value:
                    suffix = f":{str(attribute.key).strip().casefold()}"
                    value = next((item for key, item in normalized_parameters.items() if key.endswith(suffix)), "")
                if not value:
                    value = raw_parameter_value(parameters, keys[0], attribute.name)
                values = value if isinstance(value, (list, tuple)) else [value]
                if not any(str(item or "").strip() for item in values):
                    missing_required.append(attribute.name)
            if missing_required:
                raise serializers.ValidationError({
                    "parameter_values": f"请填写必填参数：{'、'.join(dict.fromkeys(missing_required))}。"
                })
            signature = identity_signature(product, parameters)
            if signature:
                conflicts = identity_conflict_messages(signature=signature, exclude_sku_id=self.instance.pk if self.instance else None)
                if conflicts:
                    raise serializers.ValidationError({"duplicate_sku": conflicts})
                attrs["identity_signature"] = signature
        if not product or not getattr(product, "sales_model_prefix", None):
            return attrs
        abbreviations = attrs.get("sales_model_abbreviations", getattr(self.instance, "sales_model_abbreviations", {})) or {}
        missing = []
        for pair in parameter_pairs(product, parameters):
            if pair.get("include_in_sales_model") and not re.fullmatch(r"[A-Za-z0-9-]{1,8}", str(abbreviations.get(pair["abbreviation_key"], "")).strip()):
                missing.append(pair["name"])
        if missing:
            raise serializers.ValidationError({"sales_model_abbreviations": f"请为参与生成型号的参数填写 1–8 位字母、数字或连字符缩写：{'、'.join(dict.fromkeys(missing))}。"})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        from .models import SKUParameterPlan
        from .services.sku_plans import definitions_for
        product = Product.objects.select_for_update().get(pk=validated_data["product"].pk)
        if not product.sku_parameter_plans.filter(status="published").exists():
            SKUParameterPlan.objects.create(product=product, version=(product.sku_parameter_plans.order_by("-version").values_list("version", flat=True).first() or 0) + 1, status="published", definitions=definitions_for(product), baseline="")
        validated_data["schema_version"] = product.sku_parameter_plans.filter(status="published").order_by("-version").first().version
        validated_data["product"] = product
        self.instance = None
        # Revalidate under the product lock so concurrent API creates cannot duplicate a combination.
        validated_data = self.validate(dict(validated_data))
        validated_data.pop("identity_change_confirmed", None)
        validated_data.setdefault("sku", allocate_sku_code())
        generated = self._generated_identity(validated_data)
        sales_model_base = generated.pop("sales_model_base", "")
        for field, value in generated.items():
            if not validated_data.get(field):
                validated_data[field] = value
        validated_data["display_name_key"] = self._ensure_unique_display_name(validated_data.get("display_name_cn", ""))
        # The create UI no longer supplies a model; retain an explicit API
        # value for backward compatibility, otherwise use the generated base directly; collisions are rejected below.
        if sales_model_base and not validated_data.get("sales_model"):
            validated_data["sales_model"] = sales_model_base
        conflicts = identity_conflict_messages(
            display_name_cn=validated_data.get("display_name_cn", ""),
            sales_model=validated_data.get("sales_model", ""),
            signature=validated_data.get("identity_signature", ""),
        )
        if conflicts:
            raise serializers.ValidationError({"duplicate_sku": conflicts})
        packaging = validated_data.pop("packaging_profile_input", None)
        instance = super().create(validated_data)
        self._save_packaging(instance, packaging)
        return instance

    @transaction.atomic
    def update(self, instance, validated_data):
        Product.objects.select_for_update().get(pk=instance.product_id)
        instance = SKU.objects.select_for_update().get(pk=instance.pk)
        self.instance = instance
        validated_data = self.validate(dict(validated_data))
        validated_data.pop("identity_change_confirmed", None)
        generated = self._generated_identity(validated_data)
        generated.pop("sales_model_base", None)
        parameter_changed = "parameter_values" in validated_data and validated_data["parameter_values"] != instance.parameter_values
        identity_fields = {"product", "specification", "parameter_values"}
        if identity_fields.intersection(validated_data):
            for field, value in generated.items():
                if parameter_changed and field == "display_name_cn":
                    validated_data[field] = value
                    continue
                if field not in self.initial_data:
                    validated_data[field] = value
        if parameter_changed:
            sales_model_base = self._generated_identity(validated_data).get("sales_model_base", "")
            current_generated_model = self._generated_identity({
                "product": instance.product,
                "specification": instance.specification,
                "parameter_values": instance.parameter_values,
                "product_details": instance.product_details,
                "sales_model_abbreviations": instance.sales_model_abbreviations,
            }).get("sales_model_base", "")
            supplied_model = validated_data.get("sales_model") if "sales_model" in self.initial_data else instance.sales_model
            # Regenerate only when the saved value still equals the model the
            # generator produced for the old identity. A different value is a
            # deliberate manual model; an explicit blank remains legacy-empty.
            auto_model_is_still_saved = (
                supplied_model == instance.sales_model
                and bool(instance.sales_model)
                and instance.sales_model == current_generated_model
            )
            omitted_model_can_generate = "sales_model" not in self.initial_data and not instance.sales_model
            if sales_model_base and (auto_model_is_still_saved or omitted_model_can_generate):
                validated_data["sales_model"] = sales_model_base
            validated_data["display_name_key"] = normalize_display_name(validated_data.get("display_name_cn", "")) or None
            conflicts = identity_conflict_messages(
                display_name_cn=validated_data.get("display_name_cn", ""),
                sales_model=validated_data.get("sales_model", instance.sales_model or ""),
                signature=validated_data.get("identity_signature", ""),
                exclude_sku_id=instance.pk,
            )
            if conflicts:
                raise serializers.ValidationError({"duplicate_sku": conflicts})
        if "display_name_cn" in validated_data and not parameter_changed:
            validated_data["display_name_key"] = self._ensure_unique_display_name(validated_data["display_name_cn"])
        if "sales_model" in validated_data and not parameter_changed:
            conflicts = identity_conflict_messages(
                display_name_cn=validated_data.get("display_name_cn", instance.display_name_cn),
                sales_model=validated_data.get("sales_model", ""),
                exclude_sku_id=instance.pk,
            )
            if conflicts:
                raise serializers.ValidationError({"duplicate_sku": conflicts})
        version_fields = {"sales_model", "display_name_cn", "description_cn", "description_en", "parameter_values", "specification", "product_details"}
        changed_fields = [field for field in version_fields if field in validated_data and getattr(instance, field) != validated_data[field]]
        if changed_fields:
            SKUVersion.objects.create(
                sku=instance,
                version_no=(instance.versions.order_by("-version_no").values_list("version_no", flat=True).first() or 0) + 1,
                sku_code_snapshot=instance.sku,
                sales_model_snapshot=instance.sales_model or "",
                display_name_cn_snapshot=instance.display_name_cn,
                description_cn_snapshot=instance.description_cn,
                description_en_snapshot=instance.description_en,
                parameter_values_snapshot=instance.parameter_values,
                product_details_snapshot=instance.product_details,
                specification_snapshot=instance.specification,
                changed_fields=sorted(changed_fields),
                changed_by=self.context["request"].user if self.context.get("request") and self.context["request"].user.is_authenticated else None,
                change_reason=str(self.initial_data.get("change_reason", "")).strip(),
            )
        packaging = validated_data.pop("packaging_profile_input", None)
        instance = super().update(instance, validated_data)
        self._save_packaging(instance, packaging)
        return instance

    def _metrics(self, obj):
        from .services.fulfillment import sku_metrics
        return sku_metrics(obj)

    def get_actual_quantity(self, obj):
        return self._metrics(obj)["actual_quantity"]

    def get_reserved_quantity(self, obj):
        return self._metrics(obj)["reserved_quantity"]

    def get_available_quantity(self, obj):
        return self._metrics(obj)["available_quantity"]

    def get_in_transit_quantity(self, obj):
        return self._metrics(obj)["in_transit_quantity"]

    def get_to_procure_quantity(self, obj):
        from .models import OrderItem
        from .services.fulfillment import order_item_metrics
        return sum((order_item_metrics(item)["to_procure_quantity"] for item in OrderItem.objects.filter(sku=obj, order__status__in=["confirmed", "production", "shipped"])), Decimal("0"))

    def get_has_anomaly(self, obj):
        return self.get_available_quantity(obj) < 0

    def get_packaging(self, obj):
        from .services.packaging import packaging_summary
        return packaging_summary(obj)

    def get_historical_matches(self, obj):
        term = str(self.context.get("request").query_params.get("search", "") if self.context.get("request") else "").strip()
        if not term:
            return []
        return list(obj.versions.filter(
            Q(sku_code_snapshot__icontains=term) | Q(sales_model_snapshot__icontains=term) |
            Q(display_name_cn_snapshot__icontains=term) | Q(description_cn_snapshot__icontains=term) |
            Q(description_en_snapshot__icontains=term)
        ).values("version_no", "sales_model_snapshot", "display_name_cn_snapshot", "changed_at", "changed_fields")[:5])

    @staticmethod
    def _category_path(category):
        """Return the complete category hierarchy for a category.

        Category names are unique today, but keeping the hierarchy in the
        response makes the SKU list unambiguous and also lets the shared SKU
        picker expose the same context.  The ``seen`` guard prevents malformed
        legacy data with a parent cycle from causing an infinite loop.
        """
        parts = []
        seen = set()
        current = category
        while current is not None and current.pk not in seen:
            seen.add(current.pk)
            parts.append(current.name)
            current = current.parent
        return " / ".join(reversed(parts))

    def get_category_names(self, obj):
        categories = [obj.product.category] if obj.product.category_id else []
        categories.extend(obj.product.additional_categories.all())
        return [self._category_path(category) for category in categories if category]

    def get_status_label(self, obj):
        return "启用" if obj.active else "停用"

    def get_sales_model_missing(self, obj):
        return not bool((obj.sales_model or "").strip())


class SKUVersionSerializer(serializers.ModelSerializer):
    changed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = SKUVersion
        fields = "__all__"
        read_only_fields = ["sku", "version_no", "sku_code_snapshot", "sales_model_snapshot", "display_name_cn_snapshot", "description_cn_snapshot", "description_en_snapshot", "parameter_values_snapshot", "product_details_snapshot", "specification_snapshot", "changed_fields", "changed_at", "changed_by", "change_reason"]

    def get_changed_by_name(self, obj):
        if not user_can(serializer_user(self.context), "employees", "view"):
            return ""
        return obj.changed_by.get_username() if obj.changed_by else "系统"


class ProductParameterSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = ProductParameter
        fields = "__all__"

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if not user_can(serializer_user(self.context), "products", "view"):
            data.update(product=None, product_name="")
        return data


def certificate_expiry(expires_on, today=None):
    today = today or timezone.localdate()
    days = (expires_on - today).days if expires_on else None
    if days is None:
        status, display = "no_expiry", "无有效期"
    elif days < 0:
        status, display = "expired", "已过期"
    elif days <= 30:
        status, display = "expiring_30", "今日到期" if days == 0 else "30 天内到期"
    elif days <= 90:
        status, display = "expiring_90", "90 天内到期"
    else:
        status, display = "valid", "有效"
    return {"expiry_status": status, "expiry_status_display": display, "days_to_expiry": days}


class ProductCertificateSerializer(serializers.ModelSerializer):
    expiry_status = serializers.SerializerMethodField()
    expiry_status_display = serializers.SerializerMethodField()
    days_to_expiry = serializers.SerializerMethodField()
    file = serializers.FileField(write_only=True, required=False, allow_empty_file=False)
    file_url = serializers.SerializerMethodField()

    def get_expiry_status(self, obj):
        return certificate_expiry(obj.expires_on)["expiry_status"]

    def get_expiry_status_display(self, obj):
        return certificate_expiry(obj.expires_on)["expiry_status_display"]

    def get_days_to_expiry(self, obj):
        return certificate_expiry(obj.expires_on)["days_to_expiry"]

    def get_file_url(self, obj):
        return protected_media_url(obj.file)

    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = ProductCertificate
        fields = [
            "id", "created_at", "updated_at", "product", "name", "certificate_no", "issuer",
            "issued_date", "expires_on", "file", "file_url", "notes",
            "expiry_status", "expiry_status_display", "days_to_expiry", "product_name",
        ]
        read_only_fields = ["file_url", "expiry_status", "expiry_status_display", "days_to_expiry", "product_name"]

    def validate(self, attrs):
        # Do not silently accept a legacy external URL from old clients. A
        # certificate file must be uploaded into ERP private storage instead.
        legacy_url = self.initial_data.get("file_url") if hasattr(self, "initial_data") else None
        if str(legacy_url or "").strip():
            raise serializers.ValidationError({"file_url": "证书文件必须上传到 ERP 私有存储，不接受外部链接。"})
        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if not user_can(serializer_user(self.context), "products", "view"):
            data.update(product=None, product_name="")
        return data


class QuoteImportantNoteSerializer(serializers.ModelSerializer):
    source_quote_no = serializers.CharField(source="source_quote.quote_no", read_only=True)
    source_revision_no = serializers.IntegerField(source="source_quote.revision_no", read_only=True)
    created_by_name = serializers.SerializerMethodField()
    deactivated_by_name = serializers.SerializerMethodField()

    class Meta:
        model = QuoteImportantNote
        fields = ["id", "content", "is_active", "source_quote_no", "source_revision_no", "created_by_name", "created_at", "deactivated_at", "deactivated_by_name"]
        read_only_fields = ["is_active", "source_quote_no", "source_revision_no", "created_by_name", "created_at", "deactivated_at", "deactivated_by_name"]

    def validate_content(self, value):
        return sanitize_important_note(value)

    def get_created_by_name(self, obj):
        return obj.created_by.get_username() if obj.created_by else "系统"

    def get_deactivated_by_name(self, obj):
        if not obj.deactivated_at:
            return ""
        return obj.deactivated_by.get_username() if obj.deactivated_by else "系统"


class QuoteAvailabilityPreviewInputSerializer(serializers.Serializer):
    sku_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
        max_length=200,
    )


class QuoteItemSerializer(TradeLineSerializerMixin, serializers.ModelSerializer):
    sku_code = serializers.CharField(source="sku_code_snapshot", read_only=True)
    model = serializers.CharField(source="sales_model_snapshot", read_only=True)
    product_name = serializers.CharField(source="product_name_snapshot", read_only=True)
    display_name_snapshot = serializers.CharField(source="product_name_snapshot", read_only=True)
    unit = serializers.CharField(source="unit_snapshot", read_only=True)
    description_snapshot = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    amount = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)

    class Meta:
        model = QuoteItem
        fields = ["id", "sku", "sku_code", "sales_model_snapshot", "model", "product_name", "display_name_snapshot", "unit", "image", "quantity", "unit_price", "amount", "description", "description_snapshot", "notes", "sales_rules_snapshot"] + TRADE_FIELDS
        read_only_fields = ["sales_rules_snapshot"]

    def get_image(self, obj):
        return protected_media_url(obj.image_snapshot)

    def to_internal_value(self, data):
        data = data.copy()
        if "model" in data and "sales_model_snapshot" not in data:
            data["sales_model_snapshot"] = data["model"]
        if "description_snapshot" in data and "description" not in data:
            data["description"] = data["description_snapshot"]
        return super().to_internal_value(data)

    def get_description_snapshot(self, obj):
        return obj.description

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if not user_can(serializer_user(self.context), "skus", "view"):
            for field in ("sku", "sku_code", "sales_model_snapshot", "model", "product_name", "display_name_snapshot", "unit", "image"):
                data[field] = None if field == "sku" else ""
        return data


def validate_sales_exchange_rate(attrs, source=None):
    currency = attrs.get("currency", getattr(source, "currency", "USD"))
    rate = attrs.get("exchange_rate", getattr(source, "exchange_rate", None))
    if source is None and rate is None:
        rate = Decimal("1") if currency == "CNY" else Decimal("7.2") if currency == "USD" else None
        if rate is not None:
            attrs["exchange_rate"] = rate
    if rate is None or rate <= 0:
        raise serializers.ValidationError({"exchange_rate": "请输入大于 0 的对人民币汇率。"})
    if currency == "CNY" and rate != Decimal("1"):
        raise serializers.ValidationError({"exchange_rate": "人民币单据的对人民币汇率必须为 1。"})


class QuoteSerializer(serializers.ModelSerializer):
    items = QuoteItemSerializer(many=True)
    buyer_tax_id = serializers.CharField(max_length=200, allow_blank=True, allow_null=True, required=False, trim_whitespace=False)
    # Lists and relationship filters must follow the live customer master record.
    # The immutable buyer_company_name remains available for PI/export snapshots.
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    total_amount = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    root_quote_no = serializers.SerializerMethodField()
    revision_label = serializers.SerializerMethodField()
    parent_quote_no = serializers.SerializerMethodField()
    can_revise_buyer_tax_id = serializers.SerializerMethodField()

    def get_can_revise_buyer_tax_id(self, obj):
        user = serializer_user(self.context)
        if not user_can(user, "customers", "view") or not user_can(user, "quotes", "update"):
            return False
        from .quote_draft_tax import can_revise_draft_tax
        return can_revise_draft_tax(obj.pk)

    class Meta:
        model = Quote
        fields = "__all__"
        read_only_fields = ["quote_no", "root_quote", "parent_quote", "revision_no", "revision_summary", "buyer_company_name", "buyer_country_snapshot"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data.pop("amount_calculation_version", None)
        data.pop("pi_template_snapshots", None)
        if not user_can(serializer_user(self.context), "customers", "view"):
            data.update(
                customer=None, customer_name="", buyer_company_name="", recipient_name="",
                buyer_address="", buyer_email="", buyer_phone="", buyer_country_snapshot=None, buyer_tax_id=None,
            )
        return data

    def validate(self, attrs):
        source = self.instance
        view = self.context.get('view')
        if source is None and view and getattr(view, 'action', '') == 'revise':
            source = view.get_object()
        if "buyer_tax_id" in attrs:
            tax_id = attrs["buyer_tax_id"]
            raw_tax_id = self.initial_data.get("buyer_tax_id")
            if raw_tax_id is not None and not isinstance(raw_tax_id, str):
                raise serializers.ValidationError({"buyer_tax_id": "税号必须为文本。"})
            if source is None and tax_id is None:
                raise serializers.ValidationError({"buyer_tax_id": "新报价未填写税号时请留空。"})
            if tax_id and tax_id.startswith("="):
                raise serializers.ValidationError({"buyer_tax_id": "税号不能以等号开头。"})
        from .sales_scope import customer_in_scope
        request = self.context.get("request")
        customer = attrs.get("customer", source.customer if source else None)
        if request and customer and not user_can(request.user, "customers", "view"):
            raise PermissionDenied("关联客户需要客户查看权限。")
        if request and attrs.get("items") and not user_can(request.user, "skus", "view"):
            raise PermissionDenied("报价明细需要 SKU 查看权限。")
        if request and customer and not customer_in_scope(customer.pk, request.user):
            raise PermissionDenied("所选客户不在当前账号的数据范围内。")
        validate_document_amount(attrs, source)
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
            # An explicitly blank recipient field is a saved user choice, not
            # an invitation to replace it with today's customer contact.
            validated_data.setdefault(field, value)
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

    def to_representation(self, instance):
        data = super().to_representation(instance)
        user = serializer_user(self.context)
        if not user_can(user, "skus", "view"):
            for field in ("sku", "sku_code", "sales_model", "model", "product_name", "display_name", "description", "unit"):
                data[field] = None if field == "sku" else ""
        if not user_can(user, "purchases", "view"):
            data["cost_price"] = None
        if self.context.get("mask_quantity_adjustment_financial"):
            data["unit_price"] = None
            data["amount"] = None
        if not user_can(user, "suppliers", "view"):
            for field in ("supplier_sku", "supplier_name", "supplier_model", "supplier_sku_code", "supplier_barcode", "supplier_allocation"):
                data[field] = None if field in {"supplier_sku", "supplier_allocation"} else ""
        elif not user_can(user, "purchases", "view"):
            data["supplier_allocation"] = None
        return data


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
    receivable_state = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = "__all__"
        read_only_fields = [
            "order_no", "status", "cancelled_at", "cancellation_reason",
            "quantity_change_version",
            "customer_name_snapshot", "customer_country_snapshot",
            "customer_address_snapshot", "customer_contact_name_snapshot",
            "customer_phone_snapshot", "customer_email_snapshot",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data.pop("amount_calculation_version", None)
        user = serializer_user(self.context)
        data['effective_party'] = None
        from .sales_scope import customer_in_scope
        if user_can(user, 'customers', 'view') and customer_in_scope(instance.customer_id, user) and instance.status != 'draft':
            from .party_document_version import effective_snapshot
            try:
                data['effective_party'] = effective_snapshot(instance)
            except DjangoValidationError as exc:
                raise serializers.ValidationError({'effective_party': exc.messages}) from exc
        if not user_can(user, "customers", "view"):
            data.update(
                customer=None,
                customer_name="",
                customer_country="",
                customer_name_snapshot="",
                customer_country_snapshot="",
                customer_address_snapshot="",
                customer_contact_name_snapshot="",
                customer_phone_snapshot="",
                customer_email_snapshot="",
            )
        if not user_can(user, "quotes", "view"):
            data.update(quote=None, quote_no="", source_quote_no="")
        if not (user_can(user, "finance", "view") and user_can(user, "transactions", "view")):
            data["paid_amount"] = None
            data["balance_amount"] = None
        if self.context.get("mask_quantity_adjustment_financial"):
            for field in ("total_amount", "base_amount", "approved_change_amount", "paid_amount", "balance_amount", "shipping_fee", "discount", "exchange_rate"):
                data[field] = None
            data["receivable_state"] = None
        return data

    def get_receivable_state(self, obj):
        user = serializer_user(self.context)
        if not (user_can(user, "finance", "view") and user_can(user, "transactions", "view")):
            return None
        from .services.finance import order_receivable_state
        return order_receivable_state(obj, obj.payment_plans.all())["state"]

    def get_balance_amount(self, obj):
        return obj.outstanding_amount.quantize(Decimal("0.01"))

    def validate(self, attrs):
        if "order_no" in self.initial_data:
            raise serializers.ValidationError({"order_no": "订单号由系统自动生成，不能手工指定。"})
        historical_mode = bool(self.context.get("historical_mode"))
        validate_contract_edit(self.instance, attrs)
        validate_sales_exchange_rate(attrs, self.instance)
        if self.instance is None and not attrs.get("items"):
            raise serializers.ValidationError({"items": "订单至少需要一条商品明细。"})
        for item in attrs.get("items", []):
            if not historical_mode and not item["sku"].active and (self.instance is None or not self.instance.items.filter(sku=item["sku"]).exists()):
                raise serializers.ValidationError({"items": "新订单行不能选择停用或已归档的 SKU。"})
        if historical_mode and attrs.get("quote"):
            raise serializers.ValidationError({"quote": "历史销售订单不能关联正式报价单。"})
        source_quote = attrs.get("quote", getattr(self.instance, "quote", None))
        customer = attrs.get("customer", getattr(self.instance, "customer", None))
        from .sales_scope import customer_in_scope
        request = self.context.get("request")
        if request and customer and not customer_in_scope(customer.pk, request.user):
            raise PermissionDenied("所选客户不在当前账号的数据范围内。")
        if request and customer and not user_can(request.user, "customers", "view"):
            raise PermissionDenied("关联客户需要客户查看权限。")
        if request and source_quote and not customer_in_scope(source_quote.customer_id, request.user):
            raise PermissionDenied("来源报价不在当前账号的数据范围内。")
        if request and source_quote and not user_can(request.user, "quotes", "view"):
            raise PermissionDenied("关联来源报价需要报价查看权限。")
        if request and attrs.get("items") and not user_can(request.user, "skus", "view"):
            raise PermissionDenied("订单明细需要 SKU 查看权限。")
        if source_quote and customer and source_quote.customer_id != customer.id:
            raise serializers.ValidationError({"customer": "从报价创建订单时，客户必须与来源报价一致。"})
        # A terminal quote is historical context only.  It cannot seed a new
        # order or replace the source quote of an existing draft order.
        quote_is_being_bound = self.instance is None or "quote" in attrs
        if quote_is_being_bound and source_quote and source_quote.status in {"rejected", "expired"}:
            raise serializers.ValidationError({"quote": "该报价已拒绝或过期，请先创建新的修订版后再转为订单。"})
        if request and not user_can(request.user, "purchases", "update") and not historical_mode:
            persisted_costs = {
                row.sku_id: row.cost_price
                for row in self.instance.items.all()
            } if self.instance else {}
            for item in attrs.get("items", []):
                # Order cost is a server-owned snapshot unless the caller has
                # explicit purchasing write access. Preserve historical costs
                # on edits and use the current SKU cost only for new lines.
                item["cost_price"] = persisted_costs.get(item["sku"].pk, item["sku"].cost_price)
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
            "deposit_ratio", "trading_terms", "shipping_details", "buyer_company_name", "buyer_country_snapshot", "buyer_tax_id",
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
            status="draft",
            pi_template_snapshots=source_quote.pi_template_snapshots,
            **revision_values,
        )
        from .quote_party_approval_guard import inherit_quote_details
        inherit_quote_details(source_quote, revision)
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
        revision.status = 'accepted'
        revision.save(update_fields=['status'])
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
        historical_mode = bool(self.context.get("historical_mode"))
        # Draft creation deliberately has no lifecycle side effects.  Quote
        # acceptance/revision, reservations and payment plans occur only in
        # order_lifecycle.confirm_order().
        validated_data.pop("status", None)
        validated_data.pop("order_no", None)
        if historical_mode:
            validated_data["quote"] = None
            validated_data["status"] = "historical"
            validated_data["historical_only"] = True
        order = Order.objects.create(order_no=allocate_order_no(), **validated_data)
        source_items = list(order.quote.items.order_by("id")) if order.quote_id else []
        rows = []
        for index, item in enumerate(items):
            # A historical entry has no reliable point-in-time procurement
            # cost.  Keep the model's neutral default instead of silently
            # copying today's SKU cost into a past order.  Historical reports
            # already keep profit unavailable for this scope.
            if not historical_mode and not item.get("cost_price"):
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
                if not (instance.historical_only or instance.status == "historical") and not item.get("cost_price"):
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
    rmb_amount = serializers.SerializerMethodField(label="账面人民币折算参考", help_text="保留既有折算值，含原币为CNY的流水；不代表银行实际到账或结汇结果。")
    allocation_capacity = serializers.DecimalField(max_digits=14, decimal_places=4, read_only=True)
    unallocated_amount = serializers.SerializerMethodField()
    remitted_amount_display = serializers.SerializerMethodField()
    fee_evidence_name = serializers.SerializerMethodField()
    fee_evidence_sha256 = serializers.SerializerMethodField()
    cash_settlements = serializers.SerializerMethodField()
    writeoffs = serializers.SerializerMethodField()
    receipt_adjustments = serializers.JSONField(write_only=True, required=False)
    plan_allocations = serializers.JSONField(write_only=True, required=False)
    receipt_adjustment_rows = serializers.SerializerMethodField()
    fx_available_amount = serializers.SerializerMethodField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        initial = getattr(self, "initial_data", {})
        if initial.get("kind") == "customer_receipt" and (
            "receipt_adjustments" in initial or "plan_allocations" in initial
            or (not initial.get("order") and not initial.get("plan"))
        ):
            self.fields["transaction_no"].validators = []

    class Meta:
        model = Transaction
        fields = "__all__"
        extra_kwargs = {"transaction_no": {"required": False}}
        read_only_fields = ["status", "allocated_amount", "split_from", "voided_at", "void_reason", "settlement_amount", "request_hash", "reference_rate_missing"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        user = serializer_user(self.context)
        if not user_can(user, "customers", "view"):
            data.update(customer=None, customer_name="")
        if not user_can(user, "orders", "view"):
            data.update(order=None, order_no="")
        if not user_can(user, "purchases", "view"):
            data.update(purchase_order=None, purchase_no="")
        if not user_can(user, "suppliers", "view"):
            data.update(supplier=None, supplier_name="")
        if not user_can(user, "finance", "view"):
            data["plan"] = None
            data["allocations"] = []
            data["allocated_amount"] = None
            data["cash_settlements"] = []
        else:
            from .finance_scope import scope_plan_queryset
            plan_ids = {row["plan"] for row in data.get("allocations", [])}
            if instance.plan_id:
                plan_ids.add(instance.plan_id)
            visible_plan_cache = self.context.setdefault("_visible_finance_plan_ids", {})
            unresolved_ids = plan_ids - visible_plan_cache.keys()
            if unresolved_ids:
                visible_ids = set(scope_plan_queryset(
                    PaymentPlan.objects.filter(pk__in=unresolved_ids), user,
                ).values_list("pk", flat=True))
                visible_plan_cache.update({plan_id: plan_id in visible_ids for plan_id in unresolved_ids})
            visible_plan_ids = {plan_id for plan_id in plan_ids if visible_plan_cache.get(plan_id, False)}
            if instance.plan_id not in visible_plan_ids:
                data["plan"] = None
            data["allocations"] = [row for row in data.get("allocations", []) if row["plan"] in visible_plan_ids]
        return data

    def get_allocations(self, obj):
        allocations = getattr(obj, "_prefetched_objects_cache", {}).get("allocations")
        if allocations is None:
            allocations = obj.allocations.select_related("plan__order", "plan__purchase_order")
        rows = [{
            "id": row.id,
            "plan": row.plan_id,
            "contract_no": row.plan.order.order_no if row.plan.order_id else row.plan.purchase_order.purchase_no,
            "order": row.plan.order_id,
            "purchase_order": row.plan.purchase_order_id,
            "amount": row.amount,
            "remaining_amount": row.plan.remaining_amount,
            "is_active": row.is_active,
        } for row in allocations]
        if obj.plan_id and obj.kind in {"customer_receipt", "supplier_payment"}:
            plan = obj.plan
            rows.append({
                "id": f"plan-{obj.pk}", "plan": plan.pk,
                "contract_no": plan.order.order_no if plan.order_id else plan.purchase_order.purchase_no,
                "order": plan.order_id, "purchase_order": plan.purchase_order_id,
                "amount": obj.settlement_amount or obj.amount,
                "remaining_amount": plan.remaining_amount, "is_active": obj.status == "confirmed",
            })
        return rows

    def get_unallocated_amount(self, obj):
        if obj.kind not in {"unallocated_advance", "unallocated_payment"} and not (obj.kind == "customer_receipt" and not obj.plan_id and not obj.order_id):
            return Decimal("0")
        return obj.unallocated_cash_amount

    def get_fx_available_amount(self, obj):
        if obj.kind != "customer_receipt" or obj.direction != "income" or obj.status != "confirmed":
            return Decimal("0")
        from .services.cash_events import available
        return available(obj)

    def get_receipt_adjustment_rows(self, obj):
        user = serializer_user(self.context)
        if not user_can(user, "finance", "view"):
            return []
        from .finance_scope import scope_plan_queryset
        rows = list(obj.receipt_adjustments.select_related("order", "plan__order", "evidence", "contract_change").order_by("pk"))
        plans = {row.plan_id for row in rows if row.plan_id}
        visible_plans = set(scope_plan_queryset(PaymentPlan.objects.filter(pk__in=plans), user).values_list("pk", flat=True)) if plans else set()
        can_orders = user_can(user, "orders", "view")
        from .sales_scope import scope_customer_related_queryset
        order_ids = {row.order_id for row in rows if row.order_id}
        visible_orders = set(scope_customer_related_queryset(Order.objects.filter(pk__in=order_ids), user).values_list("pk", flat=True)) if can_orders and order_ids else set()
        return [{"id": row.pk, "nature": row.nature, "handling": row.handling, "amount": str(row.amount),
                 "currency": row.currency, "reason": row.reason, "order": row.order_id if row.order_id in visible_orders else None,
                 "plan": row.plan_id if row.plan_id in visible_plans else None,
                 "contract_no": row.order.order_no if row.order_id in visible_orders else (row.plan.order.order_no if row.plan_id in visible_plans else ""),
                 "evidence": row.evidence_id, "evidence_name": row.evidence.original_name if row.evidence_id else "",
                 "contract_change": row.contract_change_id if row.order_id in visible_orders else None, "writeoff": row.writeoff_id,
                 "actor": row.actor, "created_at": row.created_at}
                for row in rows]

    def get_rmb_amount(self, obj):
        value = obj.rmb_reference_amount
        return value.quantize(Decimal("0.0001")) if value is not None else None

    def get_remitted_amount_display(self, obj):
        return obj.remittance_amount if obj.remittance_amount is not None else obj.amount

    def get_fee_evidence_name(self, obj):
        return obj.fee_evidence.original_name if obj.fee_evidence_id else ""

    def get_fee_evidence_sha256(self, obj):
        return obj.fee_evidence.sha256 if obj.fee_evidence_id else ""

    def get_cash_settlements(self, obj):
        from .models import CashSourceAllocation
        from .services.cash_events import visible

        user = serializer_user(self.context)
        if not user_can(user, "finance", "view"):
            return []
        rows = CashSourceAllocation.objects.filter(source=obj).select_related("event").order_by("event__bank_date", "event_id")
        result = []
        for row in rows:
            event = row.event
            if not visible(event, user):
                continue
            source_allocations = event.sources.select_related("source").all()
            reference_amount = Decimal("0")
            for item in source_allocations:
                rate = item.source_snapshot.get("exchange_rate")
                if rate in (None, "", "None") or item.source_snapshot.get("reference_rate_missing"):
                    reference_amount = None
                    break
                reference_amount += item.amount * Decimal(rate)
            if reference_amount is not None:
                reference_amount = reference_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            gross = event.gross_rmb_amount or event.bank_net_amount + event.fee_amount
            quoted_reference = (event.amount * event.quoted_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if event.quoted_rate is not None else None
            result.append({
                "id": row.event_id,
                "event_no": event.event_no,
                "bank_date": event.bank_date,
                "amount": str(row.amount),
                "currency": row.currency,
                "gross_rmb_amount": str(gross),
                "bank_net_amount": str(event.bank_net_amount),
                "fee_amount": str(event.fee_amount),
                "actual_rate": str(event.actual_rate),
                "quoted_rate": str(event.quoted_rate) if event.quoted_rate is not None else None,
                "quoted_reference_delta": str((gross - quoted_reference).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)) if quoted_reference is not None else None,
                "pre_fee_reference_delta": str((gross - reference_amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)) if reference_amount is not None else None,
                "status": event.status,
            })
        return result

    def get_writeoffs(self, obj):
        if not user_can(serializer_user(self.context), "finance", "view"):
            return []
        rows = FinancePlanWriteoff.objects.filter(source_transaction=obj).select_related("plan__order").order_by("created_at", "pk")
        return [{
            "id": row.pk,
            "plan": row.plan_id,
            "contract_no": row.plan.order.order_no,
            "amount": str(row.amount),
            "reason": row.reason,
            "confirmed_actor": row.confirmed_actor,
            "corrected_amount": str((row.corrections.aggregate(total=Sum("amount"))["total"] or Decimal("0")).quantize(Decimal("0.0001"))),
            "corrections": [{"id": correction.pk, "amount": str(correction.amount), "reason": correction.reason,
                "actor": correction.actor, "created_at": correction.created_at}
                for correction in row.corrections.order_by("created_at", "pk")],
            "created_at": row.created_at,
        } for row in rows]

    def validate(self, attrs):
        request = self.context.get("request")
        if request:
            validate_finance_relations(attrs, request.user, self.instance)
        kind = attrs.get("kind", getattr(self.instance, "kind", "other"))
        initial = getattr(self, "initial_data", {})
        if kind != "customer_receipt" and ("receipt_adjustments" in initial or "plan_allocations" in initial):
            raise serializers.ValidationError("收款扣减和应收分配仅适用于客户收款。")
        structured = kind == "customer_receipt" and ("receipt_adjustments" in initial or "plan_allocations" in initial or (not initial.get("order") and not initial.get("plan")))
        if structured:
            if attrs.get("plan"):
                raise serializers.ValidationError({"plan": "请在核销分配明细中选择应收计划。"})
            order = attrs.get("order")
            if order and "currency" not in initial:
                attrs["currency"] = order.currency
            if attrs.get("currency", "USD") != "CNY" and initial.get("exchange_rate") in (None, ""):
                attrs["exchange_rate"] = None
                attrs["reference_rate_missing"] = True
        for field in ("amount", "exchange_rate"):
            value = attrs.get(field, getattr(self.instance, field, Decimal("1")))
            if field == "exchange_rate" and value is None and structured and attrs.get("reference_rate_missing"):
                continue
            if value is None or value <= 0:
                raise serializers.ValidationError({field: "必须大于零。"})
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
        if structured:
            if not customer and not order:
                raise serializers.ValidationError({"customer": "客户收款请选择客户；可暂不关联订单。"})
            if any(attrs.get(field) not in (None, "", Decimal("0")) for field in ("bank_fee_amount", "fee_responsibility", "fee_reason", "fee_evidence")):
                raise serializers.ValidationError({"receipt_adjustments": "请在扣减明细中逐条登记手续费。"})
        elif kind in {"customer_receipt", "unallocated_advance"} and direction == "income":
            actual = attrs.get("amount", getattr(self.instance, "amount", Decimal("0")))
            remitted = attrs.get("remittance_amount", getattr(self.instance, "remittance_amount", None))
            remitted = actual if remitted is None else remitted
            fee = attrs.get("bank_fee_amount", getattr(self.instance, "bank_fee_amount", Decimal("0")))
            responsibility = attrs.get("fee_responsibility", getattr(self.instance, "fee_responsibility", ""))
            evidence = attrs.get("fee_evidence", getattr(self.instance, "fee_evidence", None))
            reason = str(attrs.get("fee_reason", getattr(self.instance, "fee_reason", "")) or "").strip()
            if remitted < actual or remitted - actual != fee:
                raise serializers.ValidationError("客户汇款额减银行实际到账额必须等于扣费金额。")
            if fee > 0:
                if responsibility not in {"company", "customer", "unknown"} or len(reason) < 5:
                    raise serializers.ValidationError("有银行扣费时，请记录承担方和扣费依据。")
                if evidence is None or evidence.scope != "transaction":
                    raise serializers.ValidationError("有银行扣费时，请上传并关联收款凭证。")
                from .services.finance_closeout import voucher as checked_voucher
                try:
                    checked_voucher(evidence.pk, scope="transaction")
                except Exception as exc:
                    raise serializers.ValidationError({"fee_evidence": str(exc)})
            elif responsibility or reason or evidence:
                raise serializers.ValidationError("没有扣费时无需填写扣费承担方、依据或凭证。")
            attrs["remittance_amount"] = remitted
        elif any(attrs.get(field) not in (None, "", Decimal("0")) for field in ("bank_fee_amount", "fee_responsibility", "fee_reason", "fee_evidence")):
            raise serializers.ValidationError("客户汇款扣费仅支持登记在客户收款或未分配预收款上。")
        if kind in {"unallocated_advance", "unallocated_payment"}:
            if order or purchase_order or attrs.get("plan"):
                raise serializers.ValidationError("未分配预收预付请只选择往来方，之后再核销计划。")
            if not (customer if direction == "income" else supplier):
                raise serializers.ValidationError("预收款请选择客户，预付款请选择供应商。")
        contract = order or purchase_order
        plan = attrs.get("plan", getattr(self.instance, "plan", None))
        if plan and not contract:
            contract = plan.order or plan.purchase_order
        if contract and (getattr(contract, "historical_only", False) or getattr(contract, "status", None) == "historical"):
            from .services.historical import has_verified_history_balance
            if not plan or not has_verified_history_balance(contract):
                raise serializers.ValidationError("历史订单尚无已核实的未结计划，不能登记关联资金流水。")
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
    writeoff_amount = serializers.SerializerMethodField()

    class Meta:
        model = PaymentPlan
        fields = "__all__"
        read_only_fields = ["settled_amount", "status"]

    def get_writeoff_amount(self, obj):
        written = obj.finance_writeoffs.aggregate(total=Sum("amount"))["total"] or Decimal("0")
        corrected = sum((row.amount for writeoff in obj.finance_writeoffs.all() for row in writeoff.corrections.all()), Decimal("0"))
        return written - corrected

    def to_representation(self, instance):
        data = super().to_representation(instance)
        user = serializer_user(self.context)
        if instance.order_id:
            if not user_can(user, "customers", "view"):
                data["customer_id"] = None
                data["counterparty_name"] = ""
            if not user_can(user, "orders", "view"):
                data["contract_no"] = ""
        else:
            if not user_can(user, "suppliers", "view"):
                data["supplier_id"] = None
                data["counterparty_name"] = ""
            if not user_can(user, "purchases", "view"):
                data["contract_no"] = ""
        return data

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
        request = self.context.get("request")
        if request:
            validate_finance_relations(attrs, request.user, self.instance)
        values = {field: attrs.get(field, getattr(self.instance, field, None)) for field in ("order", "purchase_order", "direction", "currency", "planned_amount")}
        order, purchase = values["order"], values["purchase_order"]
        if bool(order) == bool(purchase):
            raise serializers.ValidationError("计划必须且只能关联一个合同。")
        contract = order or purchase
        if getattr(contract, "historical_only", False) or getattr(contract, "status", None) == "historical":
            raise serializers.ValidationError("历史订单仅用于经营分析，不能建立收付款计划。")
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
        request = self.context.get("request")
        if request:
            validate_finance_relations(attrs, request.user, self.instance)
        if self.instance and self.instance.status != "pending":
            raise serializers.ValidationError("已处理的合同变更不能修改。")
        order = attrs.get("order", getattr(self.instance, "order", None))
        purchase = attrs.get("purchase_order", getattr(self.instance, "purchase_order", None))
        if request:
            from .finance_scope import require_finance_permission
            require_finance_permission(request.user, "orders" if order else "purchases", "update" if self.instance else "create")
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

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if not user_can(serializer_user(self.context), "suppliers", "view"):
            data.update(supplier=None, supplier_name="")
        return data

    def validate(self, attrs):
        supplier = attrs.get("supplier", getattr(self.instance, "supplier", None))
        if supplier and not user_can(serializer_user(self.context), "suppliers", "view"):
            raise PermissionDenied("关联供应商需要供应商查看权限。")
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

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if not user_can(serializer_user(self.context), "skus", "view"):
            data.update(sku=None, sku_code="", product_name="", effective_packaging=None)
        elif not user_can(serializer_user(self.context), "products", "view"):
            data["product_name"] = ""
        return data

    def validate(self, attrs):
        user = serializer_user(self.context)
        if ("sku" in attrs or self.instance is None) and user is not None and not user_can(user, "skus", "view"):
            raise PermissionDenied("SKU 包装配置需要 SKU 查看权限。")
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


def _trade_snapshot_semantics(snapshot):
    """Return the immutable unit semantics needed for actual packing.

    ``TradeUnitLine`` snapshots intentionally preserve only the values which
    describe the conversion and split rule.  The display name is not part of
    that meaning, while catalog lifecycle/supplier fields are not persisted
    in this snapshot at all.  Incomplete or malformed historical data must
    remain ambiguous rather than being reconstructed from the current SKU.
    """
    if not isinstance(snapshot, dict):
        return None
    raw_factor = snapshot.get("factor")
    if raw_factor is None or raw_factor == "":
        return None
    try:
        factor = Decimal(str(raw_factor))
    except (TypeError, ValueError, ArithmeticError):
        return None
    if not factor.is_finite() or factor <= Decimal("0"):
        return None
    base_unit = snapshot.get("base_unit")
    unit = snapshot.get("unit")
    allow_fraction = snapshot.get("allow_fraction")
    if (
        not isinstance(base_unit, str)
        or not base_unit.strip()
        or not isinstance(unit, str)
        or not unit.strip()
        or not isinstance(allow_fraction, bool)
    ):
        return None
    return factor, base_unit, unit, allow_fraction


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
        # A package line is entered in the SKU base unit, so only enforce an
        # indivisible trade unit when every shipment line for that SKU carries
        # the same explicit trade-unit snapshot.  A base-unit order line,
        # an incomplete/invalid snapshot, or conflicting historical snapshots
        # makes the physical package quantity ambiguous; in those cases do
        # not invent a carton restriction.  A valid fractional snapshot is
        # still a known semantic and remains unrestricted.
        snapshot_semantics = {}
        ambiguous_indivisible = set()
        for shipment_item in shipment.items.all():
            sku_id = shipment_item.sku_id
            snapshot = shipment_item.trade_snapshot
            if not shipment_item.trade_unit_id:
                ambiguous_indivisible.add(sku_id)
                continue
            semantics = _trade_snapshot_semantics(snapshot)
            if semantics is None:
                ambiguous_indivisible.add(sku_id)
                continue
            previous = snapshot_semantics.get(sku_id)
            if previous is not None and previous != semantics:
                ambiguous_indivisible.add(sku_id)
            else:
                snapshot_semantics[sku_id] = semantics
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
            if sku_id in snapshot_semantics and sku_id not in ambiguous_indivisible:
                factor, base_unit, _unit, allow_fraction = snapshot_semantics[sku_id]
                if not allow_fraction and quantity % factor:
                    factor_text = format(factor.normalize(), "f")
                    quantity_text = format(quantity.normalize(), "f")
                    raise serializers.ValidationError({
                        "items": f"SKU {item['sku'].sku} 按不可拆分的 {factor_text} {base_unit} 交易单位装箱，数量必须是其整数倍；当前为 {quantity_text}。"
                    })
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
    order_no = serializers.SerializerMethodField()
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

    def _visible_sales_orders(self, obj):
        if hasattr(obj, "_visible_sales_orders_cache"):
            return obj._visible_sales_orders_cache
        from .sales_scope import scope_customer_related_queryset

        user = self.context.get("user")
        if user is None:
            request = self.context.get("request")
            user = getattr(request, "user", None)
        if user is None:
            # Nested serializers are used from several context builders. With
            # no request identity they must not expose sales links by default.
            obj._visible_sales_orders_cache = []
            return obj._visible_sales_orders_cache
        from .permissions import user_can

        if not user_can(user, "orders", "view"):
            obj._visible_sales_orders_cache = []
            return obj._visible_sales_orders_cache
        associated = obj.related_orders.all()
        if obj.order_id:
            associated = Order.objects.filter(Q(pk=obj.order_id) | Q(pk__in=associated.values("pk")))
        obj._visible_sales_orders_cache = list(scope_customer_related_queryset(associated, user).distinct())
        return obj._visible_sales_orders_cache

    def get_order_no(self, obj):
        visible_ids = {order.pk for order in self._visible_sales_orders(obj)}
        return obj.order.order_no if obj.order_id in visible_ids else ""

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
        user = serializer_user(self.context)
        unit_cost = attrs.get("unit_cost", getattr(self.instance, "unit_cost", Decimal("0")))
        if unit_cost and user is not None and not user_can(user, "purchases", "update"):
            current_cost = self.instance.unit_cost if self.instance else Decimal("0")
            if unit_cost != current_cost:
                raise PermissionDenied("修改库存成本需要采购修改权限。")
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
        from .procurement_scope import require_order_writes
        related_order_ids = [row.pk for row in orders]
        if self.instance:
            related_order_ids.extend(self.instance.related_orders.values_list("pk", flat=True))
            related_order_ids.append(self.instance.order_id)
        require_order_writes(serializer_user(self.context), related_order_ids)
        if supplier_sku and not user_can(serializer_user(self.context), "suppliers", "view"):
            raise PermissionDenied("关联供应商来源需要供应商查看权限。")
        if sku and orders and not any(related_order.items.filter(sku=sku).exists() for related_order in orders):
            raise serializers.ValidationError("选择的 SKU 不在任一关联订单明细中。")
        if supplier_sku and sku and supplier_sku.sku_id != sku.pk:
            raise serializers.ValidationError("供应商来源必须对应当前库存流水 SKU。")
        return attrs

    def get_related_order_nos(self, instance):
        return [order.order_no for order in self._visible_sales_orders(instance)]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        user = serializer_user(self.context)
        if not user_can(user, "suppliers", "view"):
            data["supplier_sku"] = None
        if not user_can(user, "purchases", "view"):
            data["unit_cost"] = None
        visible_ids = {order.pk for order in self._visible_sales_orders(instance)}
        if data.get("order") not in visible_ids:
            data["order"] = None
        data["related_orders"] = [order_id for order_id in (data.get("related_orders") or []) if order_id in visible_ids]
        return data

    def check_stock(self, sku, delta):
        from .services.fulfillment import sku_metrics
        SKU.objects.select_for_update().get(pk=sku.pk)
        if delta < 0 and sku_metrics(sku)["available_quantity"] + delta < 0:
            raise serializers.ValidationError("可用库存不足，不能扣减或占用订单已预留的库存。")

    @transaction.atomic
    def create(self, validated_data):
        from .services.fulfillment import OUTGOING_MOVEMENT_TYPES, inventory_location, validate_inventory_location_change
        delta = validated_data["quantity"] * (-1 if validated_data["type"] in OUTGOING_MOVEMENT_TYPES else 1)
        self.check_stock(validated_data["sku"], delta)
        try:
            location = inventory_location(validated_data["sku"], validated_data)
            validate_inventory_location_change(validated_data["sku"], location, delta)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc
        validated_data.update(location)
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
        from .services.fulfillment import validate_inventory_location_change
        from .models import HistoryInventoryBaseline
        instance = InventoryMovement.objects.select_for_update().get(pk=instance.pk)
        if HistoryInventoryBaseline.objects.filter(sku=instance.sku, reversal__isnull=True).exists() and any(key in validated_data and validated_data[key] != getattr(instance, key) for key in ("warehouse", "warehouse_type", "lot_reference")):
            raise serializers.ValidationError("库存流水不能变更仓库或批次，请使用调整流水纠正。")
        quantity = validated_data.get("quantity", instance.quantity)
        sign = -1 if instance.signed_quantity < 0 else 1
        delta = (quantity - instance.quantity) * sign
        self.check_stock(instance.sku, delta)
        location = {key: validated_data.get(key, getattr(instance, key)) for key in ("warehouse", "warehouse_type", "lot_reference")}
        try:
            validate_inventory_location_change(instance.sku, location, quantity * sign, original=instance)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc
        related_orders = validated_data.pop("related_orders", None)
        if related_orders is not None:
            validated_data["order"] = related_orders[0] if related_orders else None
        instance = super().update(instance, validated_data)
        if related_orders is not None:
            instance.related_orders.set(related_orders)
        from .services.fulfillment import rebalance_sku_reservations
        rebalance_sku_reservations(instance.sku)
        return instance
