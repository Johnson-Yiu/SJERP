"""Business isolation for records entered only for historical analysis."""

from django.core.exceptions import ValidationError


HISTORICAL_STATUS = "historical"
HISTORICAL_LABEL = "历史订单 · 仅用于经营分析"


def is_historical(contract):
    return bool(contract and (getattr(contract, "historical_only", False) or getattr(contract, "status", None) == HISTORICAL_STATUS))


def reject_historical(contract, action="正式业务操作"):
    if is_historical(contract):
        raise ValidationError(f"历史订单仅用于经营分析，不能执行{action}。")
