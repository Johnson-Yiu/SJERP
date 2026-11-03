"""Synthetic Chrome fixture/inspection; refuses non-runner databases."""
import json
import os
from datetime import date
from pathlib import Path
import sys
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))
import django
django.setup()
from django.conf import settings
from django.apps import apps
from django.db import transaction
from test_support.isolated_runtime import verify_isolated_runtime
from crm.models import Customer, Order, Product, PurchaseOrder, SKU, Supplier

verify_isolated_runtime(settings=settings, database_must_exist=True)

if sys.argv[1] == "snapshot":
    # Full persisted values, not counts: useful for rejected writes and cancel.
    data = {model._meta.label: list(model.objects.order_by("pk").values())
            for model in apps.get_app_config("crm").get_models()}
    print(json.dumps(data, default=str, ensure_ascii=False))
elif sys.argv[1] == "seed":
    with transaction.atomic():
        tag = "C039-" + uuid4().hex[:8]
        customer = Customer.objects.create(code=tag, name=tag + " 合成客户")
        supplier_code = uuid4().hex[:2].upper()
        while Supplier.objects.filter(code=supplier_code).exists():
            supplier_code = uuid4().hex[:2].upper()
        supplier = Supplier.objects.create(code=supplier_code, name=tag + " 合成供应商")
        product = Product.objects.create(code=tag, name=tag + " 合成商品")
        sku = SKU.objects.create(product=product, sku=tag, unit="件")
        orders = [Order.objects.create(order_no=tag + f"-SO-{i}", customer=customer,
                  order_date=date(2026, 11, 3), status="confirmed", currency="CNY", exchange_rate=1)
                  for i in range(2)]
        result = {"orders": [order.pk for order in orders], "purchases": {}}
        for kind in ("new", "legacy", "zero"):
            purchase = PurchaseOrder.objects.create(purchase_no=tag + "-" + kind,
                supplier=supplier, order_date=date(2026, 11, 3), status="ordered", currency="CNY", exchange_rate=1)
            items = [purchase.items.create(sku=sku, quantity=10, unit_price=price)
                     for price in ([0, 0] if kind == "zero" else [1000, 100])]
            if kind == "legacy":
                purchase.additional_costs = [{"name": "合成历史运费", "amount": "1000.00", "method": "quantity"}]
                purchase.save(update_fields=["additional_costs"])
            result["purchases"][kind] = {"id": purchase.pk, "no": purchase.purchase_no, "items": [item.pk for item in items]}
        print(json.dumps(result, ensure_ascii=False))
else:
    raise SystemExit("Expected seed or snapshot")
