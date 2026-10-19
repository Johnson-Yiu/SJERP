"""REAL_API_OBSERVATION + DATABASE_VERIFICATION for the isolated P2-C run."""
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

from django.apps import apps
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from crm.models import AdvanceAllocation, CashSourceAllocation, Order, PaymentPlan, RmbCashEvent, Transaction

assert Path(settings.DATABASES["default"]["NAME"]).name == "r1-fin-p2-c-isolated.sqlite3"
out = Path(__file__).resolve().parent
observations = []

def call(method, path, body=None, expected=None):
    req = urllib.request.Request("http://127.0.0.1:8142/api/" + path,
        data=None if body is None else json.dumps(body).encode(),
        method=method, headers={"Content-Type": "application/json"})
    try:
        response = urllib.request.urlopen(req, timeout=10)
    except urllib.error.HTTPError as error:
        response = error
    data = json.loads(response.read())
    item = {"method": method, "path": path, "status": response.status, "request": body, "response": data}
    observations.append(item)
    if expected is not None:
        assert response.status == expected, item
    return data

listing = call("GET", "rmb-cash-events/")
assert len(listing["results"]) == 9
confirmed = [row for row in listing["results"] if row["status"] == "confirmed"]
cancelled = [row for row in listing["results"] if row["status"] == "cancelled"]
assert len(confirmed) == 7 and len(cancelled) == 2
parent = next(row for row in confirmed if row["bank_reference"] == "P2C-BANK-B-60")
payload = RmbCashEvent.objects.get(pk=parent["id"]).request_payload
assert call("GET", "rmb-cash-events/by-request-key/?request_key=" + parent["request_key"])["id"] == parent["id"]
assert call("POST", "rmb-cash-events/", payload)["id"] == parent["id"]
assert call("POST", "rmb-cash-events/", dict(payload, bank_net_amount="427.00"), expected=409)
assert call("POST", "rmb-cash-events/", dict(payload, event_no="P2C-OVER", request_key="P2C-OVER", sources=[{"transaction_id": 1, "amount": "0.01", "verified": True}]), expected=409)
jpy_id = Transaction.objects.get(transaction_no="P2C-JPY-100").pk
assert call("POST", "rmb-cash-events/preview/", dict(payload, event_no="P2C-JPY-BAD", request_key="P2C-JPY-BAD", currency="JPY", quoted_rate="0.050000", bank_net_amount="5.00", sources=[{"transaction_id": jpy_id, "amount": "0.1", "verified": True}]), expected=400) is not None
assert call("POST", "rmb-cash-events/preview/", dict(payload, event_no="P2C-FLOAT-BAD", request_key="P2C-FLOAT-BAD", bank_net_amount=87.6), expected=400) is not None
source_id = Transaction.objects.get(transaction_no="P2C-USD-A-60").pk
assert call("POST", f"transactions/{source_id}/void/", {"reason": "P2-C 已结汇来源作废拒绝"}, expected=400) is not None
assert call("POST", "transactions/", {"transaction_no": "P2C-REFUND-BLOCKED", "transaction_date": "2026-10-19", "direction": "expense", "category": "退款测试", "amount": "10.00", "currency": "USD", "exchange_rate": "7.100000", "kind": "refund", "order": 1}, expected=400) is not None
assert call("POST", "transactions/", {"transaction_no": "P2C-REPLACE-BLOCKED", "transaction_date": "2026-10-19", "direction": "income", "category": "替代测试", "amount": "1.00", "currency": "USD", "exchange_rate": "7.100000", "kind": "other_income", "replaces": source_id}, expected=400) is not None
assert call("POST", "rmb-cash-events/preview/", dict(payload, event_no="P2C-UNSUPPORTED", request_key="P2C-UNSUPPORTED", currency="KPW"), expected=400) is not None

before_legacy = (out / "legacy-before.json").read_text(encoding="utf-8")
legacy_models = {m.__name__: list(m.objects.order_by("pk").values()) for m in apps.get_app_config("crm").get_models() if m not in {RmbCashEvent, CashSourceAllocation}}
after_legacy = json.dumps(legacy_models, cls=DjangoJSONEncoder, sort_keys=True, indent=2)
(out / "legacy-after.json").write_text(after_legacy, encoding="utf-8")
assert before_legacy == after_legacy

expected_source_remaining = {
    "P2C-USD-A-60": Decimal("0.0000"), "P2C-USD-A-40": Decimal("40.0000"),
    "P2C-USD-B-100": Decimal("0.0000"), "P2C-USD-C-30": Decimal("0.0000"),
    "P2C-USD-C-70": Decimal("0.0000"), "P2C-USD-ADV": Decimal("0.0000"),
    "P2C-CNY-DIRECT": Decimal("0.0000"), "P2C-CNY-BANK-FEE": Decimal("0.0000"),
    "P2C-USD-HIST-4DP": Decimal("12.3401"),
}
remaining = {}
for row in Transaction.objects.filter(transaction_no__in=expected_source_remaining):
    used = sum((a.amount for a in row.cash_source_allocations.filter(event__status="confirmed")), Decimal("0"))
    remaining[row.transaction_no] = str(row.amount - used)
    assert row.amount - used == expected_source_remaining[row.transaction_no], (row.transaction_no, row.amount, used)

assert Transaction.objects.count() == 10
assert CashSourceAllocation.objects.count() == 10
assert RmbCashEvent.objects.count() == 9
assert AdvanceAllocation.objects.filter(advance__transaction_no="P2C-USD-ADV", is_active=True).count() == 1
assert AdvanceAllocation.objects.get(advance__transaction_no="P2C-USD-ADV").amount == Decimal("20.0000")
assert list(Order.objects.filter(order_no__startswith="P2C-").values_list("status", flat=True))
assert all(plan.settled_amount <= plan.planned_amount for plan in PaymentPlan.objects.filter(order__order_no__startswith="P2C-"))

summary = {
    "DATABASE_VERIFICATION": {
        "legacy_sha256": hashlib.sha256(after_legacy.encode()).hexdigest(),
        "legacy_unchanged": True, "transaction_count": Transaction.objects.count(),
        "payment_plan_count": PaymentPlan.objects.count(), "cash_event_count": RmbCashEvent.objects.count(),
        "confirmed_event_count": len(confirmed), "cancelled_event_count": len(cancelled),
        "allocation_count": CashSourceAllocation.objects.count(), "source_remaining": remaining,
        "confirmed_bank_net_cny": str(sum((e.bank_net_amount if e.direction == "income" else -e.bank_net_amount for e in RmbCashEvent.objects.filter(status="confirmed")), Decimal("0"))),
        "reference_difference_only": [
            {
                "bank_reference": row["bank_reference"],
                "difference": row.get("net_minus_reference_information_only"),
            }
            for row in confirmed
            if row.get("net_minus_reference_information_only") is not None
        ],
    },
    "REAL_API_OBSERVATION": {"request_count": len(observations), "rejected_statuses": [o["status"] for o in observations if o["status"] >= 400]},
}
(out / "real-api-final.json").write_text(json.dumps({"observations": observations, "summary": summary}, ensure_ascii=False, indent=2, cls=DjangoJSONEncoder), encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False, indent=2, cls=DjangoJSONEncoder))
