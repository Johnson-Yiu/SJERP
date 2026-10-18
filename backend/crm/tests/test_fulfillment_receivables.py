from decimal import Decimal as D
from datetime import timedelta
from unittest.mock import patch
from django.test import TestCase
from django.utils import timezone
from crm.tests import test_r1a_reliability as fixtures
from crm.models import PaymentPlan, Transaction, Order
from crm.services.finance import record_transaction, order_receivable_state
from crm.services.fulfillment import confirm_shipment
from crm.services.purchase_lifecycle import place_purchase_order

class FulfillmentReceivableTests(TestCase):
    def setUp(self): fixtures.R1AReliabilityTests.setUp(self)
    def cash(self, amount, kind='customer_receipt'):
        return record_transaction({'order':self.order,'kind':kind,'amount':D(amount),'currency':'USD','exchange_rate':D('7.25')})
    def rows(self): return {'plans':list(PaymentPlan.objects.order_by('pk').values()),'cash':list(Transaction.objects.order_by('pk').values())}
    def summary(self):
        response=self.client.get(f'/api/orders/{self.order.pk}/workbench/')
        self.assertEqual(response.status_code,200,response.data)
        return response.data['payment_summary']
    def test_complete_with_debt_does_not_write_finance_and_replay_rejected(self):
        place_purchase_order(self.purchase);fixtures.R1AReliabilityTests.receive(self,'10')
        confirm_shipment(self.order,{'shipment_date':self.day,'items':[{'order_item':self.order_item.pk,'quantity':D('10')}]})
        self.order.refresh_from_db();self.cash('340')
        PaymentPlan.objects.filter(order=self.order).update(due_date=timezone.localdate()-timedelta(days=1))
        before=self.rows()
        self.assertEqual(self.client.post(f'/api/orders/{self.order.pk}/complete/',{},format='json').status_code,200)
        self.assertEqual(self.rows(),before)
        summary=self.summary();self.assertEqual(D(str(summary['balance_amount'])),D('160'))
        self.assertEqual(summary['settlement']['state'],'partial');self.assertEqual(summary['settlement']['overdue_amount'],D('160'))
        result=self.client.get('/api/payment-plans/',{'order':self.order.pk,'overdue':'true'})
        self.assertEqual(result.status_code,200)
        self.assertEqual(self.client.post(f'/api/orders/{self.order.pk}/complete/',{},format='json').status_code,400)
        self.assertEqual(self.rows(),before)
    def test_payment_and_refund_preserve_completed_fulfillment(self):
        Order.objects.filter(pk=self.order.pk).update(status='completed');self.order.refresh_from_db()
        self.cash('340');self.cash('160');self.assertEqual(self.summary()['settlement']['state'],'settled')
        self.cash('40','refund');summary=self.summary()
        self.assertEqual(summary['settlement']['state'],'partial');self.assertEqual(D(str(summary['balance_amount'])),D('40'))
        self.assertEqual(D(str(summary['paid_amount'])),D('460'));self.order.refresh_from_db();self.assertEqual(self.order.status,'completed')
    def test_paid_unshipped_cannot_complete(self):
        self.cash('500');before=self.rows()
        self.assertEqual(self.client.post(f'/api/orders/{self.order.pk}/complete/',{},format='json').status_code,400)
        self.assertEqual(self.rows(),before);self.order.refresh_from_db();self.assertEqual(self.order.status,'confirmed')
    def test_historical_completed_without_plans_is_not_settled_or_mutated(self):
        Order.objects.filter(pk=self.order.pk).update(status='completed');before=self.rows()
        self.assertEqual(self.summary()['settlement']['state'],'no_plans');self.assertEqual(self.rows(),before)
        response=self.client.get(f'/api/context/customers/{self.customer.pk}/')
        self.assertEqual(response.status_code,200)
        section=next(row for row in response.data['sections'] if row['key']=='orders')
        self.assertIn(['status_display','履约状态','status'],section['columns'])
    def test_special_states_and_zero_plan(self):
        for status in ['draft','cancelled']:
            self.order.status=status;self.assertEqual(order_receivable_state(self.order,[])['state'],status)
        self.order.status='completed'
        self.order_item.unit_price=D('0');self.order_item.save()
        self.assertEqual(order_receivable_state(self.order,[])['state'],'zero_contract')
        plan=PaymentPlan.objects.create(order=self.order,direction='receivable',planned_amount=D('0'),settled_amount=D('0'),currency='USD',status='cancelled')
        self.assertEqual(order_receivable_state(self.order,[plan])['state'],'zero_contract')
    def test_metadata_hidden_without_either_financial_permission(self):
        self.cash('340')
        for denied in ['finance','transactions']:
            with patch('crm.views.user_can',side_effect=lambda user,module,action:module!=denied):
                summary=self.summary()
                for field in ['balance_amount','paid_amount','settlement']:self.assertIsNone(summary[field])
    def test_multi_plan_decimal_and_overdue(self):
        self.cash('12.34');self.cash('2.34');plans=list(self.order.payment_plans.order_by('pk'))
        plans[0].due_date=timezone.localdate()-timedelta(days=1);plans[0].save()
        self.assertEqual(order_receivable_state(self.order,plans)['overdue_amount'],D('135.32'))
        self.assertEqual(self.order.outstanding_amount,D('485.32'))
        self.assertEqual(sum((row.rmb_amount for row in Transaction.objects.all()),D('0')),D('106.43'))
