from .trade_units import TradeLineSerializerMixin, TRADE_FIELDS, SKUTradeUnitSerializer, trade_values, validate_document_amount
from decimal import Decimal
import re
from uuid import uuid4

import bleach

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Q
from django.utils.html import strip_tags
from rest_framework import serializers

from .models import AccessRole, CategoryAttribute, Contact, ContractChangeRequest, Customer, CustomerCodeSequence, EmployeeProfile, FollowUp, FollowUpAttachment, HSCode, InventoryMovement, OperationLog, Order, OrderItem, OrganizationUnit, PackagingTemplate, PackingPlan, PackingPlanCarton, PackingPlanCartonItem, PaymentPlan, Position, Product, ProductCategory, ProductCertificate, ProductCodeSequence, ProductParameter, PurchaseOrder, PurchaseOrderItem, Quote, QuoteImportantNote, QuoteItem, RolePermission, Shipment, ShipmentPackage, ShipmentPackageItem, SKUPackagingProfile, SKU, SKUVersion, Supplier, SupplierSKU, Transaction
from .quote_numbers import allocate_revision_quote_no, allocate_root_quote_no
from .quote_snapshots import create_quote_items
from .sku_identity import build_sku_identity, category_attributes, complete_sales_model_abbreviations, identity_conflict_messages, identity_signature, normalize_display_name, normalize_sales_model_abbreviations, parameter_pairs, raw_parameter_value
from .sku_numbers import allocate_sku_code


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

    class Meta:
        model = PurchaseOrderItem
        fields = ["id", "sku", "supplier_sku", "sku_code", "display_name", "sales_model", "supplier_name", "supplier_model", "supplier_sku_code", "supplier_barcode", "supplier_characteristics_snapshot", "quantity", "unit_price", "received_quantity", "remaining_quantity", "amount"] + TRADE_FIELDS
        read_only_fields = ["supplier_characteristics_snapshot"]


def validate_contract_edit(instance, attrs, *, purchase=False):
    validate_document_amount(attrs, instance)
    if instance and purchase and instance.cost_allocation_version and any(key in attrs for key in ("items", "currency", "exchange_rate", "order", "supplier")):
        raise serializers.ValidationError("采购单已有成本分配，不能改写明细、币种、汇率或原始归属；请通过成本分配调整归属。")
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
    if not purchase:
        sensitive.add("tail_goods_policy")
    def normalized_item_signature(item):
        def related_id(value):
            return value.pk if hasattr(value, "pk") else value

        return (
            related_id(item["sku"]),
            related_id(item.get("supplier_sku")),
            Decimal(item["quantity"]),
            Decimal(item["unit_price"]),
            Decimal(item.get("cost_price", 0)),
            item.get("notes", ""),
            related_id(item.get("trade_unit")),
            item.get("trade_quantity"),
            item.get("trade_unit_price"),
        )

    items_changed = "items" in attrs and (
        [normalized_item_signature(item) for item in attrs["items"]]
        != [
            (
                item.sku_id,
                item.supplier_sku_id,
                Decimal(item.quantity),
                Decimal(item.unit_price),
                Decimal(getattr(item, "cost_price", 0)),
                getattr(item, "notes", ""),
                item.trade_unit_id,
                item.trade_quantity,
                item.trade_unit_price,
            )
            for item in instance.items.order_by("id")
        ]
    )
    changed = items_changed or any(
        key in attrs and attrs[key] != getattr(instance, key, None)
        for key in sensitive - {"items"}
    )
    if changed and (history or financial):
        raise serializers.ValidationError("合同已有采购、出入库或收付款记录，不能改写商品、往来方及金额依据。请使用追加单或退款记录处理后续变化。")
    new_status = attrs.get("status", instance.status)
    if new_status != instance.status and new_status in {"cancelled", "draft"} and (history or financial):
        raise serializers.ValidationError("合同已有业务记录，不能直接取消或退回草稿。")
    if new_status != instance.status and new_status in ({"partial", "completed"} if purchase else {"shipped"}):
        raise serializers.ValidationError("到货、发货状态由实际出入库记录自动更新。")
    if not purchase and new_status != instance.status and new_status == "completed":
        raise serializers.ValidationError("订单完成需在订单工作台执行；系统会核验全部发货和全部回款。")


def sync_unsettled_contract_plans(instance, changed):
    from .services.finance import ensure_default_payment_plans
    if instance.status in {"draft", "cancelled"}:
        instance.payment_plans.filter(settled_amount=0).update(status="cancelled")
        return
    if changed and not instance.transactions.exists() and not instance.payment_plans.filter(advance_allocations__isnull=False).exists():
        instance.payment_plans.all().delete()
    ensure_default_payment_plans(instance)


class PurchaseOrderSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    items = PurchaseOrderItemSerializer(many=True)
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)
    order_no = serializers.CharField(source="order.order_no", read_only=True)
    total_amount = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    paid_amount = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    unpaid_amount = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = "__all__"

    def validate(self, attrs):
        validate_contract_edit(self.instance, attrs, purchase=True)
        supplier = attrs.get("supplier", getattr(self.instance, "supplier", None))
        unit_rows = attrs.get("items")
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
            if self.instance is None and not source.is_active:
                errors.append({"items": {index: {"supplier_sku": "新建采购单只能选择启用中的供应商来源。"}}})
        if errors:
            raise serializers.ValidationError(errors[0])
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        items = validated_data.pop("items")
        from .services.supplier_candidates import ensure_purchase_source
        for item in items:
            if not item["sku"].active:
                raise serializers.ValidationError({"sku": "新采购不能选择停用或已归档的 SKU。"})
            if not item.get("supplier_sku"):
                item["supplier_sku"] = ensure_purchase_source(item["sku"], validated_data["supplier"], order=validated_data.get("order"))
        purchase = PurchaseOrder.objects.create(**validated_data)
        PurchaseOrderItem.objects.bulk_create([
            PurchaseOrderItem(
                purchase_order=purchase,
                sku_code_snapshot=item["sku"].sku,
                sales_model_snapshot=item["sku"].sales_model or "",
                display_name_snapshot=item["sku"].display_name_cn or item["sku"].product.name,
                description_snapshot=item["sku"].description_en or item["sku"].description_cn or item["sku"].display_name_cn or item["sku"].product.name,
                supplier_name_snapshot=item["supplier_sku"].supplier.name if item.get("supplier_sku") else "",
                supplier_model_snapshot=item["supplier_sku"].supplier_model if item.get("supplier_sku") else "",
                supplier_sku_code_snapshot=item["supplier_sku"].supplier_sku_code if item.get("supplier_sku") else "",
                supplier_barcode_snapshot=item["supplier_sku"].supplier_barcode if item.get("supplier_sku") else "",
                supplier_characteristics_snapshot=item["supplier_sku"].characteristics if item.get("supplier_sku") else {},
                **item,
            ) for item in items
        ])
        from .services.finance import ensure_default_payment_plans
        ensure_default_payment_plans(purchase)
        return purchase

    @transaction.atomic
    def update(self, instance, validated_data):
        instance = PurchaseOrder.objects.select_for_update().get(pk=instance.pk)
        validate_contract_edit(instance, validated_data, purchase=True)
        changed = any(key in validated_data for key in ("items", "currency")) or (instance.status in {"draft", "cancelled"} and validated_data.get("status", instance.status) not in {"draft", "cancelled"})
        items = validated_data.pop("items", None)
        if items is not None:
            instance.items.all().delete()
            for item in items:
                PurchaseOrderItem.objects.create(purchase_order=instance, **item)
        for key, value in validated_data.items():
            setattr(instance, key, value)
        instance.save()
        sync_unsettled_contract_plans(instance, changed)
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
    primary_contact_email = serializers.CharField(read_only=True, default="")
    contacts = CustomerContactInputSerializer(many=True, write_only=True, required=False)

    class Meta:
        model = Customer
        fields = "__all__"
        read_only_fields = ["code"]

    def validate(self, attrs):
        if self.instance is None and not attrs.get("contacts"):
            raise serializers.ValidationError({"contacts": "新建客户时请至少填写一位联系人。"})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        contacts = validated_data.pop("contacts")
        customer = Customer.objects.create(code=allocate_customer_code(), **validated_data)
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


class FollowUpSerializer(serializers.ModelSerializer):
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
        if not attrs.get("key"):
            attrs["key"] = attrs.get("name", getattr(self.instance, "key", "")).strip()
        include_in_sku = attrs.get("include_in_sku", getattr(self.instance, "include_in_sku", False))
        include_in_sales_model = attrs.get("include_in_sales_model", getattr(self.instance, "include_in_sales_model", False))
        required = attrs.get("required", getattr(self.instance, "required", False))
        if required and not (include_in_sku or include_in_sales_model):
            raise serializers.ValidationError({"required": "开启“必填”需要先开启“生成中文SKU”或“生成销售型号”。"})
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

    def validate_sales_model_prefix(self, value):
        if value is None or not str(value).strip():
            return None
        value = str(value).strip().upper()
        if not re.fullmatch(r"[A-Z0-9]+", value):
            raise serializers.ValidationError("销售型号只能包含字母和数字，例如 BTY、COB320 或 SMD120。")
        return value

    def validate(self, attrs):
        if "hs_code" in self.initial_data:
            raise serializers.ValidationError({"hs_code": "HS 编码请通过“HS 编码维护”页面统一分配。"})
        if not self.instance and not attrs.get("sales_model_prefix"):
            raise serializers.ValidationError({"sales_model_prefix": "新建产品时必须填写销售型号。"})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        validated_data.pop("code", None)
        additional_categories = validated_data.pop("additional_categories", [])
        suppliers = validated_data.pop("suppliers", [])
        product = Product.objects.create(code=allocate_product_code(), **validated_data)
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
    historical_matches = serializers.SerializerMethodField()

    class Meta:
        model = SKU
        fields = "__all__"
        extra_kwargs = {"sku": {"required": False, "read_only": True}, "identity_signature": {"read_only": True}, "schema_version": {"read_only": True}}

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
        return super().create(validated_data)

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
            if sales_model_base:
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
        return super().update(instance, validated_data)

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
        return obj.changed_by.get_username() if obj.changed_by else "系统"


class ProductParameterSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = ProductParameter
        fields = "__all__"


class ProductCertificateSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = ProductCertificate
        fields = "__all__"


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


class QuoteItemSerializer(TradeLineSerializerMixin, serializers.ModelSerializer):
    sku_code = serializers.CharField(source="sku_code_snapshot", read_only=True)
    model = serializers.CharField(source="sales_model_snapshot", read_only=True)
    product_name = serializers.CharField(source="product_name_snapshot", read_only=True)
    display_name_snapshot = serializers.CharField(source="product_name_snapshot", read_only=True)
    unit = serializers.CharField(source="unit_snapshot", read_only=True)
    description_snapshot = serializers.SerializerMethodField()
    image = serializers.ImageField(source="image_snapshot", read_only=True)
    amount = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)

    class Meta:
        model = QuoteItem
        fields = ["id", "sku", "sku_code", "sales_model_snapshot", "model", "product_name", "display_name_snapshot", "unit", "image", "quantity", "unit_price", "amount", "description", "description_snapshot", "notes", "sales_rules_snapshot"] + TRADE_FIELDS
        read_only_fields = ["sales_rules_snapshot"]

    def to_internal_value(self, data):
        data = data.copy()
        if "model" in data and "sales_model_snapshot" not in data:
            data["sales_model_snapshot"] = data["model"]
        if "description_snapshot" in data and "description" not in data:
            data["description"] = data["description_snapshot"]
        return super().to_internal_value(data)

    def get_description_snapshot(self, obj):
        return obj.description


class QuoteSerializer(serializers.ModelSerializer):
    items = QuoteItemSerializer(many=True)
    # Lists and relationship filters must follow the live customer master record.
    # The immutable buyer_company_name remains available for PI/export snapshots.
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    total_amount = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    root_quote_no = serializers.SerializerMethodField()
    revision_label = serializers.SerializerMethodField()
    parent_quote_no = serializers.SerializerMethodField()

    class Meta:
        model = Quote
        fields = "__all__"
        read_only_fields = ["quote_no", "root_quote", "parent_quote", "revision_no", "revision_summary", "buyer_company_name"]

    def validate(self, attrs):
        source = self.instance
        view = self.context.get('view')
        if source is None and view and getattr(view, 'action', '') == 'revise':
            source = view.get_object()
        validate_document_amount(attrs, source)
        return attrs

    def get_root_quote_no(self, obj):
        return obj.root_quote.quote_no if obj.root_quote_id else obj.quote_no

    def get_revision_label(self, obj):
        return f"Revision {obj.revision_no}" if obj.revision_no else "Original"

    def get_parent_quote_no(self, obj):
        return obj.parent_quote.quote_no if obj.parent_quote_id else ""

    @transaction.atomic
    def create(self, validated_data):
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
    paid_amount = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    balance_amount = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = "__all__"

    def get_balance_amount(self, obj):
        return (obj.total_amount - obj.paid_amount).quantize(Decimal("0.01"))

    def validate(self, attrs):
        validate_contract_edit(self.instance, attrs)
        if self.instance is None and not attrs.get("items"):
            raise serializers.ValidationError({"items": "订单至少需要一条商品明细。"})
        for item in attrs.get("items", []):
            if not item["sku"].active and (self.instance is None or not self.instance.items.filter(sku=item["sku"]).exists()):
                raise serializers.ValidationError({"items": "新订单行不能选择停用或已归档的 SKU。"})
        source_quote = attrs.get("quote")
        customer = attrs.get("customer")
        if self.instance is None and source_quote and customer and source_quote.customer_id != customer.id:
            raise serializers.ValidationError({"customer": "从报价创建订单时，客户必须与来源报价一致。"})
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
        source_quote = validated_data.get("quote")
        if source_quote:
            validated_data["quote"] = self._create_quote_revision_if_needed(source_quote, validated_data, items)
        order = Order.objects.create(**validated_data)
        source_items = list(order.quote.items.order_by("id")) if order.quote_id else []
        rows = []
        for index, item in enumerate(items):
            if not item.get("cost_price"):
                item["cost_price"] = item["sku"].cost_price
            source = source_items[index] if index < len(source_items) and source_items[index].sku_id == item["sku"].pk else None
            rows.append(OrderItem(order=order, **item, **self._item_snapshots(item["sku"], source)))
        OrderItem.objects.bulk_create(rows)
        from .services.fulfillment import allocate_order
        allocate_order(order)
        from .services.finance import ensure_default_payment_plans
        ensure_default_payment_plans(order)
        if order.quote_id:
            Quote.objects.filter(pk=order.quote_id).update(status="accepted")
        return order

    @transaction.atomic
    def update(self, instance, validated_data):
        instance = Order.objects.select_for_update().get(pk=instance.pk)
        validate_contract_edit(instance, validated_data)
        items = validated_data.pop("items", None)
        previous_items = list(instance.items.order_by("id"))
        items_changed = items is not None and self._order_item_signature(items) != self._persisted_order_item_signature(previous_items)
        changed = items_changed or any(
            key in validated_data and validated_data[key] != getattr(instance, key)
            for key in ("currency", "exchange_rate", "shipping_fee", "discount")
        ) or (instance.status in {"draft", "cancelled"} and validated_data.get("status", instance.status) not in {"draft", "cancelled"})

        # The order remains an executable contract, but commercial edits must retain
        # an immutable quote version as their source of truth.  This mirrors initial
        # quote-to-order conversion and prevents the order total from silently
        # diverging from its linked quote.
        commercial_edit = items_changed or any(
            key in validated_data and validated_data[key] != getattr(instance, key)
            for key in ("currency", "exchange_rate", "shipping_fee", "discount", "notes")
        )
        if instance.quote_id and commercial_edit:
            revision_items = items if items is not None else self._existing_order_items_for_quote_revision(instance)
            revision = self._create_quote_revision_if_needed(instance.quote, validated_data, revision_items)
            if revision.pk != instance.quote_id:
                validated_data["quote"] = revision
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
        from .services.fulfillment import allocate_order
        allocate_order(instance)
        sync_unsettled_contract_plans(instance, changed)
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
        read_only_fields = ["status", "allocated_amount", "split_from"]

    def get_allocations(self, obj):
        return [{"id": row.id, "plan": row.plan_id, "contract_no": row.plan.order.order_no if row.plan.order_id else row.plan.purchase_order.purchase_no,
            "amount": row.amount, "is_active": row.is_active} for row in obj.allocations.select_related("plan__order", "plan__purchase_order")]

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
        additions = sum(contract.contract_changes.filter(status="approved").values_list("amount_delta", flat=True), Decimal("0"))
        if planned + values["planned_amount"] > contract.total_amount + additions:
            raise serializers.ValidationError("计划合计不能超过合同金额及已确认增补。调整分期比例时，请先调低原计划再调高另一笔。")
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
    class Meta:
        model = ContractChangeRequest
        fields = "__all__"
        read_only_fields = ["status"]

    def validate(self, attrs):
        if self.instance and self.instance.status != "pending":
            raise serializers.ValidationError("已处理的合同变更不能修改。")
        order = attrs.get("order", getattr(self.instance, "order", None))
        purchase = attrs.get("purchase_order", getattr(self.instance, "purchase_order", None))
        amount = attrs.get("amount_delta", getattr(self.instance, "amount_delta", Decimal("0")))
        if bool(order) == bool(purchase) or amount <= 0:
            raise serializers.ValidationError("变更必须关联一个合同，且增补金额必须大于零。")
        return attrs


class PackagingTemplateSerializer(serializers.ModelSerializer):
    cbm = serializers.DecimalField(max_digits=16, decimal_places=6, read_only=True)
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)
    linked_sku_count = serializers.IntegerField(source="sku_profiles.count", read_only=True)

    class Meta:
        model = PackagingTemplate
        fields = "__all__"
        read_only_fields = ["code"]


class SKUPackagingProfileSerializer(serializers.ModelSerializer):
    sku_code = serializers.CharField(source="sku.sku", read_only=True)
    product_name = serializers.CharField(source="sku.product.name", read_only=True)
    packaging_status = serializers.SerializerMethodField()
    effective_packaging = serializers.SerializerMethodField()

    class Meta:
        model = SKUPackagingProfile
        fields = "__all__"
        read_only_fields = ["verified_at", "verified_by"]

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

    def create(self, validated_data):
        items = validated_data.pop("items", [])
        package = ShipmentPackage.objects.create(**validated_data)
        ShipmentPackageItem.objects.bulk_create([ShipmentPackageItem(shipment_package=package, **item) for item in items])
        return package

    def update(self, instance, validated_data):
        items = validated_data.pop("items", None)
        for key, value in validated_data.items(): setattr(instance, key, value)
        instance.save()
        if items is not None:
            instance.items.all().delete()
            ShipmentPackageItem.objects.bulk_create([ShipmentPackageItem(shipment_package=instance, **item) for item in items])
        return instance

    def validate(self, attrs):
        if bool(attrs.get("order")) == bool(attrs.get("purchase_order")):
            raise serializers.ValidationError("变更单必须且只能关联一个订单或采购单。")
        return attrs


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
        if delta > 0:
            from .services.fulfillment import ACTIVE_ORDER_STATUSES, allocate_order
            for order in Order.objects.filter(status__in=ACTIVE_ORDER_STATUSES, items__sku=instance.sku).distinct().order_by("order_date", "pk"):
                allocate_order(order)
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
        return instance
