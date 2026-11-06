import json, os, sys
from django.core.serializers.json import DjangoJSONEncoder
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'test_support.isolated_settings')
import django
django.setup()
from django.conf import settings
from test_support.isolated_runtime import verify_isolated_runtime
verify_isolated_runtime(settings=settings, database_must_exist=True)
from crm.models import Order, PurchaseOrder, Transaction, GoodsReceipt, Shipment, ShipmentItem, InventoryMovement, PaymentPlan
from crm.party_document_details_models import PartyDocumentDetailsStorage
o, p = map(int, sys.argv[1:3])
def rows(q): return list(q.order_by('pk').values())
data = {'orders':rows(Order.objects.filter(pk=o)), 'purchases':rows(PurchaseOrder.objects.filter(pk=p)),
 'transactions':rows(Transaction.objects.filter(order_id=o) | Transaction.objects.filter(purchase_order_id=p)),
 'plans':rows(PaymentPlan.objects.filter(order_id=o) | PaymentPlan.objects.filter(purchase_order_id=p)),
 'receipts':rows(GoodsReceipt.objects.filter(purchase_item__purchase_order_id=p)),
 'shipments':rows(Shipment.objects.filter(order_id=o)), 'shipment_items':rows(ShipmentItem.objects.filter(shipment__order_id=o)),
 'movements':rows(InventoryMovement.objects.all()), 'details':rows(PartyDocumentDetailsStorage.objects.filter(order_id=o) | PartyDocumentDetailsStorage.objects.filter(purchase_order_id=p))}
print(json.dumps(data, cls=DjangoJSONEncoder, sort_keys=True))

