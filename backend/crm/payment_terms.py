from copy import deepcopy
from decimal import Decimal, InvalidOperation
from fractions import Fraction

from django.core.exceptions import ValidationError

DEFAULT_PAYMENT_TERMS = [
    {"label": "预付款", "ratio": "0.30", "due_basis": "order_date", "offset_days": 0},
    {"label": "尾款", "ratio": "0.70", "due_basis": "expected_arrival_date", "offset_days": 0},
]


def default_payment_terms():
    return deepcopy(DEFAULT_PAYMENT_TERMS)


def validate_payment_terms(value, allow_default=False):
    if not isinstance(value, list) or len(value) > 5 or (not value and not allow_default):
        raise ValidationError("请填写 1 至 5 个付款阶段。")
    total = Fraction(0)
    result = []
    for row in value:
        if not isinstance(row, dict):
            raise ValidationError("付款阶段格式无效。")
        label = row.get("label")
        days = row.get("offset_days")
        basis = row.get("due_basis")
        if not isinstance(label, str) or not label.strip():
            raise ValidationError("请填写付款阶段名称。")
        if basis not in {"order_date", "expected_arrival_date", "no_date"}:
            raise ValidationError("请选择有效的到期依据。")
        if isinstance(days, bool) or not isinstance(days, int) or days < 0:
            raise ValidationError("延后天数必须是非负整数。")
        try:
            ratio = Decimal(str(row.get("ratio")))
            if not ratio.is_finite() or ratio <= 0 or ratio > 1:
                raise ValueError
        except (InvalidOperation, ValueError, TypeError):
            raise ValidationError("每个付款阶段的比例必须大于 0 且不超过 100%。")
        total += Fraction(ratio)
        result.append({"label": label.strip(), "ratio": str(ratio), "due_basis": basis, "offset_days": days})
    if value and total != 1:
        raise ValidationError("付款比例合计必须为 100%。")
    return result
