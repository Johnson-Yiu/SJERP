"""Seed disposable records for the ISS-006 real-browser UAT.

This script only creates fixtures in the explicitly named isolated SQLite DB.
Business transitions under test are performed from the browser UI.
"""
import json
import os
from datetime import date
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from crm.models import (
    Customer,
    Order,
    OrderItem,
    Product,
    ProductCategory,
    PurchaseOrder,
    PurchaseOrderItem,
    SKU,
    Supplier,
)
from crm.services.purchase_lifecycle import place_purchase_order


EXPECTED_DB = (settings.BASE_DIR / "iss006-chrome-uat.sqlite3").resolve()
assert Path(settings.DATABASES["default"]["NAME"]).resolve() == EXPECTED_DB, "Refusing any non-UAT database"
assert not Product.objects.exists() and not Supplier.objects.exists() and not SKU.objects.exists(), "Refusing non-empty UAT database"
password = os.environ.get("ISS006_UAT_PASSWORD")
assert password, "ISS006_UAT_PASSWORD must be supplied only in the local process environment"

today: date = timezone.localdate()
ids = {"sku": {}, "purchase": {}, "item": {}, "order": {}}

with transaction.atomic():
    category = ProductCategory.objects.create(name="ISS006 UAT 合成分类")
    product = Product.objects.create(
        code="ISS006-UAT-PRODUCT",
        name="ISS006 UAT 合成灯具",
        category=category,
    )
    skus = {
        "receipt": SKU.objects.create(product=product, sku="ISS006-UAT-REC", display_name_cn="ISS006 UAT 收货冲销灯具", unit="pcs"),
        "shipment": SKU.objects.create(product=product, sku="ISS006-UAT-SHIP", display_name_cn="ISS006 UAT 发货恢复灯具", unit="pcs"),
        "gift": SKU.objects.create(product=product, sku="ISS006-UAT-GIFT", display_name_cn="ISS006 UAT 赠品超收灯具", unit="pcs"),
    }
    ids["sku"] = {key: value.pk for key, value in skus.items()}

    supplier = Supplier.objects.create(code="U6", name="ISS006 UAT 合成供应商")
    customer = Customer.objects.create(code="ISS006-UAT-C", name="ISS006 UAT 合成客户", status="customer")
    order = Order.objects.create(
        order_no="ISS006-UAT-SO-SHIP",
        customer=customer,
        order_date=today,
        expected_ship_date=today,
        currency="USD",
        exchange_rate="1",
        status="confirmed",
    )
    order_item = OrderItem.objects.create(
        order=order,
        sku=skus["shipment"],
        quantity="4",
        unit_price="50",
    )
    ids["order"] = {"id": order.pk, "item": order_item.pk}

    def create_purchase(key, number, sku, quantity, linked_order=None):
        purchase = PurchaseOrder.objects.create(
            purchase_no=number,
            supplier=supplier,
            order=linked_order,
            order_date=today,
            currency="USD",
            exchange_rate="1",
        )
        item = PurchaseOrderItem.objects.create(
            purchase_order=purchase,
            sku=sku,
            quantity=quantity,
            unit_price="12.50",
        )
        placed = place_purchase_order(purchase)
        ids["purchase"][key] = placed.pk
        ids["item"][key] = item.pk

    create_purchase("receipt", "ISS006-UAT-PO-REC", skus["receipt"], "10")
    create_purchase("shipment", "ISS006-UAT-PO-SHIP", skus["shipment"], "4", order)
    create_purchase("gift", "ISS006-UAT-PO-GIFT", skus["gift"], "2")

    user_model = get_user_model()
    user = user_model.objects.create_superuser(
        username="iss006-uat-synthetic",
        email="iss006-uat-synthetic@example.invalid",
        password=password,
    )
    user.first_name = "ISS006 UAT 合成操作人"
    user.save(update_fields=["first_name"])

output = Path(__file__).with_name("fixture-ids.json")
output.write_text(json.dumps(ids, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"FIXTURE_SETUP PASS: isolated DB={EXPECTED_DB}; synthetic business rows and synthetic admin={user.username}; ids={output}")
