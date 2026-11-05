"""Core chain counterexamples and API regression on synthetic isolated data."""
from datetime import date
from decimal import Decimal as D
import hashlib
import json
import os
from pathlib import Path
import uuid
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework.exceptions import ValidationError as RestValidationError

from crm.models import (AdvanceAllocation, RmbCashEvent, OrderItem, PurchaseOrderItem, ShipmentItem, Customer, FulfillmentIdempotency, GoodsReceipt, InventoryMovement,
    InventoryReservation, OperationLog, Order, PaymentPlan, Product, PurchaseCostAllocation,
    PurchaseOrder, Shipment, SKU, Supplier, SupplierSKU, Transaction)
from crm.services import fulfillment as stock
from crm.services import purchase_costs as costs
from crm.services.order_lifecycle import cancel_order

DAY = date(2026, 11, 5)
LOCATION = {"warehouse": "合成A仓", "warehouse_type": "自有仓", "lot_reference": "LOT-A"}
OTHER = {"warehouse": "合成B仓", "warehouse_type": "第三方仓", "lot_reference": "LOT-B"}


class CoreBusinessFixture:
    def setup_core(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser("core-synthetic-operator", "", None)
        self.client.force_authenticate(self.user)
        self.customer = Customer.objects.create(code="CORE-C", name="合成核心链路客户", country="China")
        self.supplier = Supplier.objects.create(code="CB", name="合成核心链路供应商")
        self.sku = SKU.objects.create(sku="CORE-SKU", product=Product.objects.create(code="CORE-P", name="合成核心商品"))
        self.records = []
        self.addCleanup(self.save_evidence)

    def save_evidence(self):
        if os.environ.get("CORE_BUSINESS_EVIDENCE"):
            root = Path(os.environ["CORE_BUSINESS_EVIDENCE"]).resolve()
            root.mkdir(parents=True, exist_ok=True)
            (root / (hashlib.sha256(self.id().encode()).hexdigest()[:16] + ".json")).write_text(json.dumps({"test": self.id(), "http": self.records}, ensure_ascii=False, default=str, indent=2), encoding="utf-8", newline="\n")

    def post(self, path, body, expected=200, key=None):
        headers = {"HTTP_IDEMPOTENCY_KEY": key or "CORE-" + uuid.uuid4().hex} if path.endswith(("/ship/", "/receive/")) else {}
        r = self.client.post(path, body, format="json", **headers)
        self.records.append({"path": path, "request": body, "status": r.status_code, "body": getattr(r, "data", None)})
        self.assertEqual(r.status_code, expected, getattr(r, "data", None))
        return r.data

    def order(self, quantity="6", status="confirmed"):
        order = Order.objects.create(order_no="CORE-SO-" + uuid.uuid4().hex[:8], customer=self.customer, order_date=DAY, status=status, currency="CNY", exchange_rate=1)
        return order, order.items.create(sku=self.sku, quantity=quantity, unit_price="10")

    def purchase(self, quantity="6"):
        po = PurchaseOrder.objects.create(purchase_no="CORE-PO-" + uuid.uuid4().hex[:8], supplier=self.supplier, order_date=DAY, status="ordered", currency="CNY", exchange_rate=1)
        return po, po.items.create(sku=self.sku, quantity=quantity, unit_price="3")

    def movement(self, quantity, location=LOCATION, kind="adjust_in"):
        return InventoryMovement.objects.create(movement_no="CORE-IM-" + uuid.uuid4().hex[:10], movement_date=DAY, sku=self.sku, quantity=quantity, type=kind, **location)

    def snapshot(self):
        models = (InventoryMovement, InventoryReservation, GoodsReceipt, Shipment, FulfillmentIdempotency,
                  Order, OrderItem, PurchaseOrder, PurchaseOrderItem, ShipmentItem, PurchaseCostAllocation, PaymentPlan, Transaction, AdvanceAllocation, RmbCashEvent, OperationLog)
        result = {m.__name__: list(m.objects.order_by("pk").values()) for m in models}
        self.records.append({"database_snapshot": result})
        return result

    def shipment(self, order, item, quantity, location=LOCATION):
        return {"shipment_date": DAY.isoformat(), "items": [{"order_item": item.pk, "quantity": quantity, **location}]}


@override_settings(AUDIT_LOG_ENABLED=True)
class CoreBusinessGapTests(CoreBusinessFixture, TestCase):
    def setUp(self):
        self.setup_core()

    def test_no_baseline_shipment_cannot_borrow_other_warehouse_or_lot_stock(self):
        order, item = self.order()
        self.movement("2")
        self.movement("10", OTHER)
        stock.allocate_order(order)
        before = self.snapshot()
        self.post(f"/api/orders/{order.pk}/ship/", self.shipment(order, item, "3"), 400)
        self.assertEqual(self.snapshot(), before)

    def test_no_baseline_receipt_reversal_cannot_spend_replenishment_in_other_location(self):
        po, item = self.purchase()
        receipt = self.post(f"/api/purchase-orders/{po.pk}/receive/", {"purchase_item": item.pk, "receipt_date": DAY.isoformat(), "quantity": "6", "unit_cost": "3", **LOCATION}, 201)
        self.movement("6", LOCATION, "adjust_out")
        self.movement("6", OTHER)
        before = self.snapshot()
        self.post(f"/api/purchase-orders/{po.pk}/receipts/{receipt['id']}/reverse/", {"reason": "合成测试：A批已耗用，B批不能冒充原入库"}, 400)
        self.assertEqual(self.snapshot(), before)

    def test_no_baseline_manual_reversal_cannot_make_original_location_negative(self):
        original = self.movement("6")
        self.movement("6", LOCATION, "adjust_out")
        self.movement("6", OTHER)
        before = self.snapshot()
        self.post(f"/api/inventory-movements/{original.pk}/reverse/", {"reason": "合成原批次已使用"}, 400)
        self.assertEqual(self.snapshot(), before)

    def test_no_baseline_manual_outgoing_cannot_borrow_other_location_stock(self):
        self.movement("2")
        self.movement("10", OTHER)
        before = self.snapshot()
        self.post("/api/inventory-movements/", {"movement_date": DAY.isoformat(), "type": "sample_out", "sku": self.sku.pk, "quantity": "3", "unit_cost": "0", **LOCATION}, 400)
        self.assertEqual(self.snapshot(), before)

    def test_incoming_edit_cannot_relocate_stock_already_consumed(self):
        original = self.movement("6")
        self.movement("6", LOCATION, "adjust_out")
        self.movement("10", OTHER)
        before = self.snapshot()
        r = self.client.patch(f"/api/inventory-movements/{original.pk}/", OTHER, format="json")
        self.records.append({"path": f"/api/inventory-movements/{original.pk}/", "method": "patch", "status": r.status_code, "body": r.data})
        self.assertEqual(r.status_code, 400, r.data)
        self.assertEqual(self.snapshot(), before)

    def test_stale_cost_order_after_cancel_is_reloaded_before_attribution(self):
        po, item = self.purchase()
        order, _ = self.order()
        serializer = costs.CostInput(data={"version": 0, "allocations": [{"purchase_item": item.pk, "target_type": "order", "order": order.pk, "quantity": "6"}], "expenses": []})
        serializer.is_valid(raise_exception=True)
        cancel_order(order, "合成客户取消，发生于成本校验后")
        before = self.snapshot()
        with self.assertRaises(RestValidationError):
            costs.save_costs(po, serializer.validated_data)
        self.assertEqual(self.snapshot(), before)

@override_settings(AUDIT_LOG_ENABLED=True)
class CoreBusinessFlowTests(CoreBusinessFixture, TestCase):
    def setUp(self):
        self.setup_core()

    def test_legal_location_edits_outgoing_and_receipt_reversal(self):
        original = self.movement('6')
        r = self.client.patch(f'/api/inventory-movements/{original.pk}/', OTHER, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(stock.location_quantity(self.sku, LOCATION), D('0'))
        self.assertEqual(stock.location_quantity(self.sku, OTHER), D('6'))
        self.post('/api/inventory-movements/', {'movement_date': str(DAY), 'sku': self.sku.pk, 'quantity': '2', 'unit_cost':'0', 'type':'sample_out', **OTHER}, 201)
        po, item = self.purchase()
        r = self.post(f'/api/purchase-orders/{po.pk}/receive/', {'purchase_item':item.pk, 'receipt_date':str(DAY), 'quantity':'6', 'unit_cost':'3', **LOCATION}, 201)
        self.post(f'/api/purchase-orders/{po.pk}/receipts/{r["id"]}/reverse/', {'reason':'合成未耗用原批冲销'})
        item.refresh_from_db()
        self.assertEqual(item.received_quantity, D('0'))
        self.assertEqual(stock.location_quantity(self.sku, LOCATION), D('0'))
        self.assertEqual(stock.location_quantity(self.sku, OTHER), D('4'))

    def test_quote_to_order_partial_fulfillment_payment_and_refund_api(self):
        from crm.models import Quote
        q = Quote.objects.create(quote_no='CORE-QUOTE', customer=self.customer, quote_date=DAY, currency='CNY', exchange_rate=1)
        q.items.create(sku=self.sku, quantity=6, unit_price=10)
        draft = self.post('/api/orders/', {'quote':q.pk, 'customer':self.customer.pk, 'order_date':str(DAY), 'currency':'CNY', 'exchange_rate':'1', 'items':[{'sku':self.sku.pk,'quantity':'6','unit_price':'10'}]}, 201)
        oid = draft['id']
        self.post(f'/api/orders/{oid}/confirm/', {})
        order = Order.objects.get(pk=oid)
        self.assertEqual(order.quote_id, q.pk)
        self.assertEqual(order.status, 'confirmed')
        self.movement('6')
        stock.allocate_order(order)
        item = order.items.get()
        self.post(f'/api/orders/{oid}/ship/', self.shipment(order,item,'2'),201)
        item.refresh_from_db()
        self.assertEqual(stock._shipped_quantity(item),D('2'))
        before = self.snapshot()
        self.post(f'/api/orders/{oid}/complete/',{},400)
        self.assertEqual(self.snapshot(),before)
        self.post(f'/api/orders/{oid}/ship/', self.shipment(order,item,'4'),201)
        self.post(f'/api/orders/{oid}/complete/',{})
        def balance():
            r=self.client.get(f'/api/orders/{oid}/workbench/')
            self.assertEqual(r.status_code,200)
            self.records.append({'path':f'/api/orders/{oid}/workbench/','status':r.status_code,'body':r.data})
            return D(str(r.data['payment_summary']['balance_amount']))
        self.assertEqual(balance(), D('60'))
        for amount,kind,expected in [('20','customer_receipt','40'),('40','customer_receipt','0'),('10','refund','10')]:
            self.post('/api/transactions/',{'transaction_date':str(DAY),'order':oid,'kind':kind,'direction':'expense' if kind=='refund' else 'income','category':'合成退款' if kind=='refund' else '客户收款','amount':amount,'currency':'CNY','exchange_rate':'1'},201)
            self.assertEqual(balance(),D(expected))
            order.refresh_from_db()
            self.assertEqual(order.status,'completed')
        self.assertEqual(stock.sku_metrics(self.sku)['actual_quantity'],D('0'))
        self.assertEqual(stock.sku_metrics(self.sku)['reserved_quantity'],D('0'))

    def test_shared_purchase_amount_costs_reassign_and_receipt_related_orders(self):
        a,_=self.order('30'); b,_=self.order('20')
        po,item=self.purchase('100')
        item.unit_price=D('100'); item.save()
        def payload(version, aq='30', bq='20'):
            return {'version':version,'allocations':[{'purchase_item':item.pk,'target_type':'order','order':a.pk,'quantity':aq},{'purchase_item':item.pk,'target_type':'order','order':b.pk,'quantity':bq}], 'expenses':[{'name':'合成运费','amount':'1000','method':'amount'}]}
        url=f'/api/purchase-orders/{po.pk}/cost-allocation/'
        r=self.post(url,payload(0))
        shares={x['order']:D(str(x['additional_amount'])) for x in r['allocations']}
        self.assertEqual(shares,{a.pk:D('300'),b.pk:D('200'),None:D('500')})
        self.assertEqual(D(str(r['total_amount'])),D('11000'))
        self.post(url,payload(1,'20','30'))
        before=self.snapshot()
        self.post(url,payload(1),400)
        self.assertEqual(self.snapshot(),before)
        receipt=self.post(f'/api/purchase-orders/{po.pk}/receive/',{'purchase_item':item.pk,'receipt_date':str(DAY),'quantity':'40','unit_cost':'100',**LOCATION},201)
        movement=GoodsReceipt.objects.get(pk=receipt['id']).inventory_movement
        self.assertEqual(set(movement.related_orders.values_list('pk',flat=True)),{a.pk,b.pk})
        self.post(f'/api/purchase-orders/{po.pk}/receipts/{receipt["id"]}/reverse/',{'reason':'合成共享部分冲销'})
        item.refresh_from_db();po.refresh_from_db()
        self.assertEqual(item.received_quantity,D('0'));self.assertEqual(po.status,'ordered')
        self.assertEqual(set(item.cost_allocations.exclude(order=None).values_list('order_id',flat=True)),{a.pk,b.pk})
        self.assertEqual(sum((p.remaining_amount for p in po.payment_plans.all()),D(0)),D(0)) # ORM fixture has no automatic finance placement.

    def test_zero_basis_expense_rejection_and_audit_failure_roll_back_all_tables(self):
        po,item=self.purchase()
        item.unit_price=D(0);item.save()
        url=f'/api/purchase-orders/{po.pk}/cost-allocation/'
        body={'version':0,'allocations':[],'expenses':[{'name':'合成运费','amount':'1','method':'amount'}]}
        before=self.snapshot();self.post(url,body,400);self.assertEqual(self.snapshot(),before)
        body['expenses']=[]
        self.post(url,body)
        before=self.snapshot()
        with patch('crm.views.record_operation', side_effect=RuntimeError('synthetic audit failure')):
            with self.assertRaisesRegex(RuntimeError,'synthetic audit failure'):
                self.post(f'/api/purchase-orders/{po.pk}/receive/',{'purchase_item':item.pk,'receipt_date':str(DAY),'quantity':'1','unit_cost':'0',**LOCATION},201)
        self.assertEqual(self.snapshot(),before)

    def test_deleted_serializer_target_returns_validation_error_without_partial_commit(self):
        po,item=self.purchase();order,_=self.order(status='draft')
        s=costs.CostInput(data={'version':0,'allocations':[{'purchase_item':item.pk,'target_type':'order','order':order.pk,'quantity':'6'}],'expenses':[]})
        s.is_valid(raise_exception=True)
        order.delete();before=self.snapshot()
        with self.assertRaises(RestValidationError): costs.save_costs(po,s.validated_data)
        self.assertEqual(self.snapshot(),before)

    def test_standalone_purchase_payables_survive_receipt_reversal_and_cancellation(self):
        body={'supplier':self.supplier.pk,'order_date':str(DAY),'currency':'CNY','exchange_rate':'1','payment_terms_snapshot':[{'label':'合成验收付款','ratio':'1','due_basis':'order_date','offset_days':0}],'items':[{'sku':self.sku.pk,'quantity':'6','unit_price':'3'}]}
        draft=self.post('/api/purchase-orders/',body,201);pid=draft['id']
        self.post(f'/api/purchase-orders/{pid}/place/',{})
        po=PurchaseOrder.objects.get(pk=pid);item=po.items.get()
        self.assertIsNone(po.order_id)
        self.assertEqual(sum((p.remaining_amount for p in po.payment_plans.all()),D(0)),D(18))
        receipt=self.post(f'/api/purchase-orders/{pid}/receive/',{'purchase_item':item.pk,'receipt_date':str(DAY),'quantity':'2','unit_cost':'3',**LOCATION},201)
        before=self.snapshot();self.post(f'/api/purchase-orders/{pid}/cancel/',{'reason':'合成已入库不得取消'},400);self.assertEqual(self.snapshot(),before)
        self.assertEqual(sum((p.remaining_amount for p in po.payment_plans.all()),D(0)),D(18))
        self.post(f'/api/purchase-orders/{pid}/receipts/{receipt["id"]}/reverse/',{'reason':'合成退回原入库'})
        self.assertEqual(sum((p.remaining_amount for p in po.payment_plans.all()),D(0)),D(18))
        self.post(f'/api/purchase-orders/{pid}/cancel/',{'reason':'合成无有效收货且未付款取消'})
        po.refresh_from_db();item.refresh_from_db()
        self.assertEqual(po.status,'cancelled');self.assertEqual(item.received_quantity,D(0))
        self.assertTrue(all(p.status=='cancelled' for p in po.payment_plans.all()))
        self.assertEqual(stock.sku_metrics(self.sku)['actual_quantity'],D(0))
        self.assertFalse(SupplierSKU.objects.exists())

    def test_response_loss_same_key_replays_without_second_audit_or_stock_operation(self):
        po,item=self.purchase()
        url=f'/api/purchase-orders/{po.pk}/receive/'
        body={'purchase_item':item.pk,'receipt_date':str(DAY),'quantity':'2','unit_cost':'3',**LOCATION}
        original=self.post(url,body,201,key='CORE-LOST-RESPONSE')
        before=self.snapshot()
        replay=self.post(url,body,201,key='CORE-LOST-RESPONSE')
        self.assertEqual(replay,original);self.assertEqual(self.snapshot(),before)
        self.post(url,{**body,'quantity':'3'},409,key='CORE-LOST-RESPONSE')
        self.assertEqual(self.snapshot(),before)
        self.post(url,body,201,key='CORE-INDEPENDENT-REQUEST')
        item.refresh_from_db();self.assertEqual(item.received_quantity,D(4))
        self.assertEqual(GoodsReceipt.objects.count(),2)
        self.assertEqual(FulfillmentIdempotency.objects.count(),2)
        self.assertEqual(OperationLog.objects.filter(action_label='登记采购到货').count(),2)

    def test_supplier_payment_second_audit_failure_rolls_back_plan_and_transaction(self):
        from crm.services.finance import ensure_default_payment_plans
        from crm import views
        po,item=self.purchase()
        po.payment_terms_snapshot=[{'label':'合成验收付款','ratio':'1','due_basis':'order_date','offset_days':0}]
        po.save(update_fields=['payment_terms_snapshot'])
        ensure_default_payment_plans(po)
        before=self.snapshot()
        original=views.record_operation
        labels=[]
        def fail_second(*args,**kwargs):
            labels.append(kwargs['action_label'])
            if len(labels)==2: raise RuntimeError('synthetic second payment audit failure')
            return original(*args,**kwargs)
        payload={'transaction_date':str(DAY),'amount':'6','currency':'CNY','exchange_rate':'1','reference':'CORE-SYNTHETIC-PAYMENT'}
        with patch('crm.views.record_operation',side_effect=fail_second):
            with self.assertRaisesRegex(RuntimeError,'synthetic second payment audit failure'):
                self.post(f'/api/purchase-orders/{po.pk}/pay/',payload,201)
        self.assertEqual(labels,['登记供应商付款','采购单付款'])
        self.assertEqual(self.snapshot(),before)
        self.post(f'/api/purchase-orders/{po.pk}/pay/',payload,201)
        self.assertEqual(sum((p.remaining_amount for p in po.payment_plans.all()),D(0)),D(12))
        self.assertEqual(Transaction.objects.count(),1)
        self.assertEqual(OperationLog.objects.count(),2)

    def test_full_receipt_preserves_unpaid_payable_and_partial_payment_tracking(self):
        body={'supplier':self.supplier.pk,'order_date':str(DAY),'currency':'CNY','exchange_rate':'1','payment_terms_snapshot':[{'label':'合成验收付款','ratio':'1','due_basis':'order_date','offset_days':0}],'items':[{'sku':self.sku.pk,'quantity':'6','unit_price':'3'}]}
        draft=self.post('/api/purchase-orders/',body,201);pid=draft['id']
        self.post(f'/api/purchase-orders/{pid}/place/',{})
        po=PurchaseOrder.objects.get(pk=pid);item=po.items.get()
        self.post(f'/api/purchase-orders/{pid}/receive/',{'purchase_item':item.pk,'receipt_date':str(DAY),'quantity':'6','unit_cost':'3',**LOCATION},201)
        po.refresh_from_db();item.refresh_from_db()
        self.assertEqual(po.status,'completed');self.assertEqual(item.received_quantity,D(6))
        self.assertEqual(po.unpaid_amount,D(18))
        self.assertEqual(sum((p.remaining_amount for p in po.payment_plans.all()),D(0)),D(18))
        for amount,remaining in [('6','12'),('12','0')]:
            self.post(f'/api/purchase-orders/{pid}/pay/',{'transaction_date':str(DAY),'amount':amount,'currency':'CNY','exchange_rate':'1'},201)
            po.refresh_from_db();self.assertEqual(po.status,'completed')
            self.assertEqual(po.unpaid_amount,D(remaining))
            self.assertEqual(sum((p.remaining_amount for p in po.payment_plans.all()),D(0)),D(remaining))
        self.assertEqual(stock.sku_metrics(self.sku)['actual_quantity'],D(6))
        self.assertEqual(Transaction.objects.count(),2)
