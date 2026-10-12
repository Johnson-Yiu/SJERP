"""Financial ownership follows sales customers; procurement and overhead are shared."""
from django.db.models import Q
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission

from .models import ContractChangeRequest, Customer, PaymentPlan, Transaction
from .permissions import action_for_request, user_can
from .sales_scope import effective_data_scope, scope_customer_queryset


def require_finance_permission(user, module, action):
    if not user_can(user, module, action):
        raise PermissionDenied("你没有权限执行此财务操作。")


def scope_plan_queryset(queryset, user):
    if effective_data_scope(user) == "all":
        return queryset
    customers = scope_customer_queryset(Customer.objects.all(), user)
    return queryset.filter(Q(order__isnull=True) | Q(order__customer__in=customers))


def scope_transaction_queryset(queryset, user):
    if effective_data_scope(user) == "all":
        return queryset
    customers = scope_customer_queryset(Customer.objects.all(), user)
    hidden_customers = Customer.objects.exclude(pk__in=customers.values("pk"))
    hidden_plans = PaymentPlan.objects.filter(order__customer__in=hidden_customers)
    hidden = set(Transaction.objects.filter(
        Q(customer__in=hidden_customers) | Q(order__customer__in=hidden_customers)
        | Q(plan__in=hidden_plans) | Q(allocations__plan__in=hidden_plans)
        | (Q(customer__isnull=True, order__isnull=True, plan__isnull=True)
           & (Q(kind__in=["customer_receipt", "refund", "order_expense"])
              | Q(kind="unallocated_advance", direction="income")))
    ).values_list("pk", flat=True))
    # A split family is one void operation. Hide the entire family if any
    # member touches an inaccessible sale, including historical allocations.
    frontier = hidden.copy()
    while frontier:
        parents = Transaction.objects.filter(pk__in=frontier).exclude(split_from=None).values_list("split_from_id", flat=True)
        children = Transaction.objects.filter(Q(split_from_id__in=frontier) | Q(replaces_id__in=frontier)).values_list("pk", flat=True)
        frontier = (set(parents) | set(children)) - hidden
        hidden.update(frontier)
    return queryset.exclude(pk__in=hidden)


def validate_finance_relations(attrs, user, instance=None):
    def value(name):
        return attrs.get(name, getattr(instance, name, None))
    customers = scope_customer_queryset(Customer.objects.all(), user)
    customer, order, plan = value("customer"), value("order"), value("plan")
    ids = [obj.pk for obj in [customer] if obj]
    if order:
        ids.append(order.customer_id)
    if plan and plan.order_id:
        ids.append(plan.order.customer_id)
    if any(not customers.filter(pk=pk).exists() for pk in ids):
        raise PermissionDenied("关联业务不在当前账号的数据范围内。")
    replaced = value("replaces")
    if replaced and not scope_transaction_queryset(Transaction.objects.filter(pk=replaced.pk), user).exists():
        raise PermissionDenied("原始流水不在当前账号的数据范围内。")
    if instance is None and not ids and not plan and (
        value("kind") in {"customer_receipt", "refund", "order_expense"}
        or (value("kind") == "unallocated_advance" and value("direction") == "income")
    ) and effective_data_scope(user) != "all":
        raise PermissionDenied("销售关联流水需要明确客户或订单归属。")


class ContractFinancePermission(BasePermission):
    def has_permission(self, request, view):
        action = action_for_request(request, view)
        instance = ContractChangeRequest.objects.filter(pk=view.kwargs.get("pk")).first() if view.kwargs.get("pk") else None
        if instance:
            module = "orders" if instance.order_id else "purchases"
        elif request.method == "POST":
            module = "purchases" if request.data.get("purchase_order") else "orders"
        else:
            return user_can(request.user, "orders", action) or user_can(request.user, "purchases", action)
        return user_can(request.user, module, action)
