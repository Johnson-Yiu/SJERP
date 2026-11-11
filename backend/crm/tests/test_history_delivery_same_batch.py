import tempfile
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from crm.tests.test_history_takeover import HistoryTakeoverFixtureMixin
from crm.history_takeover import execute_group
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
        rows['采购明细'][0]['specification_snapshot'] = '24W'
        workbook = self.workbook_bytes(rows)
        def submit():
            return self.client.post("/api/import/history-takeovers/", {"file": SimpleUploadedFile("synthetic-history.xlsx", workbook)}, format="multipart")
        submitted = submit()
        self.assertEqual(submitted.status_code, 201, submitted.data)
        application = HistoryTakeoverApplication.objects.get(pk=submitted.data["id"])
        group = application.groups.get()
        dup = submit()
        self.assertEqual(dup.status_code, 200, dup.data)
        self.assertTrue(dup.data['duplicate_submission_reused'])
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
        result = self.client.post(url+'execute/', {}, format='json')
        self.assertEqual(result.status_code, 200, result.data)
        self.assertTrue(self.client.post(url+'execute/', {}, format='json').data['idempotent_replay'])
        self.assertEqual(SKU.objects.count(), 0)
        self.assertEqual(ArchivedHistoryLine.objects.count(), 2)
        self.assertEqual(sum(m.objects.count() for m in (Transaction,FinanceFact,InventoryMovement,Shipment,GoodsReceipt)),0)
        sku = SKU.objects.create(product=self.product, sku='B', display_name_cn='合成正式商品 B', specification='24W', unit='pcs')
        ids = list(group.source_records.filter(record_type__in=['销售明细','采购明细']).values_list('pk',flat=True))
        preview = self.client.post('/api/import/history-products/preview/', {'ids':ids,'target':sku.pk,'operation':'link','reason':'核对合成规格'}, format='json')
        self.assertEqual(preview.status_code,200,preview.data)
        linked = self.client.post('/api/import/history-products/apply/', {'token':preview.data['token']}, format='json')
        self.assertEqual(linked.status_code,200,linked.data)
        self.assertEqual(HistoryProductLink.objects.filter(sku=sku).count(),2)
        self.assertEqual(SKU.objects.count(),1)
        self.assertEqual(sum(m.objects.count() for m in (Transaction,FinanceFact,InventoryMovement,Shipment,GoodsReceipt)),0)
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
            self.assertEqual(sum(m.objects.count() for m in (Transaction,InventoryMovement,Shipment,GoodsReceipt)),0)
