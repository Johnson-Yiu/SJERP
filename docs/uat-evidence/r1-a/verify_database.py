"""DATABASE_VERIFICATION: read-only Decimal assertions after recorded UI steps."""
import json
from decimal import Decimal as D
from pathlib import Path
from django.conf import settings
from crm.models import Order, PurchaseOrder, Transaction, GoodsReceipt, InventoryMovement, SKU
from crm.services.fulfillment import sku_metrics

assert Path(settings.DATABASES['default']['NAME']).resolve() == (settings.BASE_DIR/'r1a-isolated.sqlite3').resolve()
order = Order.objects.get(order_no='R1A-USD500')
purchase = PurchaseOrder.objects.get(purchase_no='PO-2026-00001')
assert order.status == 'completed'
assert order.total_amount == D('500') and order.paid_amount == D('340')
assert sum((p.remaining_amount for p in order.payment_plans.all()),D('0')) == D('160')
assert purchase.order_id is None and purchase.status == 'completed'
assert purchase.total_amount == D('265') and purchase.paid_amount == D('265')
assert all(p.remaining_amount == 0 for p in purchase.payment_plans.all())
receipts = list(GoodsReceipt.objects.order_by('pk'))
assert len(receipts) == 4 and sum(r.reversal_inventory_movement_id is not None for r in receipts) == 2
for r in receipts:
    if r.reversal_inventory_movement_id:
        assert r.inventory_movement.quantity == r.reversal_inventory_movement.quantity
        assert r.inventory_movement.unit_cost == r.reversal_inventory_movement.unit_cost
txs = list(Transaction.objects.order_by('pk'))
for t in txs:
    assert t.rmb_amount == (t.amount*t.exchange_rate).quantize(D('0.0001'))
assert sum((t.amount for t in txs if t.order_id == order.id),D('0')) == D('340')
assert sum((t.rmb_amount for t in txs if t.order_id == order.id),D('0')) == D('2465')
assert sum((t.rmb_amount for t in txs if t.purchase_order_id == purchase.id),D('0')) == D('1903')
data = {
 'type':'DATABASE_VERIFICATION', 'database':str(settings.DATABASES['default']['NAME']),
 'order': {'status':order.status,'total':order.total_amount,'paid':order.paid_amount,'plans':list(order.payment_plans.values())},
 'purchase':{'status':purchase.status,'order_id':purchase.order_id,'total':purchase.total_amount,'paid':purchase.paid_amount,'items':list(purchase.items.values()),'plans':list(purchase.payment_plans.values())},
 'transactions':list(Transaction.objects.values()),'receipts':list(GoodsReceipt.objects.values()),
 'movements':list(InventoryMovement.objects.values()),
 'inventory':{s.sku:sku_metrics(s) for s in SKU.objects.all()},
}
out=settings.BASE_DIR.parent/'docs/uat-evidence/r1-a/database-checkpoint.json'
out.write_text(json.dumps(data,default=str,ensure_ascii=False,indent=2),encoding='utf-8')
print('DATABASE_VERIFICATION: exact Decimal assertions passed; '+str(out))
