"""DATABASE_VERIFICATION: snapshot synthetic records after browser-only preview/restore tests."""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

from django.conf import settings
from crm.models import CashSourceAllocation, Order, PaymentPlan, RmbCashEvent, Transaction

assert Path(settings.DATABASES["default"]["NAME"]).name == "r1-fin-p2-b-fix-02-isolated.sqlite3"
out = Path(__file__).resolve().parent / "database-after.json"
data = {
    "database": Path(settings.DATABASES["default"]["NAME"]).name,
    "orders": list(Order.objects.order_by("id").values("id", "order_no", "status", "currency")),
    "payment_plans": list(PaymentPlan.objects.order_by("id").values("id", "order_id", "direction", "currency", "planned_amount", "settled_amount", "status")),
    "transactions": list(Transaction.objects.order_by("id").values("id", "transaction_no", "amount", "allocated_amount", "rmb_amount", "status", "split_from_id")),
    "cash_events": list(RmbCashEvent.objects.order_by("id").values("id", "event_no", "request_key", "status", "amount", "bank_net_amount")),
    "source_allocations": list(CashSourceAllocation.objects.order_by("id").values("id", "event_id", "source_id", "amount", "currency")),
}
out.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
print(json.dumps({"DATABASE_VERIFICATION": {"database": data["database"], "orders": len(data["orders"]), "transactions": len(data["transactions"]), "cash_events": len(data["cash_events"]), "source_allocations": len(data["source_allocations"]), "preview_only_no_write": not data["cash_events"]}}, ensure_ascii=False))
