from django.db.models import F, OuterRef, Prefetch, Subquery
from django.utils import timezone

from .models import FollowUp, PurchaseCostAllocation


def prefetch_purchase_related_orders(queryset):
    """Load actual order cost allocations for PurchaseOrderSerializer in bulk."""
    allocations = PurchaseCostAllocation.objects.select_related("order").order_by("order_id", "id")
    return queryset.prefetch_related(
        Prefetch("items__cost_allocations", queryset=allocations)
    )


def latest_follow_ups_per_customer(queryset=None):
    """Return only the newest historical FollowUp for each customer."""
    queryset = FollowUp.objects.all() if queryset is None else queryset
    latest_id = (
        FollowUp.objects.filter(customer_id=OuterRef("customer_id"))
        .order_by("-followed_at", "-id")
        .values("id")[:1]
    )
    return queryset.annotate(
        _latest_follow_up_id=Subquery(latest_id)
    ).filter(id=F("_latest_follow_up_id"))


def current_due_follow_ups(queryset=None, *, today=None):
    """Return each customer's latest FollowUp when its next action is due today or overdue."""
    today = timezone.localdate() if today is None else today
    return latest_follow_ups_per_customer(queryset).filter(
        next_follow_up__isnull=False,
        next_follow_up__lte=today,
    ).order_by("next_follow_up", "id")
