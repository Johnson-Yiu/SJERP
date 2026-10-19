"""FIXTURE_SETUP only: append disposable, unused USD sources for screenshot capture."""
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

from crm.models import Customer, Order, PaymentPlan, Product, SKU
from crm.services.finance import record_transaction

customer = Customer.objects.create(code="P2B-FIX-C", name="P2B FIX 合成客户")
product = Product.objects.create(code="P2B-FIX-P", name="P2B FIX 合成产品")
sku = SKU.objects.create(sku="P2B-FIX-SKU", product=product)
order = Order.objects.create(order_no="P2B-FIX-O", customer=customer, currency="USD", exchange_rate="7.100000", status="confirmed", order_date=date(2026, 10, 19))
order.items.create(sku=sku, quantity=1, unit_price="100")
PaymentPlan.objects.create(order=order, direction="receivable", currency="USD", planned_amount="30")
PaymentPlan.objects.create(order=order, direction="receivable", currency="USD", planned_amount="70")
root = record_transaction(dict(transaction_no="P2B-FIX-T", order=order, customer=customer, amount="100", currency="USD", exchange_rate="7.100000", kind="customer_receipt"))
rows = [root, root.split_rows.get()]
print(json.dumps({"order": order.pk, "sources": [row.pk for row in rows]}, ensure_ascii=False))
