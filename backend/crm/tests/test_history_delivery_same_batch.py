import tempfile
import hashlib
import io
import subprocess
from pathlib import Path
from django.core.management import call_command
import os
import json
from django.core.serializers.json import DjangoJSONEncoder
from crm.management.commands.reconcile_history_import import reconcile
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.db import connection
from crm.tests.test_history_takeover import HistoryTakeoverFixtureMixin
from crm.history_takeover import execute_group, _truth_rows, TakeoverRuleError
from crm.history_product_models import ArchivedHistoryLine, HistoryProductLink
from crm.models import Customer, SKU, Order, PurchaseOrder, Transaction, FinanceFact, InventoryMovement, Shipment, GoodsReceipt, HistoryTakeoverApplication
from crm import history_operational_finance as bridge
from crm.services import finance_closeout

@override_settings(AUDIT_LOG_ENABLED=True)
class DeliverySameBatchTests(HistoryTakeoverFixtureMixin, TestCase):
    def test_customer_archive_link_and_finance(self):
        rows = self.source_rows()
        self.sku.delete()
        self.customer.delete()
        content = b'code,name,country\nHT-C1,Synthetic Customer,US\n'
        def upload(): return SimpleUploadedFile('customers.csv', content, content_type='text/csv')
        pre = self.client.post('/api/import/csv/preview/', {'entity':'customers','file':upload()}, format='multipart')
        self.assertEqual(pre.status_code, 200, pre.data)
        result = self.client.post('/api/import/csv/execute/', {'entity':'customers','file':upload(),'preview_token':pre.data['preview_token']}, format='multipart')
        self.assertEqual(result.status_code, 200, result.data)
        self.customer = Customer.objects.get(code='HT-C1')
        for sheet in ('销售明细','采购明细','履约记录','库存盘点'):
            for row in rows[sheet]: row['sku_code'] = ''
        rows['销售明细'][0]['specification_snapshot'] = '24W'
        rows['采购明细'][0]['specification_snapshot'] = '18W'
        rows['采购明细'][0]['sku_name_snapshot'] = rows['销售明细'][0]['sku_name_snapshot']
        completed = dict(rows['销售订单'][0], source_record_id='SO-HT-DONE', order_no='HIST-SO-HT-DONE', lifecycle_state='completed')
        done_line = dict(rows['销售明细'][0], source_order_id='SO-HT-DONE', source_line_id='1')
        done_event = dict(rows['履约记录'][0], source_event_id='SHIP-HT-DONE', parent_source_id='SO-HT-DONE', quantity_base='10.00')
        rows['销售订单'].append(completed)
        rows['销售明细'].append(done_line)
        rows['履约记录'].append(done_event)
        bad_group = dict(rows['分组'][0], group_id='HT-G-ERROR')
        bad_order = dict(rows['销售订单'][0], group_id='HT-G-ERROR', source_record_id='SO-HT-BAD', order_no='HIST-SO-HT-BAD')
        bad_line = dict(rows['销售明细'][0], group_id='HT-G-ERROR', source_order_id='SO-HT-BAD', quantity_base='-1')
        rows['分组'].append(bad_group)
        rows['销售订单'].append(bad_order)
        rows['销售明细'].append(bad_line)
        workbook = self.workbook_bytes(rows)
        if os.environ.get('HISTORY_DELIVERY_SOURCE_WORKBOOK'):
            with open(os.environ['HISTORY_DELIVERY_SOURCE_WORKBOOK'], 'wb') as output:
                output.write(workbook)
        if os.environ.get('HISTORY_DELIVERY_CUSTOMER_CSV'):
            with open(os.environ['HISTORY_DELIVERY_CUSTOMER_CSV'], 'wb') as output:
                output.write(content)
        def submit():
            return self.client.post("/api/import/history-takeovers/", {"file": SimpleUploadedFile("synthetic-history.xlsx", workbook)}, format="multipart")
        submitted = submit()
        self.assertEqual(submitted.status_code, 201, submitted.data)
        application = HistoryTakeoverApplication.objects.get(pk=submitted.data["id"])
        group = application.groups.get(source_group_id='HT-G1')
        bad = application.groups.get(source_group_id='HT-G-ERROR')
        self.assertNotEqual(bad.preflight_result['status'], '通过')
        dup = submit()
        self.assertEqual(dup.status_code, 200, dup.data)
        self.assertTrue(dup.data['duplicate_submission_reused'])
        bad_url = f'/api/import/history-takeovers/{application.pk}/groups/{bad.pk}/'
        bad_review = self.client.post(bad_url+'review/', {'decision':'approve','note':'合成错误','confirm_manual':True}, format='json')
        self.assertNotEqual(bad_review.status_code, 200)
        url = f'/api/import/history-takeovers/{application.pk}/groups/{group.pk}/'
        reviewed = self.client.post(url+'review/', {'decision':'approve','note':'核对合成凭证','confirm_manual':True}, format='json')
        self.assertEqual(reviewed.status_code, 200, reviewed.data)
        create = ArchivedHistoryLine.objects.create
        def fail_purchase(**fields):
            if 'purchase_order' in fields: raise RuntimeError('synthetic failure')
            return create(**fields)
        with patch('crm.history_takeover.ArchivedHistoryLine.objects.create', side_effect=fail_purchase):
            with self.assertRaisesRegex(RuntimeError, 'synthetic failure'): execute_group(group, self.admin)
        self.assertEqual(Order.objects.count()+PurchaseOrder.objects.count(), 0)
        baseline = {m.__name__: m.objects.count() for m in (Transaction,FinanceFact,InventoryMovement,Shipment,GoodsReceipt)}
        result = self.client.post(url+'execute/', {}, format='json')
        self.assertEqual(result.status_code, 200, result.data)
        self.assertTrue(self.client.post(url+'execute/', {}, format='json').data['idempotent_replay'])
        changed_rows = self.source_rows()
        changed_rows['分组'][0]['notes'] = 'different file, same source identities'
        changed = self.upload_application(changed_rows, filename='duplicate-source.xlsx')
        self.assertEqual(changed.status_code, 201, changed.data)
        duplicate_app = HistoryTakeoverApplication.objects.get(pk=changed.data['id'])
        duplicate_group = duplicate_app.groups.get()
        with self.assertRaisesMessage(TakeoverRuleError, '来源记录已由其他承接批次登记'):
            _truth_rows(duplicate_group)
        duplicate_url = f'/api/import/history-takeovers/{duplicate_app.pk}/groups/{duplicate_group.pk}/'
        duplicate_review = self.client.post(duplicate_url+'review/', {'decision':'approve','note':'合成重复来源核对','confirm_manual':True}, format='json')
        self.assertNotEqual(duplicate_review.status_code, 200)
        self.assertEqual(SKU.objects.count(), 0)
        self.assertEqual(ArchivedHistoryLine.objects.count(), 3)
        self.assertEqual(sum(m.objects.count() for m in (Transaction,FinanceFact,InventoryMovement,Shipment,GoodsReceipt)),0)
        after_archive = reconcile(application, os.environ.get('HISTORY_DELIVERY_SOURCE_SHA', 'uncommitted-test'))
        self.assertEqual(after_archive['global_fact_counts']['FinanceFact'], 0)
        sku = SKU.objects.create(product=self.product, sku='B', display_name_cn='合成正式商品 B', specification='24W', unit='pcs')
        ids = list(group.source_records.filter(record_type__in=['销售明细','采购明细']).values_list('pk',flat=True))
        preview = self.client.post('/api/import/history-products/preview/', {'ids':ids,'target':sku.pk,'operation':'link','reason':'核对合成规格'}, format='json')
        self.assertEqual(preview.status_code,409,preview.data)
        self.assertEqual(len(preview.data['conflicts']), 1)
        conflict_preview = preview.data
        sales_ids = list(group.source_records.filter(record_type='销售明细').values_list('pk', flat=True))
        preview = self.client.post('/api/import/history-products/preview/', {'ids':sales_ids,'target':sku.pk,'operation':'link','reason':'核对合成规格'}, format='json')
        self.assertEqual(preview.status_code,200,preview.data)
        linked = self.client.post('/api/import/history-products/apply/', {'token':preview.data['token']}, format='json')
        self.assertEqual(linked.status_code,200,linked.data)
        self.assertEqual(HistoryProductLink.objects.filter(sku=sku).count(),2)
        self.assertEqual(SKU.objects.count(),1)
        self.assertEqual(sum(m.objects.count() for m in (Transaction,FinanceFact,InventoryMovement,Shipment,GoodsReceipt)),0)
        with CaptureQueriesContext(connection) as queries:
            before_finance = reconcile(application, os.environ.get('HISTORY_DELIVERY_SOURCE_SHA', 'uncommitted-test'))
        self.assertTrue(all(q['sql'].lstrip().upper().startswith('SELECT') for q in queries))
        self.assertEqual(before_finance['groups'][0]['order_count'], 3)
        self.assertEqual(before_finance['groups'][0]['product_count'], 3)
        self.assertEqual(before_finance['groups'][0]['product_states']['linked'], 2)
        self.assertEqual(before_finance['groups'][0]['product_states']['pending'], 1)
        self.assertEqual(before_finance['groups'][0]['cny_finance_facts'], [])
        maker = get_user_model().objects.create_superuser(username='delivery-maker',password='test-only')
        reviewer = get_user_model().objects.create_superuser(username='delivery-reviewer',password='test-only')
        with tempfile.TemporaryDirectory(prefix='delivery-media-') as media, override_settings(MEDIA_ROOT=media):
            account = finance_closeout.create_account({'code':'DELIVERY-SYN','name':'合成账户','account_type':'bank','ownership':'own','ownership_reason':'合成凭证'}, maker)
            voucher = finance_closeout.upload(SimpleUploadedFile('synthetic.pdf', b'%PDF-1.4\nsynthetic\n%%EOF'), maker)
            source = group.source_records.get(record_type='收付款流水',source_record_id='TX-SO-1')
            mapping = {'account':account.pk,'voucher':voucher.pk,'actual_date':'2024-09-03','amount':'287.43','reason':'核对合成银行到账凭证'}
            _, created = bridge.submit_source(group.pk, source.pk, mapping, maker)
            self.assertTrue(created)
            bridge.advance_source(group.pk, source.pk, 'approve', reviewer)
            fact = bridge.advance_source(group.pk, source.pk, 'post', maker, voucher_checked=True)
            self.assertEqual(bridge.advance_source(group.pk, source.pk, 'post', maker, voucher_checked=True).pk,fact.pk)
            self.assertEqual(FinanceFact.objects.count(),1)
            report = reconcile(application, os.environ.get('HISTORY_DELIVERY_SOURCE_SHA', 'uncommitted-test'))
            original_path = Path(media) / 'source.xlsx'
            original_path.write_bytes(workbook)
            current_sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
            # The command refuses dirty source; simulate the recorded clean source in this
            # transactional test while still exercising digest and argument handling.
            with patch('crm.management.commands.reconcile_history_import.subprocess.check_output', side_effect=[current_sha + '\n', '']):
                out = io.StringIO()
                call_command('reconcile_history_import', application.pk, source_sha=current_sha, source_file=str(original_path), stdout=out)
                self.assertEqual(json.loads(out.getvalue())['file_sha256'], application.source_sha256)
            original_path.write_bytes(b'wrong file')
            with patch('crm.management.commands.reconcile_history_import.subprocess.check_output', side_effect=[current_sha + '\n', '']):
                with self.assertRaisesMessage(ValueError, 'does not match'):
                    call_command('reconcile_history_import', application.pk, source_sha=current_sha, source_file=str(original_path), stdout=io.StringIO())
            self.assertEqual(len(report['groups'][0]['cny_finance_facts']), 1)
            self.assertEqual(len(report['groups'][0]['source_plans']), 2)
            self.assertEqual(report['groups'][0]['source_cash_totals']['USD']['income'], 40)
            self.assertEqual(report['groups'][0]['cny_finance_facts'][0]['amount'], fact.amount)
            self.assertEqual(report['groups'][0]['currency_totals']['USD']['sales_total'], Order.objects.get(order_no='HIST-SO-HT-1').total_amount + Order.objects.get(order_no='HIST-SO-HT-DONE').total_amount)
            self.assertTrue(all(row['record_id'] for row in report['groups'][0]['source_rows']))
            if os.environ.get('HISTORY_DELIVERY_SYNTHETIC_REPORT'):
                with open(os.environ['HISTORY_DELIVERY_SYNTHETIC_REPORT'], 'w', encoding='utf-8') as output:
                    json.dump({'customer_csv_sha256': hashlib.sha256(content).hexdigest(), 'conflict_preview': conflict_preview, 'baseline_counts': baseline, 'after_archive': after_archive, 'after_link': before_finance, 'after_finance': report}, output, cls=DjangoJSONEncoder, ensure_ascii=False, indent=2)
            self.assertEqual(sum(m.objects.count() for m in (Transaction,InventoryMovement,Shipment,GoodsReceipt)),0)
