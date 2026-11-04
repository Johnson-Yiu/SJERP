"""Seed/verify representative data on the explicitly named disposable PG17 upgrade DB."""
import os
from datetime import date
from decimal import Decimal
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

config = connection.settings_dict
if connection.vendor != "postgresql" or config["HOST"] != "127.0.0.1" or str(config["PORT"]) != "9037" or config["NAME"] != "sunjack_history_upgrade_legacy" or config["USER"] != "sunjack_test":
    raise RuntimeError("Refusing to operate outside the named disposable PostgreSQL upgrade DB")
with connection.cursor() as cursor:
    cursor.execute("SELECT current_database(), current_user, current_setting('server_version_num')")
    db, user, version = cursor.fetchone()
if (db, user) != ("sunjack_history_upgrade_legacy", "sunjack_test") or not (170000 <= int(version) < 180000):
    raise RuntimeError("Database or PostgreSQL version mismatch")
mode = os.environ.get("HISTORY_UPGRADE_PHASE")
if mode == "seed":
    apps = MigrationExecutor(connection).loader.project_state([("crm", "0103_merge_finance_and_history")]).apps
    Customer, Product, SKU, Order, Movement = (apps.get_model("crm", name) for name in ("Customer", "Product", "SKU", "Order", "InventoryMovement"))
    if Customer.objects.exists() or Movement.objects.exists():
        raise RuntimeError("Expected an empty synthetic upgrade DB")
    customer = Customer.objects.create(code="SYN-UP-C", name="Synthetic pre-upgrade customer")
    product = Product.objects.create(code="SYN-UP-P", name="Synthetic pre-upgrade product")
    sku = SKU.objects.create(sku="SYN-UP-SKU", product=product)
    order = Order.objects.create(order_no="SYN-UP-SO", customer=customer, order_date=date(2025, 1, 1), status="draft")
    Movement.objects.create(movement_no="SYN-UP-MOV", movement_date=date(2025, 1, 2), type="adjust_in", sku=sku, quantity=Decimal("7"), warehouse="Synthetic legacy warehouse", order=order)
    print("PASS seeded pre-0104 synthetic customer, SKU, order, and stock movement")
elif mode == "verify":
    from crm.models import Customer, HistoryInventoryBaseline, InventoryMovement, Order, SKU
    movement = InventoryMovement.objects.get(movement_no="SYN-UP-MOV")
    assert Customer.objects.get(code="SYN-UP-C").name == "Synthetic pre-upgrade customer"
    assert SKU.objects.get(sku="SYN-UP-SKU").pk == movement.sku_id
    assert Order.objects.get(order_no="SYN-UP-SO").pk == movement.order_id
    assert movement.quantity == Decimal("7") and movement.warehouse == "Synthetic legacy warehouse"
    assert movement.warehouse_type == "自有仓" and movement.lot_reference == ""
    assert not HistoryInventoryBaseline.objects.exists()
    print("PASS pre-existing synthetic customer, SKU, order, warehouse and quantity preserved after upgrade")
else:
    raise RuntimeError("HISTORY_UPGRADE_PHASE must be seed or verify")
