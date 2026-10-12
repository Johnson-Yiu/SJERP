"""Shared procurement with separately authorized sales links."""
from rest_framework.exceptions import PermissionDenied
from .models import Order, PurchaseCostAllocation
from .permissions import user_can
from .sales_scope import scope_customer_related_queryset


def visible_order_ids(user, ids, *, write=False):
    if not user_can(user, "orders", "view") or (write and not user_can(user, "orders", "update")):
        return set()
    return set(scope_customer_related_queryset(Order.objects.filter(pk__in=ids), user).values_list("pk", flat=True))


def require_order_writes(user, ids):
    ids = {pk for pk in ids if pk}
    if ids - visible_order_ids(user, ids, write=True):
        raise PermissionDenied("没有权限修改采购关联的销售订单。")


def validate_cost_writes(purchase, user, allocations):
    # A save replaces every attribution and recomputes all expense shares.
    old = PurchaseCostAllocation.objects.filter(purchase_item__purchase_order=purchase).values_list("order_id", flat=True)
    require_order_writes(user, [*old, *(row.get("order").pk for row in allocations if row.get("order"))])


def scoped_cost_summary(summary, user):
    ids = {row["order"] for row in summary["allocations"] if row.get("order")}
    visible = visible_order_ids(user, ids)
    summary["can_edit"] = user_can(user, "purchases", "update") and not (ids - visible_order_ids(user, ids, write=True))
    summary["read_only_reason"] = "包含无权修改的销售订单，请由具备全部关联订单权限的人员调整。" if not summary["can_edit"] else ""
    for row in summary["allocations"]:
        if row.get("order") and row["order"] not in visible:
            row.update(order=None, order_no="", target_name="", sales_link_restricted=True)
    return summary


def scoped_supplier_candidates(rows, user):
    if user_can(user, "purchases", "view"):
        return rows
    result = []
    for row in rows:
        row["last_purchase"] = None
        row["source_types"] = [value for value in row.get("source_types", []) if value != "historical_purchase"]
        row["sources"] = [value for value in row.get("sources", []) if value != "历史采购"]
        row["source_label"] = "、".join(row["source_types"])
        if row["source_types"]:
            result.append(row)
    return result
