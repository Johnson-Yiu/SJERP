"""Read-only assertions for the marked disposable Chrome UAT database."""
import json
import tempfile
from decimal import Decimal
from pathlib import Path
from django.conf import settings
from crm.models import (FinanceFact, GoodsReceipt, HistoryInventoryBaseline, HistoryOperationalContract,
    HistoryTakeoverEvent, InventoryMovement, InventoryReservation, Order, OperationLog, PaymentPlan,
    PurchaseCostAllocation, PurchaseOrder, Shipment, SKU, Transaction)
from crm.services.fulfillment import sku_metrics

db = Path(settings.DATABASES["default"]["NAME"]).resolve()
if settings.DATABASES["default"]["ENGINE"] != "django.db.backends.sqlite3" or not db.is_relative_to(Path(tempfile.gettempdir()).resolve()) or not db.parent.name.startswith("sunjack-history-operational-closeout-"):
    raise RuntimeError("Refusing to inspect an unmarked database")
sku = SKU.objects.get(sku="UAT-HT-S1")
original_sale = Order.objects.get(order_no="HIST-SO-HT-1")
original_purchase = PurchaseOrder.objects.get(purchase_no="HIST-PO-HT-1")
sale = HistoryOperationalContract.objects.get(archived_order=original_sale).continuation_order
purchase = HistoryOperationalContract.objects.get(archived_purchase=original_purchase).continuation_purchase
metrics = sku_metrics(sku)
data = {"database": "temporary synthetic SQLite", "finance_facts": FinanceFact.objects.count(),
    "new_transactions": Transaction.objects.count(), "opening_baselines": HistoryInventoryBaseline.objects.count(),
    "receipts": GoodsReceipt.objects.count(), "shipments": Shipment.objects.count(), "movements": InventoryMovement.objects.count(),
    "reservations": InventoryReservation.objects.count(), "actual_stock": str(metrics["actual_quantity"]),
    "reserved_stock": str(metrics["reserved_quantity"]), "sales_outstanding": str(original_sale.outstanding_amount),
    "purchase_outstanding": str(original_purchase.unpaid_amount), "payment_plans": PaymentPlan.objects.count(),
    "archived_sales_quantity": str(original_sale.items.get().quantity), "archived_purchase_quantity": str(original_purchase.items.get().quantity),
    "continuation_sales_quantity": str(sale.items.get().quantity), "continuation_purchase_quantity": str(purchase.items.get().quantity),
    "purchase_allocated_to_continuation": PurchaseCostAllocation.objects.filter(purchase_item__purchase_order=purchase, order=sale).exists(),
    "history_events": HistoryTakeoverEvent.objects.count(), "operation_logs": OperationLog.objects.count(),
    "movement_locations": list(InventoryMovement.objects.order_by("id").values("type", "quantity", "warehouse_type", "warehouse", "lot_reference"))}
assert (data["finance_facts"], data["new_transactions"], data["opening_baselines"], data["receipts"], data["shipments"], data["movements"]) == (2, 2, 1, 1, 1, 2)
assert tuple(Decimal(data[key]) for key in ("actual_stock", "sales_outstanding", "purchase_outstanding")) == (Decimal("15"), Decimal("40"), Decimal("6"))
assert data["purchase_allocated_to_continuation"]
assert all(row["warehouse"] == "SYN-WH-01" and row["lot_reference"] == "LOT-HT-01" for row in data["movement_locations"])
print(json.dumps(data, ensure_ascii=False, default=str, indent=2))
