"""Prove existing D2 source identities and document rows survive the H1 migration."""
import os
from datetime import date
from decimal import Decimal

from crm.models import Customer, HistoryTakeoverApplication, HistoryTakeoverGroup, HistoryTakeoverSourceRecord, Order, OrderItem, Product, SKU

source_key = {"source_system": "Synthetic D2", "record_type": "销售明细", "source_record_id": "D2-SALE:1"}
facts = {"source_order_id": "D2-SALE", "source_line_id": "1", "sku_code": "D2-OLD", "sku_name_snapshot": "旧历史商品"}
snapshot = {"source": facts, "resolved": facts}

if os.environ["H1_MIGRATION_PHASE"] == "seed":
    customer = Customer.objects.create(code="D2-C", name="合成客户")
    product = Product.objects.create(code="D2-P", name="合成旧商品", sales_model_prefix="D2P")
    sku = SKU.objects.create(product=product, sku="D2-OLD", display_name_cn="合成旧 SKU", unit="pcs")
    order = Order.objects.create(order_no="D2-SALE", customer=customer, order_date=date(2024, 1, 1),
                                 status="historical", historical_only=True, currency="CNY")
    line = OrderItem.objects.create(order=order, sku=sku, quantity=2, unit_price=35, display_name_snapshot="旧历史商品")
    app = HistoryTakeoverApplication.objects.create(source_file_name="synthetic-d2.xlsx", source_sha256="d" * 64)
    group = HistoryTakeoverGroup.objects.create(application=app, source_system="Synthetic D2",
                                                source_group_id="D2-GROUP", status="executed")
    HistoryTakeoverSourceRecord.objects.create(
        **source_key, group=group, source_snapshot=snapshot, target_model="crm.OrderItem", target_id=line.pk,
    )
    print("D2 legacy line and source identity seeded before upgrade.")
else:
    from crm.history_products import document_product_rows

    source = HistoryTakeoverSourceRecord.objects.get(**source_key)
    line = OrderItem.objects.get(pk=source.target_id)
    rows = document_product_rows(line.order)
    assert source.source_snapshot == snapshot
    assert source.target_model == "crm.OrderItem"
    assert line.order.total_amount == Decimal("70")
    assert len(rows) == 1 and rows[0]["name"] == "旧历史商品" and rows[0]["sku"]["code"] == "D2-OLD"
    assert not line.order.archived_lines.exists()
    print("Existing D2 facts, source target and total survived the H1 migration.")
