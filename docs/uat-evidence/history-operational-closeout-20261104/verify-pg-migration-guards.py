"""Verify downgrade guards on the explicitly named disposable PG17 database only."""
from datetime import date
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from crm.models import (Customer, HistoryOperationalContract, HistoryTakeoverApplication,
    HistoryTakeoverGroup, HistoryTakeoverSourceRecord, InventoryMovement, Order,
    Product, PurchaseOrder, SKU, Supplier)

config = connection.settings_dict
if connection.vendor != "postgresql" or config["HOST"] != "127.0.0.1" or str(config["PORT"]) != "9037" or config["NAME"] != "sunjack_history_isolated" or config["USER"] != "sunjack_test":
    raise RuntimeError("Refusing to operate outside the named disposable PostgreSQL cluster")
with connection.cursor() as cursor:
    cursor.execute("SELECT current_database(), current_user, current_setting('server_version_num')")
    db, user, version = cursor.fetchone()
if (db, user) != ("sunjack_history_isolated", "sunjack_test") or not (170000 <= int(version) < 180000):
    raise RuntimeError("PostgreSQL version or database identity does not match the UAT cluster")
if HistoryTakeoverApplication.objects.exists() or InventoryMovement.objects.exists() or PurchaseOrder.objects.exists():
    raise RuntimeError("Expected a newly migrated synthetic database with no business records")

app = HistoryTakeoverApplication.objects.create(source_file_name="synthetic-guard.xlsx", source_sha256="f" * 64)
group = HistoryTakeoverGroup.objects.create(application=app, source_group_id="synthetic-guard", source_system="synthetic-guard", coverage_status="complete", truth_status="真实")
source = HistoryTakeoverSourceRecord.objects.create(group=group, source_system="synthetic-guard", record_type="销售订单", source_record_id="synthetic-guard")
customer = Customer.objects.create(code="GUARD-HT", name="Synthetic migration guard")
order = Order.objects.create(order_no="SYN-GUARD-SO", customer=customer, order_date=date(2025, 1, 1), status="historical", historical_only=True)
link = HistoryOperationalContract.objects.create(group=group, source=source, archived_order=order, settlement_order=order,
    cutover_date=date(2025, 1, 1), balance_mode="balance_only", opening_balance=0, currency="USD", evidence_reference="synthetic://guard")
supplier = Supplier.objects.create(code="G1", name="Synthetic migration supplier")
purchase = PurchaseOrder.objects.create(purchase_no="SYN-GUARD-PO", supplier=supplier, order_date=date(2025, 1, 1), history_finance_mode=True)
product = Product.objects.create(code="GUARD-P", name="Synthetic migration product")
sku = SKU.objects.create(sku="GUARD-SKU", product=product)
movement = InventoryMovement.objects.create(movement_no="SYN-GUARD-MOV", movement_date=date(2025, 1, 1), type="adjust_in", sku=sku,
    quantity=1, warehouse="Synthetic warehouse", warehouse_type="第三方仓", lot_reference="SYN-LOT")

latest = MigrationExecutor(connection).loader.graph.leaf_nodes()
def refuse(target, expected):
    try:
        MigrationExecutor(connection).migrate([("crm", target)])
    except RuntimeError as error:
        if expected not in str(error):
            raise
        print(f"PASS {target}: {error}")
    else:
        raise AssertionError(f"Downgrade to {target} unexpectedly succeeded")
    finally:
        MigrationExecutor(connection).migrate(latest)

refuse("0106_historical_purchase_balance_mode", "库存流水已有仓库类型或批次")
movement.warehouse_type, movement.lot_reference = "自有仓", ""
movement.save(update_fields=["warehouse_type", "lot_reference"])
refuse("0105_historical_operational_contract", "Refusing to remove historical purchase balance semantics")
purchase.history_finance_mode = False
purchase.save(update_fields=["history_finance_mode"])
refuse("0104_historical_inventory_baseline", "Refusing to remove recorded historical operational contracts")
assert HistoryOperationalContract.objects.filter(pk=link.pk).exists()
assert InventoryMovement.objects.filter(pk=movement.pk).exists()
print("PASS synthetic source data preserved and latest migrations restored")
