"""FIXTURE_SETUP only. Refuse every database except this disposable file."""
import hashlib
import json
import os
import sys
from datetime import date
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()
from django.conf import settings
from django.apps import apps
from django.core.serializers.json import DjangoJSONEncoder
from crm.models import Customer, Order, PaymentPlan, Product, SKU, RmbCashEvent, CashSourceAllocation
from crm.services.finance import record_transaction

assert Path(settings.DATABASES["default"]["NAME"]).name == "r1-fin-p2-a-isolated.sqlite3"
assert not Customer.objects.exists(), "Only a new synthetic DB is permitted; no cleanup/rewrite"
p = Path(__file__).resolve().parent
customer = Customer.objects.create(code="P2A-SYNTH-C", name="P2A synthetic customer")
sku = SKU.objects.create(sku="P2A-SYNTH-SKU", product=Product.objects.create(code="P2A-SYNTH-P", name="Synthetic product"))
order = Order.objects.create(order_no="P2A-SYNTH-O", customer=customer, currency="USD", exchange_rate=7, status="confirmed", order_date=date(2026, 10, 18))
order.items.create(sku=sku, quantity=1, unit_price=100)
for amount in [30, 70]: PaymentPlan.objects.create(order=order, direction="receivable", currency="USD", planned_amount=amount)
root = record_transaction(dict(transaction_no="P2A-SYNTH-T", order=order, customer=customer, amount="100", currency="USD", exchange_rate="7", kind="customer_receipt"))
rows = [root, root.split_rows.get()]
voucher = {"type": "SYNTHETIC_BANK_VOUCHER_NOT_REAL", "original_currency": "USD", "original_amount": "100.00", "bank_net_cny": "705.00", "included_fee_cny": "5.00", "date": "2026-10-18", "reference": "P2A-SYNTH-BANK-01"}
data = json.dumps(voucher, indent=2).encode()
(p / "synthetic-bank-voucher.json").write_bytes(data)
payload = dict(event_no="P2A-SYNTH-EVENT-01", request_key="P2A-SYNTH-REQUEST-01", kind="fx_settlement", currency="USD", direction="income", bank_date="2026-10-18", bank_net_amount="705.00", fee_mode="included", fee_amount="5.00", source_account="SYNTH_FX", rmb_account="SYNTH_CNY", bank_reference=voucher["reference"], evidence_reference="P2A-SYNTH-VOUCHER-01", evidence_sha256=hashlib.sha256(data).hexdigest(), evidence_note="Synthetic bank voucher manually checked, not production approval", quoted_rate="7.100000", sources=[dict(transaction_id=r.pk, amount=format(r.amount, ".2f"), verified=True) for r in rows])
(p / "http-request.json").write_text(json.dumps(payload, indent=2), encoding="utf8")
old = {m.__name__: list(m.objects.order_by("pk").values()) for m in apps.get_app_config("crm").get_models() if m not in {RmbCashEvent, CashSourceAllocation}}
(p / "legacy-before.json").write_text(json.dumps(old, cls=DjangoJSONEncoder, sort_keys=True, indent=2), encoding="utf8")
print("FIXTURE_SETUP", root.pk, [(r.pk, str(r.amount)) for r in rows], "bank events", RmbCashEvent.objects.count())
