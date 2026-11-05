"""PostgreSQL17-only independent-connection HTTP races for core closeout."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
from unittest import skipUnless
from unittest.mock import patch
from decimal import Decimal as D
from django.db import connection, connections, close_old_connections
from django.db.models import Sum
from django.test import TransactionTestCase, override_settings
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from crm.models import GoodsReceipt, InventoryMovement, OperationLog, Order, PurchaseCostAllocation, FulfillmentIdempotency
from crm.services import fulfillment as stock
from crm.services import purchase_costs as costs
from crm.tests.test_core_business_closeout import CoreBusinessFixture, DAY, LOCATION, OTHER


@skipUnless(connection.vendor == 'postgresql', 'Requires real PostgreSQL row locks; SQLite is not concurrency evidence')
@override_settings(AUDIT_LOG_ENABLED=True)
class CoreBusinessConcurrencyTests(CoreBusinessFixture, TransactionTestCase):
    def setUp(self): self.setup_core()

    def race(self, functions, synchronized=True):
        barrier=Barrier(2)
        user_id=self.user.pk
        def worker(index):
            close_old_connections()
            try:
                with connections['default'].cursor() as cursor:
                    cursor.execute("SET statement_timeout = '15000ms'")
                    cursor.execute('SELECT pg_backend_pid()')
                    pid=cursor.fetchone()[0]
                client=APIClient();client.force_authenticate(get_user_model().objects.get(pk=user_id))
                if synchronized: barrier.wait(10)
                response=functions[index](client)
                return pid,response.status_code,response.data
            finally: connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures=[pool.submit(worker,i) for i in range(2)]
            results=[f.result(timeout=35) for f in futures]
        self.assertEqual(len({x[0] for x in results}),2)
        self.records.append({'independent_pg_sessions':results})
        return results

    def test_location_overdraw_competition_only_one_shipment_commits(self):
        first,fi=self.order('3');second,si=self.order('3')
        self.movement('3');self.movement('3',OTHER)
        for order in (first,second): stock.allocate_order(order)
        before_logs=OperationLog.objects.count()
        functions=[]
        for order,item in [(first,fi),(second,si)]:
            functions.append(lambda c,o=order,i=item:c.post(f'/api/orders/{o.pk}/ship/',self.shipment(o,i,'3'),format='json',HTTP_IDEMPOTENCY_KEY='CORE-RACE-'+str(o.pk)))
        results=self.race(functions)
        self.assertEqual(sorted(r[1] for r in results),[201,400])
        self.assertEqual(stock.location_quantity(self.sku,LOCATION),D(0))
        self.assertEqual(stock.location_quantity(self.sku,OTHER),D(3))
        self.assertEqual(InventoryMovement.objects.filter(type='sales_out').count(),1)
        self.assertEqual(FulfillmentIdempotency.objects.count(),1)
        self.assertEqual(OperationLog.objects.count()-before_logs,1)
        fi.refresh_from_db();si.refresh_from_db()
        self.assertEqual(stock._shipped_quantity(fi)+stock._shipped_quantity(si),D(3))
        self.assertEqual(stock.sku_metrics(self.sku)['reserved_quantity'],D(3))

    def test_cost_version_race_keeps_single_replacement_and_audit(self):
        po,item=self.purchase();a,_=self.order();b,_=self.order()
        url=f'/api/purchase-orders/{po.pk}/cost-allocation/'
        functions=[]
        for order in (a,b):
            body={'version':0,'allocations':[{'purchase_item':item.pk,'target_type':'order','order':order.pk,'quantity':'6'}],'expenses':[]}
            functions.append(lambda c,p=body:c.post(url,p,format='json'))
        before=OperationLog.objects.count()
        result=self.race(functions)
        self.assertEqual(sorted(x[1] for x in result),[200,400])
        po.refresh_from_db();self.assertEqual(po.cost_allocation_version,1)
        self.assertEqual(PurchaseCostAllocation.objects.filter(purchase_item=item).count(),1)
        self.assertEqual(item.cost_allocations.get().quantity,D(6))
        self.assertEqual(OperationLog.objects.count()-before,1)

    def test_cancel_between_serializer_validation_and_cost_lock_is_rejected(self):
        po,item=self.purchase();order,_=self.order()
        validated=Event();cancelled=Event()
        original=costs.CostInput.run_validation
        def pause(serializer,data):
            result=original(serializer,data)
            validated.set()
            if not cancelled.wait(12): raise AssertionError('cancellation did not finish')
            return result
        body={'version':0,'allocations':[{'purchase_item':item.pk,'target_type':'order','order':order.pk,'quantity':'6'}],'expenses':[]}
        def cancel(client):
            if not validated.wait(12): raise AssertionError('validation did not run')
            try:return client.post(f'/api/orders/{order.pk}/cancel/',{'reason':'合成并发取消'},format='json')
            finally:cancelled.set()
        with patch.object(costs.CostInput,'run_validation',pause):
            results=self.race([lambda c:c.post(f'/api/purchase-orders/{po.pk}/cost-allocation/',body,format='json'),cancel],synchronized=False)
        self.assertEqual([x[1] for x in results],[400,200])
        po.refresh_from_db();order.refresh_from_db()
        self.assertEqual(order.status,'cancelled');self.assertEqual(po.cost_allocation_version,0)
        self.assertFalse(item.cost_allocations.filter(order=order).exists())
        self.assertEqual(OperationLog.objects.filter(action_label='取消销售订单').count(),1)

    def test_cancel_and_ship_race_has_one_legal_outcome_without_partial_effects(self):
        order,item=self.order();self.movement('6');stock.allocate_order(order)
        result=self.race([lambda c:c.post(f'/api/orders/{order.pk}/cancel/',{'reason':'合成取消竞争'},format='json'),lambda c:c.post(f'/api/orders/{order.pk}/ship/',self.shipment(order,item,'6'),format='json',HTTP_IDEMPOTENCY_KEY='CORE-CANCEL-SHIP')])
        self.assertEqual(sorted(x[1] for x in result),[200,400] if result[0][1]==200 else [201,400])
        order.refresh_from_db();item.refresh_from_db()
        if order.status=='cancelled':
            self.assertEqual(stock._shipped_quantity(item),D(0));self.assertEqual(stock.sku_metrics(self.sku)['actual_quantity'],D(6))
            self.assertFalse(FulfillmentIdempotency.objects.exists())
        else:
            self.assertEqual(stock._shipped_quantity(item),D(6));self.assertEqual(stock.sku_metrics(self.sku)['actual_quantity'],D(0))
            self.assertEqual(FulfillmentIdempotency.objects.count(),1)
        self.assertEqual(stock.sku_metrics(self.sku)['reserved_quantity'],D(0))
        self.assertEqual(OperationLog.objects.count(),1)

    def test_purchase_cancellation_and_receipt_compete_without_partial_effects(self):
        po,item=self.purchase()
        receipt={'purchase_item':item.pk,'receipt_date':str(DAY),'quantity':'6','unit_cost':'3',**LOCATION}
        result=self.race([lambda c:c.post(f'/api/purchase-orders/{po.pk}/cancel/',{'reason':'合成采购取消竞争'},format='json'),lambda c:c.post(f'/api/purchase-orders/{po.pk}/receive/',receipt,format='json',HTTP_IDEMPOTENCY_KEY='CORE-CANCEL-RECEIVE')])
        self.assertEqual(sorted(x[1] for x in result),[200,400] if result[0][1]==200 else [201,400])
        po.refresh_from_db();item.refresh_from_db()
        expected=D(0) if po.status=='cancelled' else D(6)
        self.assertIn(po.status,['cancelled','completed'])
        self.assertEqual(item.received_quantity,expected)
        self.assertEqual(stock.sku_metrics(self.sku)['actual_quantity'],expected)
        self.assertEqual(GoodsReceipt.objects.count(),int(expected>0))
        self.assertEqual(FulfillmentIdempotency.objects.count(),int(expected>0))
        self.assertEqual(OperationLog.objects.count(),1)
