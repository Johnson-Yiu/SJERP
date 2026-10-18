"""FUP-01 real API/database regression; UI transport loss is evidenced separately."""
from datetime import date
from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient
from crm.models import Transaction

class FinanceRetrySafetyTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.payload = dict(transaction_no='FUP01-STABLE', transaction_date=str(date(2026,10,18)), kind='period_expense', direction='expense', category='办公费用', amount='12.34', currency='USD', exchange_rate='7.123456')

    def test_same_number_replay_rejected_without_writes(self):
        self.assertEqual(self.client.post('/api/transactions/',self.payload,format='json').status_code,201)
        before=list(Transaction.objects.values())
        response=self.client.post('/api/transactions/',self.payload,format='json')
        self.assertEqual(response.status_code,400)
        self.assertIn('transaction_no',response.data)
        self.assertEqual(list(Transaction.objects.values()),before)
        self.assertEqual(Transaction.objects.get().rmb_amount,Decimal('87.9034'))

    def test_rejected_request_can_be_corrected_with_original_number(self):
        self.payload['amount']='-1'
        self.assertEqual(self.client.post('/api/transactions/',self.payload,format='json').status_code,400)
        self.assertEqual(Transaction.objects.count(),0)
        self.payload['amount']='2.34'
        self.assertEqual(self.client.post('/api/transactions/',self.payload,format='json').status_code,201)
        self.assertEqual(Transaction.objects.get().rmb_amount,Decimal('16.6689'))

    def test_two_real_payments_same_amount_distinct_numbers_are_allowed(self):
        for number in ['FUP01-PAYMENT-1','FUP01-PAYMENT-2']:
            self.payload['transaction_no']=number
            self.assertEqual(self.client.post('/api/transactions/',self.payload,format='json').status_code,201)
        self.assertEqual(Transaction.objects.count(),2)
        self.assertEqual(sum((t.amount for t in Transaction.objects.all()),Decimal('0')),Decimal('24.68'))
