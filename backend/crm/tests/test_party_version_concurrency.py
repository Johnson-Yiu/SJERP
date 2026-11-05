"""PostgreSQL row-lock verification for party correction proposals and approvals."""
from concurrent.futures import ThreadPoolExecutor, wait
from datetime import date
from threading import Barrier
from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.contrib.sessions.backends.db import SessionStore
from django.core.exceptions import ValidationError
from django.db import close_old_connections, connection, connections
from django.test import Client, RequestFactory, TransactionTestCase, override_settings

from crm.models import Customer, PartyVersionApproval, PartyVersionRequest, Quote
from crm.party_version import approve, baseline, propose


@skipUnless(connection.vendor == 'postgresql', 'Requires PostgreSQL row locks and independent database sessions')
@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class PartyVersionPostgresConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.session_keys = []
        for suffix in ('initiator', 'reviewer1', 'reviewer2'):
            username = f'party-concurrency-{suffix}'
            get_user_model().objects.create_user(username=username, password='test-only-password')
            client = Client()
            self.assertTrue(client.login(username=username, password='test-only-password'))
            self.session_keys.append(client.session.session_key)
        self.assertEqual(len(set(self.session_keys)), 3)
        customer = Customer.objects.create(code='PVC-PG', name='Party concurrency customer')
        self.quote = Quote.objects.create(quote_no='PVC-PG-QUOTE', customer=customer, quote_date=date(2026, 1, 1), status='sent')
        self.original = baseline(request=self.request_for(0), target_type='quote', target_id=self.quote.pk)
        self.proposed = {key: value if value is not None else '' for key, value in self.original['snapshot'].items()}
        self.proposed['name'] = 'Corrected party'

    def request_for(self, index):
        request = RequestFactory().post('/')
        request.session = SessionStore(session_key=self.session_keys[index])
        return request

    def proposal(self, index):
        return propose(request=self.request_for(index), target_type='quote', target_id=self.quote.pk,
            expected_base_fingerprint=self.original['fingerprint'], proposed_snapshot=self.proposed,
            change_type='correction', reason='Correct party', evidence='Source reference', source_trust='unverified')

    def compete(self, function):
        barrier = Barrier(2, timeout=10)

        def worker(index):
            close_old_connections()
            try:
                with connections['default'].cursor() as cursor:
                    cursor.execute("SET statement_timeout = '15000ms'")
                    cursor.execute("SET lock_timeout = '10000ms'")
                    cursor.execute('SELECT pg_backend_pid()')
                    pid = cursor.fetchone()[0]
                barrier.wait()
                try:
                    result = function(index)
                    return pid, 'success', result.pk
                except ValidationError as error:
                    return pid, 'rejected', str(error)
            finally:
                connections['default'].close()

        pool = ThreadPoolExecutor(max_workers=2)
        futures = [pool.submit(worker, index) for index in range(2)]
        try:
            done, pending = wait(futures, timeout=30)
            self.assertFalse(pending, 'Concurrent operations exceeded the bounded wait')
            results = [future.result() for future in futures]
        finally:
            pool.shutdown(wait=False, cancel_futures=True)
        self.assertNotEqual(results[0][0], results[1][0], 'Workers must use independent PostgreSQL connections')
        self.assertEqual(sorted(result[1] for result in results), ['rejected', 'success'])
        return results

    def test_two_sessions_compete_for_same_baseline(self):
        results = self.compete(lambda index: self.proposal(index))
        self.assertEqual(PartyVersionRequest.objects.count(), 1)
        self.assertEqual(PartyVersionApproval.objects.count(), 0)
        obj = PartyVersionRequest.objects.get()
        self.assertEqual(obj.pk, next(result[2] for result in results if result[1] == 'success'))
        self.assertEqual(obj.base_snapshot, self.original['snapshot'])
        self.assertEqual(obj.base_fingerprint, self.original['fingerprint'])
        self.assertEqual(obj.proposed_snapshot, self.proposed)
        self.assertEqual(baseline(request=self.request_for(0), target_type='quote', target_id=self.quote.pk), self.original)

    def test_two_sessions_compete_to_approve_same_request(self):
        obj = self.proposal(0)
        results = self.compete(lambda index: approve(request=self.request_for(index + 1), request_id=obj.pk,
            expected_content_fingerprint=obj.content_fingerprint, note='Reviewed'))
        self.assertEqual(PartyVersionRequest.objects.count(), 1)
        self.assertEqual(PartyVersionApproval.objects.count(), 1)
        decision = PartyVersionApproval.objects.get()
        self.assertEqual(decision.pk, next(result[2] for result in results if result[1] == 'success'))
        self.assertEqual(decision.request_id, obj.pk)
        self.assertEqual(decision.approved_fingerprint, obj.content_fingerprint)
        self.assertNotEqual(decision.approver_id, obj.initiator_id)
        self.assertEqual(baseline(request=self.request_for(0), target_type='quote', target_id=self.quote.pk), self.original)
