from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers

from .models import AccessRole, CategoryAttribute, Contact, Customer, CustomerCodeSequence, EmployeeProfile, FollowUp, InventoryMovement, Order, OrderItem, OrganizationUnit, Position, Product, ProductCategory, ProductCertificate, ProductCodeSequence, ProductParameter, Quote, QuoteItem, RolePermission, SKU, Transaction
from .quote_numbers import allocate_root_quote_no
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

    class Meta:
        model = SKU
        fields = "__all__"


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

    class Meta:
        model = Quote
        fields = "__all__"
        read_only_fields = ["quote_no", "root_quote", "revision_no", "buyer_company_name"]

    def get_root_quote_no(self, obj):
        return obj.root_quote.quote_no if obj.root_quote_id else obj.quote_no

    def get_revision_label(self, obj):
        return f"Revision {obj.revision_no}" if obj.revision_no else "Original"

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
    quote_no = serializers.CharField(source="quote.quote_no", read_only=True, default="")
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    total_amount = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    paid_amount = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    balance_amount = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = "__all__"

    def get_balance_amount(self, obj):
        return (obj.total_amount - obj.paid_amount).quantize(Decimal("0.01"))

    @transaction.atomic
    def create(self, validated_data):
        items = validated_data.pop("items", [])
        order = Order.objects.create(**validated_data)
        rows = []
        for item in items:
            if not item.get("cost_price"):
                item["cost_price"] = item["sku"].cost_price
            rows.append(OrderItem(order=order, **item))
        OrderItem.objects.bulk_create(rows)
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
        return instance


class TransactionSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.name", read_only=True, default="")
    order_no = serializers.CharField(source="order.order_no", read_only=True, default="")
    direction_display = serializers.CharField(source="get_direction_display", read_only=True)
    rmb_amount = serializers.SerializerMethodField()

    class Meta:
        model = Transaction
        fields = "__all__"

    def get_rmb_amount(self, obj):
        return (obj.amount * obj.exchange_rate).quantize(Decimal("0.01"))

    def validate(self, attrs):
        order = attrs.get("order", getattr(self.instance, "order", None))
        customer = attrs.get("customer", getattr(self.instance, "customer", None))
        if order and customer and order.customer_id != customer.id:
            raise serializers.ValidationError("流水选择的客户必须与订单客户一致。")
        if order and not customer:
            attrs["customer"] = order.customer
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
