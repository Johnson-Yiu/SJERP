"""Seed synthetic quote fixtures only in the Q6 isolated database."""
import json
from datetime import date

import django

django.setup()

from django.conf import settings
from crm.models import Customer, InventoryMovement, Product, SKU, SKUTradeUnit
from test_support.isolated_runtime import verify_isolated_runtime

verify_isolated_runtime(settings=settings, database_must_exist=True)

customer = Customer.objects.create(code="Q6-CUSTOMER", name="Q6 Synthetic Buyer", country="Germany", address="Q6 Synthetic Address")
product = Product.objects.create(code="Q6-PRODUCT", name="Q6 Synthetic Lamp")
for suffix, stock in (("BOX", 15), ("EACH", 20)):
    sku = SKU.objects.create(product=product, sku=f"Q6-{suffix}", sales_model=f"Q6-{suffix}-MODEL", unit="pcs", default_price="12.50")
    InventoryMovement.objects.create(movement_no=f"Q6-STOCK-{suffix}", movement_date=date.today(), type="other_in", sku=sku, quantity=stock, warehouse="默认仓")
    if suffix == "BOX":
        box = SKUTradeUnit.objects.create(sku=sku, name="Q6 Box", unit="box", factor=10)
print(json.dumps({"customer": customer.pk, "box": box.pk}))
