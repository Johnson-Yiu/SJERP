"""Business isolation for records entered only for historical analysis."""

from django.core.exceptions import ValidationError


HISTORICAL_STATUS = "historical"
HISTORICAL_LABEL = "历史订单 · 仅用于经营分析"


def is_historical(contract):
    return bool(contract and (getattr(contract, "historical_only", False) or getattr(contract, "status", None) == HISTORICAL_STATUS))


def reject_historical(contract, action="正式业务操作"):
    if is_historical(contract):
        raise ValidationError(f"历史订单仅用于经营分析，不能执行{action}。")


def has_verified_history_balance(contract):
    """Only explicitly activated historical balances can settle new cash."""
    if not contract or not hasattr(contract, "history_balance"):
        return False
    return contract.history_balance.group.fulfillment_handoff_status in {"approved", "drafts_created"}


def reject_unlinked_historical_finance(contract, action="收付款"):
    if is_historical(contract) and not has_verified_history_balance(contract):
        raise ValidationError(f"历史订单尚未核实启用未结余额，不能执行{action}。")
