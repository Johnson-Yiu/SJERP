"""Shared procurement with separately authorized sales links."""
from rest_framework.exceptions import PermissionDenied
from .models import Order
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


def require_cost_allocation_updates(user):
    """Require the purchasing write capability for allocation target lookup."""
    if not user_can(user, "purchases", "update"):
        raise PermissionDenied("需要采购修改权限才能选择成本归属订单。")


def validate_cost_writes(purchase, user, allocations):
    """Authorize a complete cost-attribution replacement as procurement work.

    Cost attribution is a purchasing responsibility even when the target sales
    order belongs to another salesperson.  Keep the order objects in the
    payload for the service-level cancelled-order and integrity checks, but do
    not turn a purchase allocation into an order edit or require the caller to
    have the sales order's customer scope.
    """
    if not user_can(user, "purchases", "update"):
        raise PermissionDenied("需要采购修改权限才能调整成本归属。")

    # A save replaces every attribution and recomputes all expense shares.
    # Only incoming targets need an order existence check; persisted rows are
    # protected by the foreign key and may legitimately be moved away from a
    # cancelled historical order.
    target_ids = {row.get("order").pk for row in allocations if row.get("order")}
    existing_ids = set(Order.objects.filter(pk__in=target_ids).values_list("pk", flat=True))
    if target_ids - existing_ids:
        raise PermissionDenied("成本归属目标销售订单不存在。")


def scoped_cost_summary(summary, user):
    ids = {row["order"] for row in summary["allocations"] if row.get("order")}
    visible = visible_order_ids(user, ids)
    summary["can_edit"] = user_can(user, "purchases", "update")
    summary["read_only_reason"] = "需要采购修改权限才能调整成本归属。" if not summary["can_edit"] else ""
    for row in summary["allocations"]:
        if row.get("order") and row["order"] not in visible:
            row["sales_link_restricted"] = True
            if not summary["can_edit"]:
                # A read-only purchasing user may see that a historical
                # allocation exists, but must not receive a cross-scope order
                # identifier.  Keep the row and its amounts intact while
                # replacing only the restricted sales link with an explicit
                # placeholder.
                row["order"] = None
                row["order_no"] = ""
                row["target_name"] = "销售订单（详情受限）"
    return summary


def scoped_supplier_candidates(rows, user):
    can_view_purchases = user_can(user, "purchases", "view")
    if can_view_purchases:
        return rows
    result = []
    for row in rows:
        row["last_purchase"] = None
        for source in row.get("supplier_skus", []):
            for field in ("purchase_price", "currency"):
                source.pop(field, None)
        row["source_types"] = [value for value in row.get("source_types", []) if value != "historical_purchase"]
        row["sources"] = [value for value in row.get("sources", []) if value != "历史采购"]
        row["source_label"] = "、".join(row["source_types"])
        if row["source_types"]:
            result.append(row)
    return result
