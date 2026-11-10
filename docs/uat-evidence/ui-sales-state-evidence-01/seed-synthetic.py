"""Seed only the current marked sales evidence database."""
import json
import os
from datetime import date
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))
if os.environ.get("DJANGO_SETTINGS_MODULE") != "test_support.isolated_settings":
    raise RuntimeError("This fixture requires the isolated browser runner.")

import django

django.setup()

from crm.models import Customer, Order, OrderItem, Product, Quote, QuoteItem, SKU
from django.conf import settings
from test_support.isolated_runtime import verify_isolated_runtime

verify_isolated_runtime(settings=settings, database_must_exist=True)
customer = Customer.objects.get(pk=int(sys.argv[1]))
if not customer.name.startswith("SYNTH-SALES "):
    raise RuntimeError("Expected the synthetic browser-created customer.")

product = Product.objects.create(code="SYNTH-SALES-LIGHT", name="Synthetic commercial lighting")
quote = Quote.objects.create(
    quote_no="SYNTH-SALES-QUOTATION-20261110-INTERNATIONAL-PROJECT-00000001",
    customer=customer, buyer_company_name=customer.name, quote_date=date(2026, 11, 10),
)
order = Order.objects.create(
    order_no="SYNTH-SALES-ORDER-20261110-00000000001", customer=customer,
    quote=quote, order_date=date(2026, 11, 10),
)
for index in range(1, 5):
    sku = SKU.objects.create(
        sku=f"SYNTH-SALES-SKU-{index:03d}", product=product, sales_model=f"SYNTH-MODEL-{index}",
        unit="pcs", default_price="12.50",
    )
    fields = {
        "sku": sku, "sku_code_snapshot": sku.sku, "quantity": index * 10, "unit_price": "12.50",
        "description": "Synthetic commercial lighting — long item description for wrapped table cells",
    }
    QuoteItem.objects.create(quote=quote, **fields)
    fields.pop("description")
    OrderItem.objects.create(order=order, **fields)

print(json.dumps({"quote": quote.pk, "order": order.pk, "lines": 4}))
