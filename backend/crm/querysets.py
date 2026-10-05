from django.db.models import Prefetch

from .models import PurchaseCostAllocation


def prefetch_purchase_related_orders(queryset):
    """Load actual order cost allocations for PurchaseOrderSerializer in bulk."""
    allocations = PurchaseCostAllocation.objects.select_related("order").order_by("order_id", "id")
    return queryset.prefetch_related(
        Prefetch("items__cost_allocations", queryset=allocations)
    )
