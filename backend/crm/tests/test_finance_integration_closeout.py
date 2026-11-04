"""Coordinator regression for API counterexamples; synthetic service fixtures only."""
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from crm.models import FinanceFact, FinanceTransferMatch, FinanceHistoricalTransfer, OperationLog
from crm.services import finance_closeout as ledger
from crm.tests.test_finance_closeout import CloseoutFixture


class FinanceIntegrationCloseoutTests(CloseoutFixture, TestCase):
    def setUp(self):
        self.setup_ledger()
        self.client = APIClient()
        self.client.force_authenticate(self.maker)

    def test_classified_external_expense_cannot_be_hidden_as_internal_principal(self):
        out = self.fact(direction='expense', nature='internal_principal', amount='50.00')
        inc = self.fact(account=self.second.pk, nature='internal_principal', amount='50.00')
        changed = self.client.post('/api/finance-ledger/classifications/',
                                   {'fact': out.pk, 'nature': 'expense', 'reason': '合成核实为对外支出'}, format='json')
        self.assertEqual(changed.status_code, 201, changed.data)
        before = list(FinanceFact.objects.order_by('pk').values())
        logs = OperationLog.objects.count()
        response = self.client.post('/api/finance-ledger/transfers/',
                                    {'outgoing': out.pk, 'incoming': inc.pk, 'reason': '合成错误本金配对'}, format='json')
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(FinanceTransferMatch.objects.count(), 0)
        self.assertEqual(list(FinanceFact.objects.order_by('pk').values()), before)
        self.assertEqual(OperationLog.objects.count(), logs)
        detail = self.client.get('/api/finance-ledger/fact_detail/', {'id': out.pk})
        self.assertEqual(detail.status_code, 200, detail.data)
        self.assertEqual(detail.data['nature'], 'expense')
        self.assertTrue(detail.data['company_flow_included'])

    def test_new_transfer_match_requires_rechecking_completed_account_review(self):
        self.fact(kind='opening', actual_date='2026-01-01', amount='1000.00')
        out = self.fact(direction='expense', nature='internal_principal', amount='50.00')
        inc = self.fact(account=self.second.pk, nature='internal_principal', amount='50.00')
        review = ledger.reconcile({'account': self.account.pk, 'date_from': '2026-01-01', 'date_to': '2026-01-31',
                                  'voucher': self.proof.pk, 'statement_balance': '950.00', 'completed': True,
                                  'reason': '合成月末核对'}, self.maker)
        initial = self.client.get('/api/finance-ledger/', {'date_to': '2026-01-31'})
        self.assertEqual(initial.status_code, 200, initial.data)
        self.assertEqual(next(r for r in initial.data['reviews'] if r['id'] == review.pk)['status'], 'completed')
        matched = self.client.post('/api/finance-ledger/transfers/',
                                   {'outgoing': out.pk, 'incoming': inc.pk, 'reason': '合成核实本金配对'}, format='json')
        self.assertEqual(matched.status_code, 201, matched.data)
        current = self.client.get('/api/finance-ledger/', {'date_to': '2026-01-31'})
        self.assertEqual(current.status_code, 200, current.data)
        self.assertEqual(next(r for r in current.data['reviews'] if r['id'] == review.pk)['status'], 'needs_review')
        self.assertEqual(ledger.balance(self.account, '2026-01-31', self.maker)[0], Decimal('950.00'))
        self.assertNotEqual(ledger.balance(self.account, '2026-01-31', self.maker)[1], review.fingerprint)
        duplicate = self.client.post('/api/finance-ledger/transfers/',
                                     {'outgoing': out.pk, 'incoming': inc.pk, 'reason': '合成同源重放'}, format='json')
        self.assertEqual(duplicate.status_code, 201, duplicate.data)
        self.assertEqual(duplicate.data['id'], matched.data['id'])
        self.assertEqual(FinanceTransferMatch.objects.count(), 1)

    @override_settings(RMB_CASH_ACCOUNT_IDS=('SYNTH_FX', 'SYNTH_CNY'))
    def test_classified_external_fact_cannot_be_hidden_by_legacy_transfer_match(self):
        from crm.tests.test_cash_events import CashFixture, payload
        from crm.services import cash_events
        CashFixture.setup_cash(self)
        self.client.force_authenticate(self.maker)
        self.proof = ledger.upload(SimpleUploadedFile('closeout-legacy.pdf', b'%PDF-1.4\nSynthetic closeout voucher\n%%EOF'), self.maker)
        legacy, _ = cash_events.register_event(payload([self.receipt], key='SYNTH-CLOSEOUT-LEGACY'), self.maker)
        cash_events.confirm_event(legacy.pk, self.maker, voucher_checked=True)
        ledger.map_account({'account': self.account.pk, 'legacy_code': 'SYNTH_CNY', 'reason': '合成旧银行账户映射'}, self.maker)
        out = self.fact(account=self.second.pk, direction='expense', amount=str(legacy.bank_net_amount), nature='internal_principal')
        changed = self.client.post('/api/finance-ledger/classifications/',
                                   {'fact': out.pk, 'nature': 'expense', 'reason': '合成核实为外部费用'}, format='json')
        self.assertEqual(changed.status_code, 201, changed.data)
        logs = OperationLog.objects.count()
        response = self.client.post('/api/finance-ledger/transfers/',
                                    {'outgoing': f'fact:{out.pk}', 'incoming': f'legacy:{legacy.pk}',
                                     'outgoing_voucher': self.proof.pk, 'incoming_voucher': self.proof.pk,
                                     'reason': '合成错误新旧本金匹配'}, format='json')
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(FinanceHistoricalTransfer.objects.count(), 0)
        self.assertEqual(OperationLog.objects.count(), logs)

    @override_settings(RMB_CASH_ACCOUNT_IDS=('SYNTH_FX', 'SYNTH_CNY'))
    def test_legacy_transfer_match_invalidates_review_without_changing_balance(self):
        from crm.tests.test_cash_events import CashFixture, payload
        from crm.services import cash_events
        CashFixture.setup_cash(self)
        self.client.force_authenticate(self.maker)
        self.proof = ledger.upload(SimpleUploadedFile('legacy-review.pdf', b'%PDF-1.4\nSynthetic review voucher\n%%EOF'), self.maker)
        legacy, _ = cash_events.register_event(payload([self.receipt], key='SYNTH-CLOSEOUT-REVIEW'), self.maker)
        cash_events.confirm_event(legacy.pk, self.maker, voucher_checked=True)
        ledger.map_account({'account': self.account.pk, 'legacy_code': 'SYNTH_CNY', 'reason': '合成旧银行核对映射'}, self.maker)
        self.fact(kind='opening', actual_date='2026-10-01', amount='1000.00')
        out = self.fact(account=self.second.pk, direction='expense', actual_date='2026-10-19',
                        amount=str(legacy.bank_net_amount), nature='internal_principal')
        calculated, original_fingerprint = ledger.balance(self.account, '2026-10-31', self.maker)
        review = ledger.reconcile({'account': self.account.pk, 'date_from': '2026-10-01', 'date_to': '2026-10-31',
                                  'voucher': self.proof.pk, 'statement_balance': str(calculated), 'completed': True,
                                  'reason': '合成旧银行月末核对'}, self.maker)
        response = self.client.post('/api/finance-ledger/transfers/',
                                    {'outgoing': f'fact:{out.pk}', 'incoming': f'legacy:{legacy.pk}',
                                     'outgoing_voucher': self.proof.pk, 'incoming_voucher': self.proof.pk,
                                     'reason': '合成新旧本金核实'}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        current = self.client.get('/api/finance-ledger/', {'date_to': '2026-10-31'})
        self.assertEqual(current.status_code, 200, current.data)
        self.assertEqual(next(r for r in current.data['reviews'] if r['id'] == review.pk)['status'], 'needs_review')
        after, fingerprint = ledger.balance(self.account, '2026-10-31', self.maker)
        self.assertEqual(after, calculated)
        self.assertNotEqual(fingerprint, original_fingerprint)

    def test_unmatched_review_fingerprint_remains_compatible(self):
        opening = self.fact(kind='opening', actual_date='2026-01-01', amount='1000.00')
        receipt = self.fact(amount='40.00')
        expected = ledger.digest({'facts': [opening.pk, receipt.pk], 'legacy': [], 'corrections': [], 'classifications': []})
        amount, fingerprint = ledger.balance(self.account, '2026-01-31', self.maker)
        self.assertEqual(amount, Decimal('1040.00'))
        self.assertEqual(fingerprint, expected)
