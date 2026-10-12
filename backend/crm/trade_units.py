"""SKU-specific transaction units. Inventory quantities always remain base quantities."""
from decimal import Decimal, InvalidOperation, localcontext

from django.db import transaction
from django.db.models import F, DecimalField
from django.db.models.functions import Coalesce
from rest_framework import serializers, viewsets

from .models import SKU, SKUTradeUnit
from .audit import AuditTrailMixin

TRADE_FIELDS = ['trade_unit', 'trade_quantity', 'trade_unit_price', 'trade_snapshot']


def amount_expression(prefix=''):
    return Coalesce(F(prefix + 'trade_quantity') * F(prefix + 'trade_unit_price'),
                    F(prefix + 'quantity') * F(prefix + 'unit_price'),
                    output_field=DecimalField(max_digits=28, decimal_places=8))


def trade_values(line):
    return {key: getattr(line, key) for key in TRADE_FIELDS}


def validate_document_amount(attrs, instance=None):
    rows = attrs.get('items')
    if rows is None:
        subtotal = sum((row.amount for row in instance.items.all()), Decimal(0)) if instance else Decimal(0)
    else:
        subtotal = sum((row['trade_quantity'] * row['trade_unit_price'] if row.get('trade_unit') else
                        row['quantity'] * row['unit_price'] for row in rows), Decimal(0))
    total = subtotal + Decimal(attrs.get('shipping_fee', getattr(instance, 'shipping_fee', 0))) - Decimal(attrs.get('discount', getattr(instance, 'discount', 0)))
    if total < 0 or total >= Decimal('10000000000000000'):
        raise serializers.ValidationError({'items': '单据总金额为负或超出系统精度，请检查数量、单价及折扣。'})


def portion_trade(values, base_quantity):
    """Split physical overages without inventing fractional sealed packages."""
    snap = values.get('trade_snapshot') or {}
    factor = Decimal(snap.get('factor', '1'))
    qty = base_quantity / factor
    if values.get('trade_unit') and qty == qty.quantize(Decimal('.01')):
        return {**{k: values.get(k) for k in TRADE_FIELDS}, 'trade_quantity': qty}
    return dict(trade_unit=None, trade_quantity=None, trade_unit_price=None,
                trade_snapshot={'unit': snap.get('base_unit', ''), 'base_unit': snap.get('base_unit', ''), 'factor': '1', 'name': ''})


def number(value, field, *, positive=False, places=2):
    try:
        value = Decimal(str(value))
        if not value.is_finite() or value < 0 or (positive and value == 0):
            raise ValueError()
        if value >= Decimal('1000000000000') or value != value.quantize(Decimal(1).scaleb(-places)):
            raise ValueError()
        return value.quantize(Decimal(1).scaleb(-places))
    except (InvalidOperation, ValueError, TypeError):
        raise serializers.ValidationError({field: f'请输入有效的{"正" if positive else "非负"}数，最多 {places} 位小数，且小于一万亿。'})


def normalize_trade(data, sku, *, price_field='unit_price', existing=None, supplier_id=None):
    """Only trusted catalog values become snapshots; never trust client conversion rates."""
    data = dict(data)
    data.pop('trade_snapshot', None)
    unit_id = data.get('trade_unit')
    if hasattr(unit_id, 'pk'):
        unit_id = unit_id.pk
    if unit_id:
        try:
            unit = SKUTradeUnit.objects.get(pk=unit_id, sku=sku)
        except (SKUTradeUnit.DoesNotExist, ValueError, TypeError):
            raise serializers.ValidationError({'trade_unit': '交易单位不存在或不属于当前 SKU。'})
        inherited = existing is not None and existing.trade_unit_id == unit.pk and existing.sku_id == sku.pk
        if not unit.active and not inherited:
            raise serializers.ValidationError({'trade_unit': '此规格已停用；新业务请选择启用规格。'})
        if supplier_id and unit.supplier_id and str(unit.supplier_id) != str(supplier_id):
            raise serializers.ValidationError({'trade_unit': '此包装规格不属于当前采购供应商。'})
        snap = dict(existing.trade_snapshot) if inherited and existing.trade_snapshot else {
            'name': unit.name, 'unit': unit.unit, 'factor': str(unit.factor),
            'base_unit': sku.unit, 'allow_fraction': unit.allow_fraction,
        }
        qty = number(data.get('trade_quantity'), 'trade_quantity', positive=True)
        if not snap['allow_fraction'] and qty != qty.to_integral_value():
            raise serializers.ValidationError({'trade_quantity': '此规格仅支持整包装数量；拆零请使用基础单位。'})
        factor = Decimal(snap['factor'])
        base = number(qty * factor, 'quantity', positive=True)
        result = dict(trade_unit=unit, trade_quantity=qty, trade_snapshot=snap, quantity=base)
        if price_field:
            price = number(data.get('trade_unit_price'), 'trade_unit_price', places=4)
            with localcontext() as ctx:
                ctx.prec = 40
                base_price = (price / factor).quantize(Decimal('0.000000000001'))
            number(base_price, price_field, places=12)
            result.update(trade_unit_price=price, **{price_field: base_price})
        return result
    qty = number(data.get('quantity', getattr(existing, 'quantity', None)), 'quantity', positive=True)
    result = dict(quantity=qty, trade_unit=None, trade_quantity=None, trade_unit_price=None,
                  trade_snapshot={'base_unit': sku.unit, 'unit': sku.unit, 'factor': '1', 'name': ''})
    if price_field:
        fallback = getattr(existing, price_field, 0 if price_field == 'unit_cost' else None)
        result[price_field] = number(data.get(price_field, fallback), price_field, places=12)
    return result


class TradeLineSerializerMixin:
    def to_representation(self, instance):
        result = super().to_representation(instance)
        for field in ('unit_price', 'unit_cost'):
            if field in result and result[field] is not None:
                value = Decimal(result[field])
                if value == value.quantize(Decimal('.0001')):
                    result[field] = format(value, '.4f')
        return result

    def get_fields(self):
        fields = super().get_fields()
        fields['trade_snapshot'].read_only = True
        # Converted values are calculated before DRF validates the model fields.
        return fields

    def to_internal_value(self, data):
        data = data.copy()
        if self.instance and not any(k in data for k in ('quantity', 'unit_cost', 'unit_price', 'trade_unit', 'trade_quantity', 'trade_unit_price')):
            return super().to_internal_value(data)
        sku_id = data.get('sku', getattr(self.instance, 'sku_id', None))
        try:
            sku = SKU.objects.get(pk=sku_id)
        except (SKU.DoesNotExist, ValueError, TypeError):
            return super().to_internal_value(data)
        source = self.instance
        parent = getattr(self.root, 'instance', None)
        view = self.context.get('view')
        if parent is None and view and getattr(view, 'action', '') == 'revise':
            parent = view.get_object()
        if parent is None and self.root.initial_data.get('quote'):
            from .models import Quote
            try:
                parent = Quote.objects.filter(pk=self.root.initial_data['quote']).first()
            except (ValueError, TypeError):
                raise serializers.ValidationError({'quote': '请选择有效的来源报价。'})
        if source is None and parent and hasattr(parent, 'items'):
            try:
                source = parent.items.filter(sku=sku, trade_unit_id=data.get('trade_unit') or None).first()
            except (ValueError, TypeError):
                raise serializers.ValidationError({'trade_unit': '请选择有效的交易规格。'})
        price_field = 'unit_cost' if self.Meta.model.__name__ == 'InventoryMovement' else 'unit_price'
        values = normalize_trade(data, sku, price_field=price_field, existing=source,
                                 supplier_id=self.root.initial_data.get('supplier'))
        data.update({k: v.pk if k == 'trade_unit' and v else v for k, v in values.items()})
        result = super().to_internal_value(data)
        result['trade_snapshot'] = values['trade_snapshot']
        return result


class SKUTradeUnitSerializer(serializers.ModelSerializer):
    base_unit = serializers.CharField(source='sku.unit', read_only=True)
    sku_code = serializers.CharField(source='sku.sku', read_only=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True, default='')

    class Meta:
        model = SKUTradeUnit
        fields = '__all__'
        # A new default replaces the old one inside create/update's SKU lock.
        # DRF's automatic conditional uniqueness check runs before that switch.
        # This model has no other automatic object-level uniqueness validators;
        # explicit validation and all database constraints remain in force.
        validators = []

    def to_representation(self, instance):
        data = super().to_representation(instance)
        from .permissions import user_can
        request = self.context.get("request")
        user = request.user if request is not None else self.context.get("user")
        if not user_can(user, "suppliers", "view"):
            data.update(supplier=None, supplier_name="")
        if not user_can(user, "skus", "view"):
            data.update(sku=None, sku_code="")
        return data

    def validate(self, attrs):
        from rest_framework.exceptions import PermissionDenied
        from .permissions import user_can
        request = self.context.get("request")
        user = request.user if request is not None else self.context.get("user")
        sku = attrs.get("sku", getattr(self.instance, "sku", None))
        supplier = attrs.get("supplier", getattr(self.instance, "supplier", None))
        if sku and not user_can(user, "skus", "view"):
            raise PermissionDenied("交易单位关联需要 SKU 查看权限。")
        if supplier and not user_can(user, "suppliers", "view"):
            raise PermissionDenied("关联供应商需要供应商查看权限。")
        if self.instance:
            for field in ('sku', 'supplier', 'name', 'unit', 'factor', 'allow_fraction'):
                if field in attrs and attrs[field] != getattr(self.instance, field):
                    raise serializers.ValidationError({field: '规格定义不可改写，请停用旧规格并新建规格。'})
        if attrs.get('factor', Decimal(1)) <= 0:
            raise serializers.ValidationError({'factor': '换算系数必须大于零。'})
        if attrs.get('is_default', getattr(self.instance, 'is_default', False)) and not attrs.get('active', getattr(self.instance, 'active', True)):
            attrs['is_default'] = False
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        SKU.objects.select_for_update().get(pk=validated_data['sku'].pk)
        if validated_data.get('is_default'):
            SKUTradeUnit.objects.filter(sku=validated_data['sku']).update(is_default=False)
        return super().create(validated_data)

    @transaction.atomic
    def update(self, instance, validated_data):
        SKU.objects.select_for_update().get(pk=instance.sku_id)
        if validated_data.get('is_default'):
            SKUTradeUnit.objects.filter(sku=instance.sku).exclude(pk=instance.pk).update(is_default=False)
        return super().update(instance, validated_data)


class SKUTradeUnitViewSet(AuditTrailMixin, viewsets.ModelViewSet):
    serializer_class = SKUTradeUnitSerializer
    queryset = SKUTradeUnit.objects.select_related('sku', 'supplier').all()
    search_fields = ['name', 'unit', 'sku__sku', 'sku__display_name_cn']

    def get_search_fields(self, request):
        from .permissions import user_can
        return list(self.search_fields) if user_can(request.user, "skus", "view") else ["name", "unit"]
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_queryset(self):
        qs = super().get_queryset()
        for key in ('sku', 'supplier'):
            if self.request.query_params.get(key):
                try:
                    qs = qs.filter(**{key + '_id': self.request.query_params[key]})
                except (ValueError, TypeError):
                    raise serializers.ValidationError({key: '筛选 ID 必须是整数。'})
        if self.request.query_params.get('active') == '1':
            qs = qs.filter(active=True)
        return qs
