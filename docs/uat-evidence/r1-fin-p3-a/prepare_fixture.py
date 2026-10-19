"""FIXTURE_SETUP only: create an isolated P2-C synthetic finance dataset."""
import hashlib
import json
import os
import sys
from datetime import date
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
from crm.models import Customer, Order, PaymentPlan, Product, SKU, RmbCashEvent, CashSourceAllocation, Transaction
from crm.services.finance import allocate_advance, record_transaction

assert Path(settings.DATABASES["default"]["NAME"]).name == ".r1-fin-p3-a-isolated.sqlite3"
assert not Customer.objects.exists(), "Only the new synthetic database is permitted"
out = Path(__file__).resolve().parent

customer = Customer.objects.create(code="P2C-SYNTH-C", name="P2C 合成客户")
product = Product.objects.create(code="P2C-SYNTH-P", name="P2C 合成产品")
sku = SKU.objects.create(sku="P2C-SYNTH-SKU", product=product)

def make_order(no, currency, total, rate="7.100000"):
    order = Order.objects.create(order_no=no, customer=customer, currency=currency, exchange_rate=rate,
                                 status="confirmed", order_date=date(2026, 10, 18))
    order.items.create(sku=sku, quantity=1, unit_price=total)
    return order

order_a = make_order("P2C-ORDER-A", "USD", "200", "7.100000")
plan_a1 = PaymentPlan.objects.create(order=order_a, direction="receivable", currency="USD", planned_amount="100", due_date=date(2026, 10, 18), notes="首期")
plan_a2 = PaymentPlan.objects.create(order=order_a, direction="receivable", currency="USD", planned_amount="100", due_date=date(2026, 10, 25), notes="尾款")
receipt_a1 = record_transaction(dict(transaction_no="P2C-USD-A-60", plan=plan_a1, amount="60", currency="USD", exchange_rate="7.100000"))
receipt_a2 = record_transaction(dict(transaction_no="P2C-USD-A-40", plan=plan_a1, amount="40", currency="USD", exchange_rate="7.100000"))

order_b = make_order("P2C-ORDER-B", "USD", "100", "7.100000")
plan_b = PaymentPlan.objects.create(order=order_b, direction="receivable", currency="USD", planned_amount="100", due_date=date(2026, 10, 19))
receipt_b = record_transaction(dict(transaction_no="P2C-USD-B-100", plan=plan_b, amount="100", currency="USD", exchange_rate="7.100000"))

order_c = make_order("P2C-ORDER-C", "USD", "100", "7.100000")
plan_c = PaymentPlan.objects.create(order=order_c, direction="receivable", currency="USD", planned_amount="100", due_date=date(2026, 10, 20))
receipt_c1 = record_transaction(dict(transaction_no="P2C-USD-C-30", plan=plan_c, amount="30", currency="USD", exchange_rate="7.100000"))
receipt_c2 = record_transaction(dict(transaction_no="P2C-USD-C-70", plan=plan_c, amount="70", currency="USD", exchange_rate="7.100000"))

order_d = make_order("P2C-ORDER-D", "USD", "50", "7.100000")
plan_d = PaymentPlan.objects.create(order=order_d, direction="receivable", currency="USD", planned_amount="50", due_date=date(2026, 10, 21))
advance = record_transaction(dict(transaction_no="P2C-USD-ADV", amount="50", currency="USD", exchange_rate="7.100000", direction="income", kind="unallocated_advance", category="预收款", customer=customer, order=order_d, transaction_date=date(2026, 10, 18)))
allocate_advance(advance, plan_d, Decimal("20"))

cny_customer = Customer.objects.create(code="P2C-CNY-C", name="P2C 人民币客户")
cny_order = Order.objects.create(order_no="P2C-CNY-ORDER", customer=cny_customer, currency="CNY", exchange_rate="1", status="confirmed", order_date=date(2026, 10, 18))
cny_order.items.create(sku=sku, quantity=1, unit_price="20")
cny_plan = PaymentPlan.objects.create(order=cny_order, direction="receivable", currency="CNY", planned_amount="20", due_date=date(2026, 10, 18))
cny_receipt = record_transaction(dict(transaction_no="P2C-CNY-DIRECT", plan=cny_plan, amount="20", currency="CNY", exchange_rate="1"))

historic = Transaction.objects.create(transaction_no="P2C-USD-HIST-4DP", transaction_date=date(2026, 10, 18), direction="income", category="历史四位小数", amount=Decimal("12.3401"), currency="USD", exchange_rate=Decimal("7.123456"), rmb_amount=Decimal("87.9034"), customer=customer, order=order_a, kind="other", status="confirmed")
jpy = Transaction.objects.create(transaction_no="P2C-JPY-100", transaction_date=date(2026, 10, 18), direction="income", category="日元来源", amount=Decimal("100"), currency="JPY", exchange_rate=Decimal("0.050000"), rmb_amount=Decimal("5.0000"), customer=customer, order=order_a, kind="other", status="confirmed")

voucher = {"type": "SYNTHETIC_BANK_VOUCHER_NOT_REAL", "date": "2026-10-19", "reference": "P2C-SYNTH-BANK-01", "note": "仅用于隔离验收"}
voucher_bytes = json.dumps(voucher, ensure_ascii=False, indent=2).encode()
(out / "synthetic-bank-voucher.json").write_bytes(voucher_bytes)

models_before = {m.__name__: list(m.objects.order_by("pk").values()) for m in apps.get_app_config("crm").get_models() if m not in {RmbCashEvent, CashSourceAllocation}}
(out / "legacy-before.json").write_text(json.dumps(models_before, cls=DjangoJSONEncoder, sort_keys=True, indent=2), encoding="utf-8")
(out / "fixture.json").write_text(json.dumps({
    "customer": customer.pk, "orders": [order_a.pk, order_b.pk, order_c.pk, order_d.pk, cny_order.pk],
    "sources": {"split_60_40": [receipt_a1.pk, receipt_a2.pk], "single_100": receipt_b.pk,
                "merge_30_70": [receipt_c1.pk, receipt_c2.pk], "prepayment": advance.pk,
                "cny_direct": cny_receipt.pk, "historic_4dp": historic.pk, "jpy": jpy.pk},
    "voucher_sha256": hashlib.sha256(voucher_bytes).hexdigest(), "voucher": voucher,
}, ensure_ascii=False, indent=2), encoding="utf-8")
assert RmbCashEvent.objects.count() == 0 and CashSourceAllocation.objects.count() == 0
print(json.dumps({"FIXTURE_SETUP": {"db": settings.DATABASES["default"]["NAME"], "orders": 5, "transactions": Transaction.objects.count(), "plans": PaymentPlan.objects.count(), "bank_events": 0}}, ensure_ascii=False))


