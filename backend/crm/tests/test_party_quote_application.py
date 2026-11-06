"""Isolated tests for applying approved quote party corrections."""
from concurrent.futures import ThreadPoolExecutor, wait
from copy import deepcopy
from datetime import date
from decimal import Decimal
from threading import Barrier
from unittest import skipUnless
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.sessions.backends.db import SessionStore
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import close_old_connections, connection, connections
from django.test import Client, RequestFactory, TestCase, TransactionTestCase, override_settings

from crm.models import (Customer, Order, PartyQuoteApplication, PartyVersionApproval,
    Product, PurchaseOrder, Quote, QuoteItem, SKU, SKUTradeUnit, Supplier)
from crm.party_version import (apply_approved_quote_change, approve, baseline, propose,
                               _application_fingerprint, _quote_fingerprint)


class ApplicationFixture:
    def create_fixture(self):
        self.keys = []
        for name in ('maker', 'reviewer', 'operator'):
            username = 'apply-' + name
            get_user_model().objects.create_user(username=username, password='test-only-password')
            client = Client()
            self.assertTrue(client.login(username=username, password='test-only-password'))
            self.keys.append(client.session.session_key)
        self.customer = Customer.objects.create(code='APPLY-C', name='Buyer', country='Germany')
        self.supplier = Supplier.objects.create(code='AP', name='Supplier')
        self.quote = Quote.objects.create(quote_no='APPLY-Q', customer=self.customer,
            quote_date=date(2026, 1, 1), status='sent', buyer_company_name='Original',
            buyer_country_snapshot=None, buyer_tax_id=None, amount_calculation_version=1,
            currency='USD', exchange_rate='7.123456', shipping_fee='1.2345', discount='0.0500')
        product = Product.objects.create(code='APPLY-P', name='Product')
        sku = SKU.objects.create(product=product, sku='APPLY-SKU', unit='pcs')
        unit = SKUTradeUnit.objects.create(sku=sku, name='Pack', unit='pack', factor=Decimal('5'))
        # Bulk-create an actual historical empty snapshot: save() would fill it from today's SKU.
        QuoteItem.objects.bulk_create([QuoteItem(quote=self.quote, sku=sku, sku_code_snapshot='',
            sales_model_snapshot='', product_name_snapshot='', unit_snapshot='', image_snapshot='old/private.jpg',
            trade_unit=unit, trade_quantity=Decimal('2'), trade_unit_price=Decimal('3.1234'),
            trade_snapshot={'unit': 'pack', 'factor': '5', 'base_unit': 'pcs', 'allow_fraction': False},
            sales_rules_snapshot=[{'rule': 'original', 'unknown': None}], quantity=Decimal('10'),
            unit_price=Decimal('0.624680000000'), description='', notes='history')])
        self.order = Order.objects.create(order_no='APPLY-SO', customer=self.customer,
            quote=self.quote, order_date=date(2026, 1, 1), status='confirmed')
        self.purchase = PurchaseOrder.objects.create(purchase_no='APPLY-PO', supplier=self.supplier,
            order=self.order, order_date=date(2026, 1, 1), status='ordered')

    def session(self, index):
        request = RequestFactory().post('/')
        request.session = SessionStore(session_key=self.keys[index])
        return request

    def proposal(self, change_type='correction', source_trust='unverified'):
        data = baseline(request=self.session(0), target_type='quote', target_id=self.quote.pk)
        proposed = deepcopy(data['snapshot'])
        replacement = None
        if change_type == 'replacement':
            replacement = Customer.objects.create(code='APPLY-REPLACE', name='Replacement buyer')
        proposed['name'] = replacement.name if replacement else 'Corrected same legal party'
        return propose(request=self.session(0), target_type='quote', target_id=self.quote.pk,
            expected_base_fingerprint=data['fingerprint'], proposed_snapshot=proposed,
            change_type=change_type, reason='Correction reason', evidence='Evidence reference', source_trust=source_trust,
            replacement_target_id=replacement.pk if replacement else None)

    def approved(self, change_type='correction'):
        obj = self.proposal(change_type)
        approval = approve(request=self.session(1), request_id=obj.pk,
            expected_content_fingerprint=obj.content_fingerprint, note='Same-party evidence reviewed')
        return obj, approval


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class PartyQuoteApplicationTests(ApplicationFixture, TestCase):
    def setUp(self):
        self.create_fixture()

    def test_application_preserves_quote_and_line_facts_and_is_idempotent(self):
        obj, approval = self.approved()
        self.quote.refresh_from_db()
        source_item = self.quote.items.get()
        source_before = _quote_fingerprint(self.quote, [source_item])
        old_total = self.quote.total_amount
        order_before = (self.order.quote_id, self.order.status, self.order.customer_id)
        po_before = (self.purchase.order_id, self.purchase.status, self.purchase.supplier_id)
        application = apply_approved_quote_change(request=self.session(2), request_id=obj.pk)
        self.assertEqual(application.source_quote_id, self.quote.pk)
        self.assertEqual(application.approval_id, approval.pk)
        self.assertEqual(application.source_fingerprint, obj.source_document_fingerprint)
        approval.refresh_from_db()
        self.assertEqual(approval.application.pk, application.pk)
        self.assertEqual(application.source_fingerprint, source_before)
        self.assertEqual(application.application_fingerprint, _application_fingerprint(application))
        revision = Quote.objects.get(pk=application.result_quote_id)
        self.assertEqual(revision.party_application.approval.request.source_trust, 'unverified')
        self.assertEqual(revision.party_application.approval.request_id, obj.pk)
        self.assertEqual((revision.parent_quote_id, revision.root_quote_id, revision.customer_id, revision.status),
                         (self.quote.pk, self.quote.pk, self.customer.pk, 'draft'))
        self.assertEqual(revision.buyer_company_name, 'Corrected same legal party')
        self.assertIsNone(revision.buyer_tax_id)
        self.assertIsNone(revision.buyer_country_snapshot)
        self.assertEqual(revision.pi_template_snapshots, self.quote.pi_template_snapshots)
        self.assertEqual(revision.amount_calculation_version, self.quote.amount_calculation_version)
        self.assertEqual(revision.total_amount, old_total)
        new_item = revision.items.get()
        for field in QuoteItem._meta.concrete_fields:
            if field.name not in {'id', 'quote'}:
                self.assertEqual(getattr(new_item, field.attname), getattr(source_item, field.attname), field.name)
        self.assertEqual(application.revision_fingerprint, _quote_fingerprint(revision, [new_item]))
        self.quote.refresh_from_db()
        self.assertEqual(_quote_fingerprint(self.quote, list(self.quote.items.order_by('id'))), source_before)
        self.order.refresh_from_db(); self.purchase.refresh_from_db()
        self.assertEqual((self.order.quote_id, self.order.status, self.order.customer_id), order_before)
        self.assertEqual((self.purchase.order_id, self.purchase.status, self.purchase.supplier_id), po_before)
        again = apply_approved_quote_change(request=self.session(1), request_id=obj.pk)
        self.assertEqual(again.pk, application.pk)
        self.assertEqual(PartyQuoteApplication.objects.count(), 1)
        self.assertEqual(Quote.objects.filter(parent_quote=self.quote).count(), 1)
        with self.assertRaises(ValidationError):
            PartyQuoteApplication.objects.filter(pk=application.pk).update(source_fingerprint='x')
        with self.assertRaises(ValidationError):
            application.delete()

    def test_replay_rechecks_both_source_and_result_facts(self):
        obj, _approval = self.approved()
        application = apply_approved_quote_change(request=self.session(2), request_id=obj.pk)
        source_item = self.quote.items.get()
        result = Quote.objects.get(pk=application.result_quote_id)
        result_item = result.items.get()
        for item, message in ((source_item, '来源报价或明细已变更'),
                              (result_item, '生成修订或明细已变更')):
            original = item.image_snapshot.name
            with self.subTest(item=item.pk):
                QuoteItem.objects.filter(pk=item.pk).update(image_snapshot='tampered.jpg')
                with self.assertRaisesMessage(ValidationError, message):
                    apply_approved_quote_change(request=self.session(2), request_id=obj.pk)
                QuoteItem.objects.filter(pk=item.pk).update(image_snapshot=original)
        for quote, message in ((self.quote, '来源报价或明细已变更'),
                               (result, '生成修订或明细已变更')):
            with self.subTest(quote=quote.pk):
                Quote.objects.filter(pk=quote.pk).update(amount_calculation_version=2)
                with self.assertRaisesMessage(ValidationError, message):
                    apply_approved_quote_change(request=self.session(2), request_id=obj.pk)
                Quote.objects.filter(pk=quote.pk).update(amount_calculation_version=1)
        Quote.objects.filter(pk=self.quote.pk).update(status='accepted')
        self.assertEqual(apply_approved_quote_change(request=self.session(2), request_id=obj.pk).pk, application.pk)
        self.assertEqual(PartyQuoteApplication.objects.count(), 1)
        self.assertEqual(Quote.objects.filter(parent_quote=self.quote).count(), 1)

    def test_only_sent_or_accepted_quotes_can_be_proposed(self):
        for status in ('draft', 'rejected', 'expired'):
            with self.subTest(status=status):
                Quote.objects.filter(pk=self.quote.pk).update(status=status)
                with self.assertRaisesMessage(ValidationError, '只有已发送或已接受'):
                    self.proposal()
        self.assertFalse(PartyVersionApproval.objects.exists())
        self.assertFalse(PartyQuoteApplication.objects.exists())
        Quote.objects.filter(pk=self.quote.pk).update(status='accepted')
        obj = self.proposal()
        self.assertEqual(obj.quote_id, self.quote.pk)

    def test_existing_old_status_request_cannot_create_new_revision(self):
        obj, _approval = self.approved()
        for status in ('draft', 'rejected', 'expired'):
            with self.subTest(status=status):
                Quote.objects.filter(pk=self.quote.pk).update(status=status)
                with self.assertRaisesMessage(ValidationError, '只有已发送或已接受'):
                    apply_approved_quote_change(request=self.session(2), request_id=obj.pk)
        self.assertFalse(PartyQuoteApplication.objects.exists())
        self.assertFalse(Quote.objects.filter(parent_quote=self.quote).exists())

    def test_replacement_and_missing_approval_are_never_applied(self):
        obj = self.proposal('replacement')
        with self.assertRaisesMessage(ValidationError, '尚未批准'):
            apply_approved_quote_change(request=self.session(2), request_id=obj.pk)
        approve(request=self.session(1), request_id=obj.pk, expected_content_fingerprint=obj.content_fingerprint, note='Review')
        with self.assertRaisesMessage(ValidationError, '法律主体替换'):
            apply_approved_quote_change(request=self.session(2), request_id=obj.pk)
        self.assertEqual(PartyQuoteApplication.objects.count(), 0)
        self.assertFalse(Quote.objects.filter(parent_quote=self.quote).exists())

    def test_rejects_stale_and_tampered_approval_and_anonymous(self):
        obj, approval = self.approved()
        request = RequestFactory().post('/')
        with self.assertRaises(ValidationError):
            apply_approved_quote_change(request=request, request_id=obj.pk)
        with connection.cursor() as cursor:
            cursor.execute('UPDATE crm_partyversionapproval SET approved_fingerprint = %s WHERE id = %s', ['x' * 64, approval.pk])
        with self.assertRaisesMessage(ValidationError, '指纹不一致'):
            apply_approved_quote_change(request=self.session(2), request_id=obj.pk)
        with connection.cursor() as cursor:
            cursor.execute('UPDATE crm_partyversionapproval SET approved_fingerprint = %s WHERE id = %s', [obj.content_fingerprint, approval.pk])
        Quote.objects.filter(pk=self.quote.pk).update(buyer_address='Changed')
        with self.assertRaisesMessage(ValidationError, '基准快照已变更'):
            apply_approved_quote_change(request=self.session(2), request_id=obj.pk)
        self.assertFalse(PartyQuoteApplication.objects.exists())
        self.assertFalse(Quote.objects.filter(parent_quote=self.quote).exists())

    def test_unknown_source_trust_is_preserved_in_reverse_relation(self):
        obj = self.proposal(source_trust='unknown')
        approve(request=self.session(1), request_id=obj.pk,
            expected_content_fingerprint=obj.content_fingerprint, note='Reviewed')
        application = apply_approved_quote_change(request=self.session(2), request_id=obj.pk)
        revision = Quote.objects.get(pk=application.result_quote_id)
        self.assertEqual(revision.party_application.approval.request.source_trust, 'unknown')
        self.assertIsNone(revision.buyer_country_snapshot)
        self.assertIsNone(revision.buyer_tax_id)

    def test_changed_commercial_facts_rejected_before_approval_and_application(self):
        obj = self.proposal()
        item = self.quote.items.get()
        original_templates = deepcopy(self.quote.pi_template_snapshots)
        mutations = [
            (QuoteItem, item.pk, 'unit_price', Decimal('9'), item.unit_price),
            (QuoteItem, item.pk, 'image_snapshot', 'changed.jpg', item.image_snapshot.name),
            (QuoteItem, item.pk, 'sales_rules_snapshot', [{'changed': True}], item.sales_rules_snapshot),
            (Quote, self.quote.pk, 'pi_template_snapshots', {}, original_templates),
            (Quote, self.quote.pk, 'amount_calculation_version', 2, 1),
        ]
        for model, pk, field, changed, original in mutations:
            with self.subTest(stage='approve', field=field):
                model.objects.filter(pk=pk).update(**{field: changed})
                with self.assertRaisesMessage(ValidationError, '来源报价或明细已变更'):
                    approve(request=self.session(1), request_id=obj.pk,
                        expected_content_fingerprint=obj.content_fingerprint, note='Reviewed')
                self.assertFalse(PartyVersionApproval.objects.filter(request=obj).exists())
                model.objects.filter(pk=pk).update(**{field: original})
        approve(request=self.session(1), request_id=obj.pk,
            expected_content_fingerprint=obj.content_fingerprint, note='Reviewed')
        for model, pk, field, changed, original in mutations:
            with self.subTest(stage='apply', field=field):
                model.objects.filter(pk=pk).update(**{field: changed})
                with self.assertRaisesMessage(ValidationError, '来源报价或明细已变更'):
                    apply_approved_quote_change(request=self.session(2), request_id=obj.pk)
                self.assertFalse(PartyQuoteApplication.objects.exists())
                self.assertFalse(Quote.objects.filter(parent_quote=self.quote).exists())
                model.objects.filter(pk=pk).update(**{field: original})
        # A normal status change is not a change in the approved commercial facts.
        Quote.objects.filter(pk=self.quote.pk).update(status='accepted')
        application = apply_approved_quote_change(request=self.session(2), request_id=obj.pk)
        self.assertEqual(application.result_quote.status, 'draft')

    def test_pre_fingerprint_approval_can_be_read_but_not_applied(self):
        from crm.models import PartyVersionRequest
        from crm.party_version import _content, _digest, verified_approval
        base = baseline(request=self.session(0), target_type='quote', target_id=self.quote.pk)['snapshot']
        proposed = {**base, 'name': 'Old application'}
        obj = PartyVersionRequest(quote=self.quote, quote_customer=self.customer,
            initiator=get_user_model().objects.get(username='apply-maker'),
            base_snapshot=base, proposed_snapshot=proposed, base_fingerprint=_digest(base),
            change_type='correction', reason='Reason', evidence='Evidence', source_trust='unknown')
        obj.content_fingerprint = _digest(_content(obj))
        obj.save(force_insert=True)
        approve(request=self.session(1), request_id=obj.pk,
            expected_content_fingerprint=obj.content_fingerprint, note='Reviewed')
        verified_approval(request=self.session(2), request_id=obj.pk)
        with self.assertRaisesMessage(ValidationError, '缺少来源报价指纹'):
            apply_approved_quote_change(request=self.session(2), request_id=obj.pk)
        self.assertFalse(PartyQuoteApplication.objects.exists())

    def test_customer_identity_is_signed_and_cannot_be_rebound(self):
        obj, _approval = self.approved()
        self.assertEqual(obj.quote_customer_id, self.customer.pk)
        other = Customer.objects.create(code='APPLY-C2', name='Other buyer', country='Germany')
        # Deliberate test-only bypass of the existing formal-party guard.
        Quote.objects.filter(pk=self.quote.pk).update(customer=other)
        with self.assertRaisesMessage(ValidationError, '客户身份'):
            apply_approved_quote_change(request=self.session(2), request_id=obj.pk)
        self.assertFalse(PartyQuoteApplication.objects.exists())
        self.assertFalse(Quote.objects.filter(parent_quote=self.quote).exists())

    def test_unknown_country_and_tax_cannot_be_upgraded_on_application(self):
        base = baseline(request=self.session(0), target_type='quote', target_id=self.quote.pk)
        proposed = deepcopy(base['snapshot'])
        proposed.update(name='Corrected same party', country='')
        obj = propose(request=self.session(0), target_type='quote', target_id=self.quote.pk,
            expected_base_fingerprint=base['fingerprint'], proposed_snapshot=proposed,
            change_type='correction', reason='Reason', evidence='Evidence', source_trust='unknown')
        approve(request=self.session(1), request_id=obj.pk,
            expected_content_fingerprint=obj.content_fingerprint, note='Reviewed')
        with self.assertRaisesMessage(ValidationError, '历史未知主体字段'):
            apply_approved_quote_change(request=self.session(2), request_id=obj.pk)
        self.assertFalse(PartyQuoteApplication.objects.exists())

    def test_failure_rolls_back_revision_and_counters(self):
        obj, _approval = self.approved()
        from crm.models import QuoteChildRevisionCounter, QuoteRevisionCounter
        with patch('crm.party_version.PartyQuoteApplication.save', side_effect=RuntimeError('application audit failure')):
            with self.assertRaises(RuntimeError):
                apply_approved_quote_change(request=self.session(2), request_id=obj.pk)
        self.assertFalse(PartyQuoteApplication.objects.exists())
        self.assertFalse(Quote.objects.filter(parent_quote=self.quote).exists())
        self.assertFalse(QuoteRevisionCounter.objects.filter(root_quote=self.quote).exists())
        self.assertFalse(QuoteChildRevisionCounter.objects.filter(parent_quote=self.quote).exists())
        self.assertEqual(apply_approved_quote_change(request=self.session(2), request_id=obj.pk).result_quote.parent_quote_id, self.quote.pk)

    def test_permission_required_even_for_replay(self):
        obj, _approval = self.approved()
        apply_approved_quote_change(request=self.session(2), request_id=obj.pk)
        with override_settings(RBAC_ENFORCEMENT=True, DEVELOPMENT_SUPERADMIN=False):
            with self.assertRaises(PermissionDenied):
                apply_approved_quote_change(request=self.session(2), request_id=obj.pk)


@skipUnless(connection.vendor == 'postgresql', 'Requires PostgreSQL row locks and independent DB sessions')
@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class PartyQuoteApplicationConcurrencyTests(ApplicationFixture, TransactionTestCase):
    def setUp(self):
        self.create_fixture()

    def test_two_authenticated_sessions_apply_once(self):
        obj, _approval = self.approved()
        gate = Barrier(2, timeout=10)
        def worker(index):
            close_old_connections()
            try:
                with connections['default'].cursor() as cursor:
                    cursor.execute("SET statement_timeout = '15000ms'")
                    cursor.execute("SET lock_timeout = '10000ms'")
                    cursor.execute('SELECT pg_backend_pid()')
                    pid = cursor.fetchone()[0]
                gate.wait()
                return pid, apply_approved_quote_change(request=self.session(index + 1), request_id=obj.pk).pk
            finally:
                connections['default'].close()
        pool = ThreadPoolExecutor(max_workers=2)
        futures = [pool.submit(worker, i) for i in range(2)]
        try:
            done, pending = wait(futures, timeout=30)
            self.assertFalse(pending)
            results = [f.result() for f in futures]
        finally:
            pool.shutdown(wait=False, cancel_futures=True)
        self.assertNotEqual(results[0][0], results[1][0])
        self.assertEqual(results[0][1], results[1][1])
        self.assertEqual(PartyQuoteApplication.objects.count(), 1)
        self.assertEqual(Quote.objects.filter(parent_quote=self.quote).count(), 1)
