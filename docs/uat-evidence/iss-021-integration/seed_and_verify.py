"""Synthetic local evidence only; run through manage.py shell with runpy."""
import hashlib
import json
import os
from datetime import date
from decimal import Decimal
from pathlib import Path

from crm.models import (
    Customer, Product, SKU, Supplier, Order, OrderItem, PaymentPlan, PurchaseOrder,
    PurchaseOrderItem, PurchaseCostAllocation, GoodsReceipt, Shipment, ShipmentItem,
    InventoryMovement, Transaction, OrderQuantityAdjustment,
)
from crm.services.fulfillment import record_receipt, confirm_shipment, signed_inventory_quantity
from crm.services.finance import record_transaction
from crm.services.order_lifecycle import confirm_order

evidence = Path(__file__).resolve().parent
protected = [PurchaseOrder, PurchaseOrderItem, PurchaseCostAllocation, GoodsReceipt, Shipment, ShipmentItem, InventoryMovement, Transaction]

def facts():
    return {model._meta.label: list(model.objects.order_by("pk").values()) for model in protected}

def canonical(value):
    return json.dumps(value, default=str, ensure_ascii=False, sort_keys=True)

if os.environ.get("ISS021_EVIDENCE_MODE", "seed") == "seed":
    assert not Order.objects.exists(), "Use only a fresh isolated database."
    customer = Customer.objects.create(code="ISS021-C", name="ISS021 原确认客户", address="原合同地址")
    supplier = Supplier.objects.create(code="ISS021-S", name="ISS021 采购供应商")
    product = Product.objects.create(code="ISS021-P", name="数量变更验收灯具")
    ids = []
    for index, shipped, paid in ((1, 50, 200), (2, 70, 200), (3, 0, 900)):
        sku = SKU.objects.create(product=product, sku=f"ISS021-SKU-{index}", display_name_cn=f"数量变更灯具 {index}", unit="pcs")
        order = Order.objects.create(order_no=f"SO-ISS021-{index}", customer=customer, order_date=date(2026, 10, 25), currency="USD", exchange_rate=1)
        item = OrderItem.objects.create(order=order, sku=sku, quantity=100, unit_price=10)
        confirm_order(order)
        order.refresh_from_db()
        remaining = Decimal(paid)
        for plan in order.payment_plans.exclude(status="cancelled").order_by("pk"):
            amount = min(remaining, plan.planned_amount)
            if amount:
                record_transaction({"plan": plan, "amount": amount, "currency": "USD", "exchange_rate": Decimal(1), "category": "客户收款"})
                remaining -= amount
        assert remaining == 0
        purchase = PurchaseOrder.objects.create(
            purchase_no=f"PO-ISS021-{index}", order=order, supplier=supplier,
            order_date=date(2026, 10, 25), status="ordered", currency="USD", exchange_rate=1,
        )
        purchase_item = purchase.items.create(sku=sku, quantity=100, unit_price=7)
        PurchaseCostAllocation.objects.update_or_create(
            purchase_item=purchase_item, target_type="order", order=order, defaults={"quantity": 100},
        )
        record_receipt(purchase_item, {"quantity": "100", "unit_cost": "7", "receipt_date": date(2026, 10, 25)})
        if shipped:
            confirm_shipment(order, {"shipment_date": date(2026, 10, 25), "items": [{"order_item": item.pk, "quantity": str(shipped)}]})
        ids.append({"order": order.pk, "item": item.pk, "sku": sku.pk, "shipped": shipped, "paid": paid})
    customer.name = "ISS021 主档更名后"
    customer.address = "当前主档地址"
    customer.save()
    (evidence / "database-before.json").write_text(canonical(facts()), encoding="utf-8")
    (evidence / "seed.json").write_text(canonical(ids), encoding="utf-8")
    print(canonical({"seed": ids, "protected_hash": hashlib.sha256(canonical(facts()).encode()).hexdigest()}))
else:
    before = json.loads((evidence / "database-before.json").read_text(encoding="utf-8"))
    after = json.loads(canonical(facts()))
    result = {
        "protected_facts_unchanged": before == after,
        "before_hash": hashlib.sha256(canonical(before).encode()).hexdigest(),
        "after_hash": hashlib.sha256(canonical(after).encode()).hexdigest(),
        "orders": [{
            "id": order.pk, "order_no": order.order_no, "quantity_change_version": order.quantity_change_version,
            "customer_name_snapshot": order.customer_name_snapshot, "customer_address_snapshot": order.customer_address_snapshot,
            "current_customer_name": order.customer.name, "total_amount": str(order.total_amount), "paid_amount": str(order.paid_amount),
            "plans": list(order.payment_plans.values("id", "planned_amount", "settled_amount", "status")),
            "items": [{
                "id": item.pk, "quantity": str(item.quantity),
                "reserved": list(item.reservations.values_list("quantity", flat=True)),
                "stock": str(signed_inventory_quantity(item.sku)),
            } for item in order.items.all()],
            "adjustments": list(order.quantity_adjustments.values()),
        } for order in Order.objects.select_related("customer").order_by("pk")],
    }
    (evidence / "database-after.json").write_text(canonical(result), encoding="utf-8")
    print(canonical(result))
    assert result["protected_facts_unchanged"]
