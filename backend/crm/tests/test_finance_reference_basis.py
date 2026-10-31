from datetime import date
from decimal import Decimal as D
import csv,io
from django.test import TestCase
from crm.tests import test_reporting as fixtures
from crm.models import Transaction,PaymentPlan
from crm.finance_basis import BOOK_RMB_NOTE

class FinanceReferenceBasisTests(TestCase):
    def setUp(self):
        fixtures.ReportingTests.setUp(self)
        self.dates={'date_from':'2026-09-01','date_to':'2026-09-30'}
        for no,direction,currency,amount,rate,rmb,status in [('USD','income','USD','10','7.123456','71.2346','confirmed'),('CNY','income','CNY','100','1','100','confirmed'),('EUR-FALLBACK','income','EUR','10','7.8','0','confirmed'),('EXPENSE','expense','USD','2.34','7.123456','16.6689','confirmed'),('VOID','income','CNY','1000','1','1000','cancelled')]:
            Transaction.objects.create(transaction_no=no,transaction_date=date(2026,9,1),direction=direction,kind='other',category='合成分类',currency=currency,amount=D(amount),exchange_rate=D(rate),rmb_amount=D(rmb),status=status)
    def test_reference_metadata_keeps_exact_existing_amounts_and_cny_rows(self):
        before=[list(m.objects.order_by('pk').values()) for m in [Transaction,PaymentPlan]]
        data=self.client.get('/api/finance-dashboard/',self.dates).data
        self.assertEqual(data['metrics']['income_rmb'],D('249.2346'))
        self.assertEqual(data['metrics']['expense_rmb'],D('16.6689'))
        self.assertEqual(data['metrics']['net_cash_rmb'],D('232.5657'))
        self.assertEqual(data['metrics']['sales_rmb'],D('189'))
        self.assertEqual(data['cash_basis']['basis'],'book_rmb_reference')
        self.assertTrue(data['cash_basis']['includes_cny']);self.assertEqual(data['cash_basis']['note'],BOOK_RMB_NOTE)
        cash=self.client.get('/api/reports/data/',dict(self.dates,source='cash',group_by='direction')).data
        self.assertEqual(cash['totals']['amount'],D('232.5657'));self.assertEqual(cash['totals']['count'],4)
        self.assertEqual(cash['basis'],'book_rmb_reference');self.assertEqual(cash['version'],1)
        self.assertIn('原币为CNY',cash['note']);self.assertIn('不等同于银行到账日',cash['note'])
        self.assertEqual(before,[list(m.objects.order_by('pk').values()) for m in [Transaction,PaymentPlan]])

    def test_model_metadata_labels_rmb_amount_as_book_reference(self):
        field = Transaction._meta.get_field('rmb_amount')
        self.assertEqual(field.name, 'rmb_amount')
        self.assertEqual(field.verbose_name, '账面人民币折算参考')
    def test_csv_headers_notes_and_exact_numbers_agree(self):
        finance=self.client.get('/api/finance-dashboard/',dict(self.dates,export='csv'))
        rows=list(csv.reader(io.StringIO(finance.content.decode('utf-8-sig'))))
        self.assertIn('人民币折算参考',rows[0][0]);self.assertIn(BOOK_RMB_NOTE,rows[0])
        self.assertEqual([D(x) for x in rows[2][1:]],[D('249.2346'),D('16.6689'),D('232.5657')])
        cash=self.client.get('/api/reports/data/',dict(self.dates,source='cash',group_by='direction',export='csv'))
        text=cash.content.decode('utf-8-sig');self.assertIn('账面收支（人民币折算参考）',text)
        self.assertIn('金额（人民币折算参考）',text);self.assertIn('232.5657',text)
        for forbidden in ['实际收入（人民币）','实际支出（人民币）','优先使用实际人民币金额']:
            self.assertNotIn(forbidden,finance.content.decode('utf8')+text)
    def test_old_cash_query_contract_stays_valid_and_other_sources_keep_metadata(self):
        catalog=self.client.get('/api/reports/catalog/').data['sources']
        self.assertEqual(catalog['cash']['dates']['transaction_date'],'流水发生日期')
        response=self.client.get('/api/reports/data/',dict(self.dates,source='cash',date_field='transaction_date',group_by='currency'))
        self.assertEqual(response.status_code,200);self.assertEqual(response.data['source'],'cash')
        sales=self.client.get('/api/reports/data/',dict(self.dates,source='sales')).data
        self.assertNotIn('basis',sales);self.assertEqual(sales['totals']['amount'],D('189'))
