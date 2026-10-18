"""FIXTURE_SETUP only: create a fresh disposable browser test database."""
import hashlib
import json
import os
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

from django.conf import settings
from crm.models import Customer, Order, PaymentPlan, Product, SKU, RmbCashEvent, CashSourceAllocation
from crm.services.finance import record_transaction

assert Path(settings.DATABASES["default"]["NAME"]).name == "r1-fin-p2-b-isolated.sqlite3"
assert not Customer.objects.exists(), "Only a new synthetic DB is permitted; no cleanup/rewrite"

out = Path(__file__).resolve().parent
customer = Customer.objects.create(code="P2B-SYNTH-C", name="P2B 合成客户")
product = Product.objects.create(code="P2B-SYNTH-P", name="P2B 合成产品")
sku = SKU.objects.create(sku="P2B-SYNTH-SKU", product=product)
order = Order.objects.create(order_no="P2B-SYNTH-O", customer=customer, currency="USD", exchange_rate="7.100000", status="confirmed", order_date=date(2026, 10, 19))
order.items.create(sku=sku, quantity=1, unit_price="100")
PaymentPlan.objects.create(order=order, direction="receivable", currency="USD", planned_amount="30")
PaymentPlan.objects.create(order=order, direction="receivable", currency="USD", planned_amount="70")
root = record_transaction(dict(transaction_no="P2B-SYNTH-T", order=order, customer=customer, amount="100", currency="USD", exchange_rate="7.100000", kind="customer_receipt"))
rows = [root, root.split_rows.get()]
voucher = {"type": "SYNTHETIC_BANK_VOUCHER_NOT_REAL", "original_currency": "USD", "original_amount": "100.00", "bank_net_cny": "705.00", "included_fee_cny": "5.00", "date": "2026-10-19", "reference": "P2B-SYNTH-BANK-01"}
voucher_bytes = json.dumps(voucher, indent=2, ensure_ascii=False).encode()
(out / "synthetic-bank-voucher.json").write_bytes(voucher_bytes)
(out / "fixture.json").write_text(json.dumps({"customer": customer.pk, "order": order.pk, "sources": [row.pk for row in rows], "voucher_sha256": hashlib.sha256(voucher_bytes).hexdigest(), "voucher": voucher}, ensure_ascii=False, indent=2), encoding="utf-8")
old = {model.__name__: list(model.objects.order_by("pk").values()) for model in (Customer, Order, PaymentPlan, Product, SKU)}
(out / "fixture-legacy-before.json").write_text(json.dumps(old, sort_keys=True, indent=2, default=str), encoding="utf-8")
assert RmbCashEvent.objects.count() == 0 and CashSourceAllocation.objects.count() == 0
print("FIXTURE_SETUP", {"order": order.pk, "sources": [row.pk for row in rows], "bank_accounts": ["SYNTH-FX-01", "SYNTH-CNY-01"], "voucher": voucher})
