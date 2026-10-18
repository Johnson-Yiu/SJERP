"""DATABASE_VERIFICATION: snapshot synthetic business and bank-fact records."""
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
from crm.models import CashSourceAllocation, Customer, Order, PaymentPlan, RmbCashEvent, Transaction

assert Path(settings.DATABASES["default"]["NAME"]).name == "r1-fin-p2-b-isolated.sqlite3"
out = Path(__file__).resolve().parent / "database-after.json"
def dec(value):
    return str(value) if value is not None else None

data = {
    "database": Path(settings.DATABASES["default"]["NAME"]).name,
    "orders": list(Order.objects.filter(order_no="P2B-SYNTH-O").values("id", "order_no", "status", "currency")),
    "payment_plans": list(PaymentPlan.objects.filter(order__order_no="P2B-SYNTH-O").values("id", "direction", "currency", "planned_amount", "settled_amount", "status")),
    "transactions": list(Transaction.objects.filter(transaction_no__in=["P2B-SYNTH-T"]).values("id", "transaction_no", "amount", "allocated_amount", "rmb_amount", "status", "split_from_id")),
    "cash_events": [],
    "source_allocations": [],
}
for row in RmbCashEvent.objects.order_by("id"):
    data["cash_events"].append({
        "id": row.id, "event_no": row.event_no, "request_key": row.request_key,
        "kind": row.kind, "currency": row.currency, "amount": dec(row.amount),
        "bank_date": str(row.bank_date), "bank_net_amount": dec(row.bank_net_amount),
        "fee_mode": row.fee_mode, "fee_amount": dec(row.fee_amount),
        "source_account": row.source_account, "rmb_account": row.rmb_account,
        "bank_reference": row.bank_reference, "status": row.status,
        "evidence_reference": row.evidence_reference, "evidence_sha256": row.evidence_sha256,
        "cancelled_reason": row.cancelled_reason, "confirmed_at": str(row.confirmed_at) if row.confirmed_at else None,
    })
for row in CashSourceAllocation.objects.order_by("id"):
    data["source_allocations"].append({
        "id": row.id, "event_id": row.event_id, "source_id": row.source_id,
        "amount": dec(row.amount), "currency": row.currency,
        "source_transaction_no": row.source.transaction_no,
    })
out.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
print(json.dumps({"DATABASE_VERIFICATION": {"events": len(data["cash_events"]), "allocations": len(data["source_allocations"]), "output": str(out)}}, ensure_ascii=False))
