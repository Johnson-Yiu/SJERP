"""PostgreSQL-only trigger and concurrent creation acceptance, synthetic data."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import DatabaseError, close_old_connections, connection, connections, transaction
from django.test import TransactionTestCase, override_settings
from rest_framework.test import APIClient

from crm.models import Customer, Order, PurchaseOrder, Quote, Supplier
from crm.party_replacement_models import PartyReplacementLink
from crm.tests import test_quote_buyer_tax_id as tax_fixtures


@skipUnless(connection.vendor == 'postgresql', 'requires isolated PostgreSQL')
@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class ReplacementPostgresTests(TransactionTestCase):
    def setUp(self):
        tax_fixtures.QuoteBuyerTaxTests.setUp(self)
        users = get_user_model()
        users.objects.create_user(username='pg-replacement-maker', password='test-only')
        users.objects.create_user(username='pg-replacement-reviewer', password='test-only')
        self.maker, self.reviewer = APIClient(), APIClient()
        self.assertTrue(self.maker.login(username='pg-replacement-maker', password='test-only'))
        self.assertTrue(self.reviewer.login(username='pg-replacement-reviewer', password='test-only'))

    def test_append_only_guards_even_on_empty_tables(self):
        for table in ('crm_partyreplacementtarget', 'crm_partyreplacementlink'):
            for sql in (f'UPDATE {table} SET id=id', f'DELETE FROM {table}', f'TRUNCATE TABLE {table}'):
                with self.subTest(sql=sql), self.assertRaises(DatabaseError):
                    with transaction.atomic():
                        with connection.cursor() as cursor:
                            cursor.execute(sql)

    def test_order_and_purchase_retry_formalization_and_details_serialize(self):
        from crm.party_document_details import unknown_details
        target_customer = Customer.objects.create(code='PG-NEW-C', name='Synthetic PG replacement customer')
        old_supplier = Supplier.objects.create(code='P1', name='Synthetic PG original supplier')
        new_supplier = Supplier.objects.create(code='P2', name='Synthetic PG replacement supplier')
        order = Order.objects.create(order_no='PG-SOURCE-SO', customer=self.customer, order_date='2026-11-05', status='confirmed', customer_name_snapshot=self.customer.name)
        purchase = PurchaseOrder.objects.create(purchase_no='PG-SOURCE-PO', supplier=old_supplier, order_date='2026-11-05', status='ordered', supplier_name_snapshot=old_supplier.name)
        for kind, route, source, target in [('order', 'orders', order, target_customer), ('purchase_order', 'purchase-orders', purchase, new_supplier)]:
            with self.subTest(kind=kind):
                url = f'/api/{route}/{source.pk}/party-change/'
                basis = self.maker.get(url).data['baseline']
                proposed = dict(basis['snapshot'], name=target.name)
                proposal = self.maker.post(url, {'expected_base_fingerprint': basis['fingerprint'], 'proposed_snapshot': proposed,
                    'change_type': 'replacement', 'reason': 'Synthetic', 'evidence': 'Synthetic', 'source_trust': 'unverified', 'replacement_target_id': target.pk}, format='json')
                self.assertEqual(proposal.status_code, 201, proposal.data)
                decision = self.reviewer.post(f"{url}{proposal.data['id']}/approve/", {'expected_content_fingerprint': proposal.data['content_fingerprint'], 'note': 'Reviewed'}, format='json')
                self.assertEqual(decision.status_code, 200, decision.data)
                endpoint = f"{url}{proposal.data['id']}/create-replacement/"
                payload = {('customer' if kind == 'order' else 'supplier'): target.pk, 'order_date': '2026-11-05',
                    'currency': 'USD', 'exchange_rate': '7.2', 'items': [{'sku': self.sku.pk, 'quantity': '2', 'unit_price': '3'}]}
                payload.update({'shipping_fee': '0', 'discount': '0', 'tail_goods_policy': 'SAME_CARTON'} if kind == 'order' else {'payment_terms_snapshot': []})
                created = self.maker.post(endpoint, payload, format='json')
                self.assertEqual(created.status_code, 200, created.data)
                result_id = created.data['result_order_id' if kind == 'order' else 'result_purchase_order_id']
                barrier = Barrier(3)
                def invoke(action):
                    close_old_connections()
                    try:
                        client = APIClient()
                        assert client.login(username='pg-replacement-maker', password='test-only')
                        barrier.wait(timeout=15)
                        response = (client.post(endpoint, payload, format='json') if action == 'retry' else
                            client.put(f'/api/{route}/{result_id}/party-details/', {'details': unknown_details()}, format='json') if action == 'details' else
                            client.post(f'/api/{route}/{result_id}/' + ('confirm/' if kind == 'order' else 'place/'), {}, format='json'))
                        return response.status_code, response.data
                    finally:
                        connections['default'].close()
                with ThreadPoolExecutor(max_workers=3) as pool:
                    retry, formal, details = list(pool.map(invoke, ('retry', 'formalize', 'details')))
                self.assertEqual(retry[0], 200, retry)
                self.assertIn((formal[0], details[0]), {(200, 400), (400, 200)}, (formal, details))
                result = source.__class__.objects.get(pk=result_id)
                self.assertEqual(result.status, ('confirmed' if kind == 'order' else 'ordered') if formal[0] == 200 else 'draft')

    def test_concurrent_same_payload_creates_one_linked_quote(self):
        created = self.client.post('/api/quotes/', {'customer': self.customer.pk, 'quote_date': '2026-11-05',
            'currency': 'USD', 'items': [{'sku': self.sku.pk, 'quantity': '1', 'unit_price': '10'}]}, format='json')
        self.assertEqual(created.status_code, 201, created.data)
        source = Quote.objects.get(pk=created.data['id'])
        Quote.objects.filter(pk=source.pk).update(status='sent')
        target = Customer.objects.create(code='PG-R', name='Synthetic PG target', country='France')
        url = f'/api/quotes/{source.pk}/party-change/'
        base = self.maker.get(url).data['baseline']
        proposed = dict(base['snapshot'], name=target.name, country='France', address='', contact='', phone='', email='', tax_id='')
        proposal = self.maker.post(url, {'expected_base_fingerprint': base['fingerprint'], 'proposed_snapshot': proposed,
            'change_type': 'replacement', 'reason': 'Synthetic', 'evidence': 'Synthetic', 'source_trust': 'unverified', 'replacement_target_id': target.pk}, format='json')
        self.assertEqual(proposal.status_code, 201, proposal.data)
        decision = self.reviewer.post(f"{url}{proposal.data['id']}/approve/", {'expected_content_fingerprint': proposal.data['content_fingerprint'], 'note': 'Reviewed'}, format='json')
        self.assertEqual(decision.status_code, 200, decision.data)
        endpoint = f"{url}{proposal.data['id']}/create-replacement/"
        payload = {'customer': target.pk, 'quote_date': '2026-11-05', 'currency': 'USD', 'exchange_rate': '7.2',
            'shipping_fee': '0', 'discount': '0', 'deposit_ratio': '0.3', 'trading_terms': '', 'shipping_details': '',
            'recipient_name': '', 'buyer_address': '', 'buyer_email': '', 'buyer_phone': '', 'buyer_tax_id': '',
            'items': [{'sku': self.sku.pk, 'quantity': '2', 'unit_price': '3'}]}
        from crm.party_document_details import unknown_details
        barrier = Barrier(2)
        def submit():
            close_old_connections()
            try:
                client = APIClient()
                assert client.login(username='pg-replacement-maker', password='test-only')
                barrier.wait(timeout=10)
                response = client.post(endpoint, payload, format='json')
                return response.status_code, response.data
            finally:
                connections['default'].close()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: submit(), range(2)))
        self.assertEqual([r[0] for r in results], [200, 200], results)
        self.assertEqual(results[0][1], results[1][1])
        self.assertEqual(PartyReplacementLink.objects.count(), 1)
        self.assertEqual(Quote.objects.count(), 2)
        result_id = results[0][1]['result_quote_id']
        barrier = Barrier(3)
        def retry_or_formalize(action):
            close_old_connections()
            try:
                client = APIClient()
                assert client.login(username='pg-replacement-maker', password='test-only')
                barrier.wait(timeout=10)
                response = (client.post(endpoint, payload, format='json') if action == 'retry' else
                            client.put(f'/api/quotes/{result_id}/party-details/', {'details': unknown_details()}, format='json') if action == 'details' else
                            client.post(f'/api/quotes/{result_id}/mark-sent/', {}, format='json'))
                return response.status_code, response.data
            finally:
                connections['default'].close()
        with ThreadPoolExecutor(max_workers=3) as pool:
            retry, formal, details = list(pool.map(retry_or_formalize, ('retry', 'formalize', 'details')))
        self.assertEqual(retry[0], 200, retry)
        self.assertIn((formal[0], details[0]), {(200, 400), (400, 200)}, (formal, details))
        self.assertEqual(Quote.objects.get(pk=result_id).status, 'sent' if formal[0] == 200 else 'draft')

    def test_source_change_serializes_before_link_lock_and_is_rejected(self):
        from crm.models import PartyVersionApproval, PartyVersionRequest
        from crm.party_replacement import _link_hash, prepare_formalization
        from crm.party_version import _approval_attestation_fingerprint

        created = self.client.post('/api/quotes/', {'customer': self.customer.pk, 'quote_date': '2026-11-05',
            'currency': 'USD', 'items': [{'sku': self.sku.pk, 'quantity': '1', 'unit_price': '10'}]}, format='json')
        self.assertEqual(created.status_code, 201, created.data)
        source = Quote.objects.get(pk=created.data['id'])
        Quote.objects.filter(pk=source.pk).update(status='sent')
        target = Customer.objects.create(code='PG-S', name='Synthetic target PG', country='France')
        url = f'/api/quotes/{source.pk}/party-change/'
        base = self.maker.get(url).data['baseline']
        proposed = dict(base['snapshot'], name=target.name, country='France', address='', contact='', phone='', email='', tax_id='')
        proposal = self.maker.post(url, {'expected_base_fingerprint': base['fingerprint'], 'proposed_snapshot': proposed,
            'change_type': 'replacement', 'reason': 'Synthetic', 'evidence': 'Synthetic', 'source_trust': 'unverified', 'replacement_target_id': target.pk}, format='json')
        self.assertEqual(proposal.status_code, 201, proposal.data)
        decision = self.reviewer.post(f"{url}{proposal.data['id']}/approve/", {'expected_content_fingerprint': proposal.data['content_fingerprint'], 'note': 'Reviewed'}, format='json')
        self.assertEqual(decision.status_code, 200, decision.data)
        obj = PartyVersionRequest.objects.get(pk=proposal.data['id'])
        approval = PartyVersionApproval.objects.get(request=obj)
        result = Quote.objects.create(quote_no='SYN-PG-REPLACEMENT', customer=target, quote_date='2026-11-05', buyer_tax_id='')
        link = PartyReplacementLink(target=obj.replacement_target, approval=approval, result_quote=result,
            created_by=obj.initiator, approved_fingerprint=obj.content_fingerprint,
            approval_fingerprint=_approval_attestation_fingerprint(approval), payload_fingerprint='a' * 64)
        link.link_fingerprint = _link_hash(link)
        link.save()
        PartyVersionRequest._base_manager.filter(pk=obj.pk).update(is_active=False)
        ready, attempt, finished = Event(), Event(), Event()

        def writer():
            close_old_connections()
            try:
                with transaction.atomic():
                    locked = Quote.objects.select_for_update().get(pk=source.pk)
                    ready.set()
                    self.assertTrue(attempt.wait(10))
                    # The competing prelock must be waiting on source, not
                    # holding the link and waiting for source.
                    PartyReplacementLink.objects.select_for_update(nowait=True).get(pk=link.pk)
                    # Isolated fault injection: formal quote fields normally
                    # cannot be edited through the model/API.
                    Quote.objects.filter(pk=locked.pk).update(buyer_address='Synthetic changed basis')
                return 'committed'
            finally:
                connections['default'].close()

        def formalizer():
            close_old_connections()
            try:
                self.assertTrue(ready.wait(10))
                attempt.set()
                try:
                    with transaction.atomic():
                        prepare_formalization('quote', result.pk)
                except ValidationError:
                    return 'rejected'
                return 'unexpected success'
            finally:
                finished.set()
                connections['default'].close()

        with ThreadPoolExecutor(max_workers=2) as pool:
            write = pool.submit(writer)
            check = pool.submit(formalizer)
            self.assertEqual(write.result(timeout=20), 'committed')
            self.assertEqual(check.result(timeout=20), 'rejected')
        self.assertTrue(finished.is_set())
