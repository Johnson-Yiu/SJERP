from decimal import Decimal

import bleach

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils.html import strip_tags
from rest_framework import serializers

from .models import AccessRole, CategoryAttribute, Contact, ContractChangeRequest, Customer, CustomerCodeSequence, EmployeeProfile, FollowUp, InventoryMovement, Order, OrderItem, OrganizationUnit, PaymentPlan, Position, Product, ProductCategory, ProductCertificate, ProductCodeSequence, ProductParameter, PurchaseOrder, PurchaseOrderItem, Quote, QuoteImportantNote, QuoteItem, RolePermission, SKU, Supplier, Transaction
from .quote_numbers import allocate_revision_quote_no, allocate_root_quote_no
from .quote_snapshots import create_quote_items


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
    purchase_count = serializers.IntegerField(source="purchase_orders.count", read_only=True)

    class Meta:
        model = Supplier
        fields = "__all__"
        read_only_fields = ["purchase_count", "created_at", "updated_at"]


class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    sku_code = serializers.CharField(source="sku.sku", read_only=True)
    received_quantity = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    remaining_quantity = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)

    class Meta:
        model = PurchaseOrderItem
        fields = ["id", "sku", "sku_code", "quantity", "unit_price", "received_quantity", "remaining_quantity"]


class PurchaseOrderSerializer(serializers.ModelSerializer):
    items = PurchaseOrderItemSerializer(many=True)
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)
    order_no = serializers.CharField(source="order.order_no", read_only=True)
    total_amount = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    paid_amount = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    unpaid_amount = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = "__all__"

    @transaction.atomic
    def create(self, validated_data):
        items = validated_data.pop("items")
        purchase = PurchaseOrder.objects.create(**validated_data)
        PurchaseOrderItem.objects.bulk_create([
            PurchaseOrderItem(purchase_order=purchase, **item) for item in items
        ])
        from .services.finance import ensure_default_payment_plans
        ensure_default_payment_plans(purchase)
        return purchase


class ReceiptInputSerializer(serializers.Serializer):
    purchase_item = serializers.IntegerField()
    receipt_date = serializers.DateField()
    quantity = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.01"))
    unit_cost = serializers.DecimalField(max_digits=14, decimal_places=4, min_value=Decimal("0"))
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


class ShipmentInputSerializer(serializers.Serializer):
    shipment_no = serializers.CharField(max_length=40, required=False, allow_blank=True)
    shipment_date = serializers.DateField()
    logistics_provider = serializers.CharField(max_length=100, required=False, allow_blank=True)
    waybill_no = serializers.CharField(max_length=100, required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    items = serializers.ListField(child=serializers.DictField(), min_length=1)


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

    class Meta:
        model = FollowUp
        fields = "__all__"

    def get_type_display(self, obj):
        return obj.get_type_display()


class CategoryAttributeSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = CategoryAttribute
        fields = "__all__"
        extra_kwargs = {"key": {"required": False}}

    def validate(self, attrs):
        if not attrs.get("key"):
            attrs["key"] = attrs.get("name", getattr(self.instance, "key", "")).strip()
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
    category_name = serializers.CharField(source="category.name", read_only=True, default="未分类")
    sku_count = serializers.IntegerField(read_only=True, default=0)
    parameter_count = serializers.IntegerField(read_only=True, default=0)
    certificate_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Product
        fields = "__all__"
        read_only_fields = ["code"]

    @transaction.atomic
    def create(self, validated_data):
        validated_data.pop("code", None)
        additional_categories = validated_data.pop("additional_categories", [])
        product = Product.objects.create(code=allocate_product_code(), **validated_data)
        product.additional_categories.set(additional_categories)
        return product


class SKUSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_code = serializers.CharField(source="product.code", read_only=True)
    stock_quantity = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True, default=0)
    actual_quantity = serializers.SerializerMethodField()
    reserved_quantity = serializers.SerializerMethodField()
    available_quantity = serializers.SerializerMethodField()
    in_transit_quantity = serializers.SerializerMethodField()
    to_procure_quantity = serializers.SerializerMethodField()
    has_anomaly = serializers.SerializerMethodField()

    class Meta:
        model = SKU
        fields = "__all__"

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


class QuoteItemSerializer(serializers.ModelSerializer):
    sku_code = serializers.CharField(source="sku_code_snapshot", read_only=True)
    product_name = serializers.CharField(source="product_name_snapshot", read_only=True)
    unit = serializers.CharField(source="unit_snapshot", read_only=True)
    image = serializers.ImageField(source="image_snapshot", read_only=True)
    amount = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)

    class Meta:
        model = QuoteItem
        fields = ["id", "sku", "sku_code", "product_name", "unit", "image", "quantity", "unit_price", "amount", "description", "notes"]


class QuoteSerializer(serializers.ModelSerializer):
    items = QuoteItemSerializer(many=True)
    customer_name = serializers.CharField(source="buyer_company_name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    total_amount = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    root_quote_no = serializers.SerializerMethodField()
    revision_label = serializers.SerializerMethodField()
    parent_quote_no = serializers.SerializerMethodField()

    class Meta:
        model = Quote
        fields = "__all__"
        read_only_fields = ["quote_no", "root_quote", "parent_quote", "revision_no", "revision_summary", "buyer_company_name"]

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


class OrderItemSerializer(serializers.ModelSerializer):
    sku_code = serializers.CharField(source="sku.sku", read_only=True)
    product_name = serializers.CharField(source="sku.product.name", read_only=True)
    amount = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = ["id", "sku", "sku_code", "product_name", "quantity", "unit_price", "cost_price", "amount", "notes"]


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
        if self.instance is None and not attrs.get("items"):
            raise serializers.ValidationError({"items": "订单至少需要一条商品明细。"})
        source_quote = attrs.get("quote")
        customer = attrs.get("customer")
        if self.instance is None and source_quote and customer and source_quote.customer_id != customer.id:
            raise serializers.ValidationError({"customer": "从报价创建订单时，客户必须与来源报价一致。"})
        return attrs

    @staticmethod
    def _item_signature(items):
        return [
            (item["sku"].pk, Decimal(item["quantity"]), Decimal(item["unit_price"]), item.get("notes", ""))
            for item in items
        ]

    def _create_quote_revision_if_needed(self, source_quote, order_data, order_items):
        source_items = list(source_quote.items.order_by("id"))
        changed_parts = []
        if self._item_signature(order_items) != [
            (item.sku_id, item.quantity, item.unit_price, item.notes)
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
            quote_no, revision_no = allocate_revision_quote_no(root_quote)
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
                }
                for index, item in enumerate(order_items)
            ],
            source_items=source_items,
        )
        return revision

    @transaction.atomic
    def create(self, validated_data):
        items = validated_data.pop("items", [])
        source_quote = validated_data.get("quote")
        if source_quote:
            validated_data["quote"] = self._create_quote_revision_if_needed(source_quote, validated_data, items)
        order = Order.objects.create(**validated_data)
        rows = []
        for item in items:
            if not item.get("cost_price"):
                item["cost_price"] = item["sku"].cost_price
            rows.append(OrderItem(order=order, **item))
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
        items = validated_data.pop("items", None)
        for key, value in validated_data.items():
            setattr(instance, key, value)
        instance.save()
        if items is not None:
            instance.items.all().delete()
            rows = []
            for item in items:
                if not item.get("cost_price"):
                    item["cost_price"] = item["sku"].cost_price
                rows.append(OrderItem(order=instance, **item))
            OrderItem.objects.bulk_create(rows)
        from .services.fulfillment import allocate_order
        allocate_order(instance)
        return instance


class TransactionSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.name", read_only=True, default="")
    order_no = serializers.CharField(source="order.order_no", read_only=True, default="")
    direction_display = serializers.CharField(source="get_direction_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    rmb_amount = serializers.SerializerMethodField()

    class Meta:
        model = Transaction
        fields = "__all__"
        extra_kwargs = {"transaction_no": {"required": False}}

    def get_rmb_amount(self, obj):
        return obj.rmb_amount or (obj.amount * obj.exchange_rate).quantize(Decimal("0.01"))

    def validate(self, attrs):
        order = attrs.get("order", getattr(self.instance, "order", None))
        customer = attrs.get("customer", getattr(self.instance, "customer", None))
        if order and customer and order.customer_id != customer.id:
            raise serializers.ValidationError("流水选择的客户必须与订单客户一致。")
        if order and not customer:
            attrs["customer"] = order.customer
        return attrs


class PaymentPlanSerializer(serializers.ModelSerializer):
    remaining_amount = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    contract_no = serializers.SerializerMethodField()
    counterparty_name = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()

    class Meta:
        model = PaymentPlan
        fields = "__all__"

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

    def validate(self, attrs):
        if bool(attrs.get("order")) == bool(attrs.get("purchase_order")):
            raise serializers.ValidationError("变更单必须且只能关联一个订单或采购单。")
        return attrs


class InventoryMovementSerializer(serializers.ModelSerializer):
    sku_code = serializers.CharField(source="sku.sku", read_only=True)
    product_name = serializers.CharField(source="sku.product.name", read_only=True)
    order_no = serializers.CharField(source="order.order_no", read_only=True, default="")
    type_display = serializers.CharField(source="get_type_display", read_only=True)
    signed_quantity = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)

    class Meta:
        model = InventoryMovement
        fields = "__all__"

    def validate(self, attrs):
        order = attrs.get("order", getattr(self.instance, "order", None))
        sku = attrs.get("sku", getattr(self.instance, "sku", None))
        if order and sku and not order.items.filter(sku=sku).exists():
            raise serializers.ValidationError("选择的 SKU 不在该订单明细中。")
        return attrs
