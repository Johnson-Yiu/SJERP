"""Create synthetic, isolated SQLite data for R1-REPAIR-03 browser evidence."""

import json
import os
from datetime import date
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
database_url = os.environ.get("DATABASE_URL", "").strip()
if not database_url.startswith("sqlite:///"):
    raise RuntimeError("R1-REPAIR-03 requires an isolated SQLite database")

sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django

django.setup()

from django.core.management import call_command
from crm.models import Contact, Customer, Order, OrderItem, Product, ProductCategory, PurchaseOrder, SKU, Supplier

if os.environ.get("ISOLATED_TEST_RUN_ID"):
    from django.conf import settings
    from test_support.isolated_runtime import verify_isolated_runtime

    verify_isolated_runtime(settings=settings, database_must_exist=True)
elif not database_url.rsplit("/", 1)[-1].startswith("r1-repair-03-"):
    raise RuntimeError("R1-REPAIR-03 requires an explicitly selected isolated SQLite database")

call_command("migrate", interactive=False, verbosity=0)

customer = Customer.objects.create(
    code="R1-REPAIR-029-C",
    name="ISS029 R1 Snapshot Buyer",
    country="Germany",
    address="Original Berlin Address",
)
contact = Contact.objects.create(
    customer=customer,
    name="Original Primary",
    email="primary@example.com",
    phone="+49 111",
    is_primary=True,
)
product = Product.objects.create(code="R1-REPAIR-P", name="R1 Repair Panel")
sku = SKU.objects.create(sku="ISS029-SKU", product=product, sales_model="SJ-029", unit="pcs", default_price="10.00")

history_customer = Customer.objects.create(code="R1-REPAIR-HC", name="Chrome历史客户", country="中国")
history_supplier = Supplier.objects.create(code="R1-REPAIR-HS", name="Chrome历史供应商", country="中国")
category = ProductCategory.objects.create(name="R1历史分类")
history_product = Product.objects.create(code="R1-REPAIR-HP", name="Chrome历史灯具", category=category)
history_sku = SKU.objects.create(sku="CHROME-SKU", product=history_product, display_name_cn="Chrome历史灯具", unit="pcs")
order = Order.objects.create(
    order_no="R1-REPAIR-HSO",
    customer=history_customer,
    order_date=date(2020, 1, 2),
    status="historical",
    historical_only=True,
    currency="CNY",
    exchange_rate=1,
)
OrderItem.objects.create(order=order, sku=history_sku, quantity=17, unit_price=80, cost_price=0, display_name_snapshot="Chrome历史灯具")
purchase = PurchaseOrder.objects.create(
    purchase_no="R1-REPAIR-HPO",
    supplier=history_supplier,
    order_date=date(2020, 1, 3),
    status="historical",
    historical_only=True,
    currency="CNY",
    exchange_rate=1,
)
purchase.items.create(sku=history_sku, quantity=27, unit_price=30, display_name_snapshot="Chrome历史灯具")

out = Path(os.environ.get("R1_REPAIR_EVIDENCE_DIR", Path(__file__).resolve().parent)).resolve()
out.mkdir(parents=True, exist_ok=True)
(out / "fixture.json").write_text(
    json.dumps(
        {
            "customer": customer.pk,
            "contact": contact.pk,
            "sku": sku.pk,
            "database": database_url,
            "development_identity": True,
            "historical_order": order.pk,
            "historical_purchase": purchase.pk,
        },
        indent=2,
    ),
    encoding="utf-8",
)
print(json.dumps({"customer": customer.pk, "contact": contact.pk, "sku": sku.pk, "historical_order": order.pk, "historical_purchase": purchase.pk}))
