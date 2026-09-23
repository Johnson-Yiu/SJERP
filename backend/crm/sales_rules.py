"""Sales restrictions, independent of SKU identity and purchasing MOQ."""
from decimal import Decimal
from django.db.models import Q
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from .audit import AuditTrailMixin
from .models import SalesRule, SKU
from .services.supplier_candidates import validate_filters
from .sku_identity import category_attributes, raw_parameter_value, normalize_parameter_token, _with_unit


def matches(sku, rule):
    definitions = {f'{a.category_id}:{a.key}': a for a in category_attributes(sku.product)}
    for key, allowed in rule.filters.items():
        attribute = definitions.get(key)
        unit = getattr(attribute, 'unit', '')
        normalize = lambda value: normalize_parameter_token(_with_unit(value, unit))
        actual = raw_parameter_value(sku.parameter_values, key, getattr(attribute, 'name', ''))
        if normalize(actual) not in {normalize(value) for value in allowed}:
            return False
    return True


def check_rows(day, rows, enforce=False):
    rules = list(SalesRule.objects.filter(
        product_id__in={row['sku'].product_id for row in rows}, is_active=True,
    ).filter(Q(effective_from__isnull=True) | Q(effective_from__lte=day))
      .filter(Q(effective_until__isnull=True) | Q(effective_until__gte=day)).order_by('id'))
    result = []
    for index, row in enumerate(rows):
        sku = row['sku']
        applied, errors = [], []
        for rule in rules:
            if rule.product_id != sku.product_id or (rule.sku_id and rule.sku_id != sku.pk) or not matches(sku, rule):
                continue
            applied.append({'id': rule.pk, 'name': rule.name, 'rule_type': rule.rule_type,
                            'minimum_quantity': str(rule.minimum_quantity), 'unit': rule.unit,
                            'filters': rule.filters, 'notes': rule.notes, 'sku': rule.sku_id,
                            'effective_from': rule.effective_from.isoformat() if rule.effective_from else None,
                            'effective_until': rule.effective_until.isoformat() if rule.effective_until else None})
            if sku.unit.strip().casefold() != rule.unit.strip().casefold():
                errors.append(f'规则「{rule.name}」单位 {rule.unit} 与 SKU 单位 {sku.unit} 不一致，请修正规则。')
            elif row['quantity'] < rule.minimum_quantity:
                errors.append(f'{sku.sales_model or sku.sku} 最低报价数量为 {rule.minimum_quantity:g} {rule.unit}，当前 {row["quantity"]:g}；请修改数量。')
        result.append({'line': index + 1, 'sku': sku.pk, 'rules': applied, 'errors': errors})
    if enforce and any(r['errors'] for r in result):
        raise ValidationError({'sales_rules': [f'第 {r["line"]} 行：{e}' for r in result for e in r['errors']]})
    return result


class SalesRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalesRule
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']

    def validate(self, attrs):
        def value(key, default=None):
            return attrs.get(key, getattr(self.instance, key, default))
        product, sku = value('product'), value('sku')
        if sku and sku.product_id != product.pk:
            raise ValidationError({'sku': 'SKU 不属于该产品。'})
        validate_filters(product, value('filters', {}))
        if value('minimum_quantity', 0) <= 0:
            raise ValidationError({'minimum_quantity': '最低报价数量必须大于 0。'})
        if sku and value('unit', 'pcs').strip().casefold() != sku.unit.strip().casefold():
            raise ValidationError({'unit': f'请使用 SKU 的单位：{sku.unit}。'})
        if value('effective_from') and value('effective_until') and value('effective_until') < value('effective_from'):
            raise ValidationError({'effective_until': '结束日期不能早于开始日期。'})
        return attrs


class QuoteCheckSerializer(serializers.Serializer):
    class Row(serializers.Serializer):
        sku = serializers.PrimaryKeyRelatedField(queryset=SKU.objects.select_related('product'))
        quantity = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.01"))
    quote_date = serializers.DateField()
    items = Row(many=True)


class SalesRuleViewSet(AuditTrailMixin, viewsets.ModelViewSet):
    queryset = SalesRule.objects.all().order_by('-id')
    serializer_class = SalesRuleSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        product = self.request.query_params.get('product')
        return qs.filter(product_id=product) if product else qs

    @action(detail=False, methods=['post'], url_path='check-quote')
    def check_quote(self, request):
        serializer = QuoteCheckSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        return Response(check_rows(data['quote_date'], data['items']))
