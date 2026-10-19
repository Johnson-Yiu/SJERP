"""FIXTURE_SETUP only: create a fresh disposable database for real browser evidence."""
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

assert Path(settings.DATABASES["default"]["NAME"]).name == "r1-fin-p2-b-fix-02-isolated.sqlite3"
assert not Customer.objects.exists(), "Only the new synthetic database is permitted"
out = Path(__file__).resolve().parent
customer = Customer.objects.create(code="P2B-FIX-02-C", name="P2B FIX 02 合成客户")
product = Product.objects.create(code="P2B-FIX-02-P", name="P2B FIX 02 合成产品")
sku = SKU.objects.create(sku="P2B-FIX-02-SKU", product=product)
order = Order.objects.create(order_no="P2B-FIX-02-O", customer=customer, currency="USD", exchange_rate="7.100000", status="confirmed", order_date=date(2026, 10, 19))
order.items.create(sku=sku, quantity=1, unit_price="100")
PaymentPlan.objects.create(order=order, direction="receivable", currency="USD", planned_amount="30")
PaymentPlan.objects.create(order=order, direction="receivable", currency="USD", planned_amount="70")
root = record_transaction(dict(transaction_no="P2B-FIX-02-T", order=order, customer=customer, amount="100", currency="USD", exchange_rate="7.100000", kind="customer_receipt"))
rows = [root, root.split_rows.get()]
voucher = {"type": "SYNTHETIC_BANK_VOUCHER_NOT_REAL", "original_currency": "USD", "original_amount": "100.00", "bank_net_cny": "705.00", "included_fee_cny": "5.00", "date": "2026-10-19", "reference": "P2B-FIX-02-BANK-01"}
voucher_bytes = json.dumps(voucher, indent=2, ensure_ascii=False).encode()
(out / "synthetic-bank-voucher.json").write_bytes(voucher_bytes)
(out / "fixture.json").write_text(json.dumps({"customer": customer.pk, "order": order.pk, "sources": [row.pk for row in rows], "voucher_sha256": hashlib.sha256(voucher_bytes).hexdigest(), "voucher": voucher}, ensure_ascii=False, indent=2), encoding="utf-8")
(out / "fixture-legacy-before.json").write_text(json.dumps({"order": list(Order.objects.values()), "payment_plans": list(PaymentPlan.objects.values()), "transactions": list(order.transactions.values())}, sort_keys=True, indent=2, default=str), encoding="utf-8")
assert RmbCashEvent.objects.count() == 0 and CashSourceAllocation.objects.count() == 0
print(json.dumps({"FIXTURE_SETUP": {"database": settings.DATABASES["default"]["NAME"], "order": order.pk, "sources": [row.pk for row in rows], "bank_accounts": ["SYNTH-FX-02", "SYNTH-CNY-02"], "voucher": voucher}}, ensure_ascii=False))
