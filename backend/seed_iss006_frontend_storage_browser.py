import hashlib
import json
import os
from datetime import date
from pathlib import Path

import django

django.setup()

from django.conf import settings
from crm.models import Customer, InventoryMovement, Order, Product, PurchaseOrder, SKU, Supplier
from crm.services.fulfillment import allocate_order
from test_support.isolated_runtime import verify_isolated_runtime


verify_isolated_runtime(settings=settings, database_must_exist=True)
evidence_dir = Path(os.environ["ISS006_STORAGE_EVIDENCE_DIR"])
evidence_dir.mkdir(parents=True, exist_ok=True)
run_suffix = os.environ["ISOLATED_TEST_RUN_ID"].replace("-", "")[:8].upper()
today = date.today()
customer = Customer.objects.create(code=f"I6C{run_suffix}", name=f"ISS-006 Chrome Buyer {run_suffix}")
supplier_code_alphabet = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
supplier_code_space = len(supplier_code_alphabet) ** 2
supplier_code_start = (
    int.from_bytes(hashlib.sha256(run_suffix.encode("ascii")).digest()[:4], "big")
    % supplier_code_space
)
for supplier_code_offset in range(supplier_code_space):
    supplier_code_value = (supplier_code_start + supplier_code_offset) % supplier_code_space
    supplier_code = (
        supplier_code_alphabet[supplier_code_value // len(supplier_code_alphabet)]
        + supplier_code_alphabet[supplier_code_value % len(supplier_code_alphabet)]
    )
    if not Supplier.objects.filter(code=supplier_code).exists():
        break
else:
    raise RuntimeError("No unused two-character Supplier.code remains for isolated ISS-006 browser fixtures")
supplier = Supplier.objects.create(code=supplier_code, name=f"ISS-006 Chrome Supplier {run_suffix}")

case_names = ["property-getter", "get-item", "set-item-recovery", "remove-item-recovery", "lost-response"]
fixture = {"run_id": os.environ["ISOLATED_TEST_RUN_ID"], "database": str(settings.DATABASES["default"]["NAME"]), "receive": {}, "ship": {}}

for operation, cases in (("receive", fixture["receive"]), ("ship", fixture["ship"])):
    for index, case_name in enumerate(case_names, start=1):
        suffix = f"{run_suffix}{operation[0].upper()}{index}"
        product = Product.objects.create(code=f"I6P{suffix}", name=f"ISS-006 Chrome {operation} {case_name}")
        sku = SKU.objects.create(product=product, sku=f"I6SKU{suffix}")
        order = Order.objects.create(
            order_no=f"I6SO{suffix}", customer=customer, order_date=today, status="confirmed", currency="CNY"
        )
        order_item = order.items.create(sku=sku, quantity="5", unit_price="10")
        row = {"order_id": order.pk, "order_item_id": order_item.pk, "sku_id": sku.pk, "sku_code": sku.sku}

        if operation == "receive":
            purchase = PurchaseOrder.objects.create(
                purchase_no=f"I6PO{suffix}", supplier=supplier, order=order, order_date=today,
                status="ordered", currency="CNY", exchange_rate="1",
            )
            purchase_item = purchase.items.create(sku=sku, quantity="5", unit_price="4")
            row.update(purchase_id=purchase.pk, purchase_no=purchase.purchase_no, purchase_item_id=purchase_item.pk)
        else:
            InventoryMovement.objects.create(
                movement_no=f"I6IN{suffix}", movement_date=today, type="purchase_in", sku=sku,
                quantity="5", warehouse="默认仓", source_type="manual", is_automatic=False,
            )
            allocate_order(order)

        cases[case_name] = row

(evidence_dir / "fixture.json").write_text(json.dumps(fixture, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"fixture": str(evidence_dir / "fixture.json"), "database": fixture["database"], "case_count": 10}, ensure_ascii=False))
