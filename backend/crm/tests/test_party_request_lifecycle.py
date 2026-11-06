"""Party request lifecycle: history, authorization, and bounded concurrency."""
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from datetime import date
from threading import Barrier, Event
from time import monotonic, sleep
from unittest import skipUnless
from unittest.mock import patch

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, close_old_connections, connection, connections, transaction
from django.test import TestCase, TransactionTestCase, override_settings
from rest_framework.test import APIClient

from crm.models import Order, OrderItem, PartyVersionApproval, PartyVersionRequest, Quote
from crm.party_version_models import PartyVersionTerminalEvent
from crm.party_version import (apply_approved_quote_change, approve, get_request_lifecycle,
                               invalidate, reject, verified_approval, withdraw)
from crm.tests.test_party_quote_application import ApplicationFixture


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class PartyLifecycleTests(ApplicationFixture, TestCase):
    def setUp(self):
        self.create_fixture()

    def test_reject_withdraw_invalidate_and_reapply_preserve_history(self):
        for fn, index, kind in ((reject, 1, 'rejected'), (withdraw, 0, 'withdrawn'), (invalidate, 2, 'invalidated')):
            with self.subTest(kind=kind):
                obj = self.proposal()
                self.assertEqual(get_request_lifecycle(request=self.session(0), request_id=obj.pk)['status'], 'pending')
                event = fn(request=self.session(index), request_id=obj.pk, note='Documented reason')
                self.assertEqual(event.kind, kind)
                self.assertEqual(event.request_fingerprint, obj.content_fingerprint)
                self.assertEqual(fn(request=self.session(index), request_id=obj.pk, note='Documented reason').pk, event.pk)
                status = get_request_lifecycle(request=self.session(1), request_id=obj.pk)
                self.assertEqual(status['status'], kind)
                self.assertEqual(status['terminal_event']['id'], event.pk)
                with self.assertRaises(ValidationError):
                    approve(request=self.session(1), request_id=obj.pk, expected_content_fingerprint=obj.content_fingerprint, note='Late')
                with self.assertRaises(ValidationError):
                    event.delete()
                self.assertTrue(PartyVersionRequest.objects.filter(pk=obj.pk, is_active=False).exists())
        self.assertEqual(PartyVersionRequest.objects.count(), 3)
        self.assertEqual(PartyVersionTerminalEvent.objects.count(), 3)
        again = self.proposal()
        self.assertTrue(again.is_active)
        self.assertEqual(PartyVersionRequest.objects.count(), 4)

    def test_auth_separation_and_terminal_conflicts(self):
        obj = self.proposal()
        with self.assertRaises(ValidationError):
            reject(request=self.session(0), request_id=obj.pk, note='No')
        with self.assertRaises(PermissionDenied):
            withdraw(request=self.session(1), request_id=obj.pk, note='No')
        with self.assertRaises(ValidationError):
            invalidate(request=self.session(2), request_id=obj.pk, note=' ')
        from django.test import RequestFactory
        with self.assertRaises(ValidationError):
            reject(request=RequestFactory().post('/'), request_id=obj.pk, note='No')
        event = reject(request=self.session(1), request_id=obj.pk, note='No')
        with self.assertRaises(ValidationError):
            reject(request=self.session(2), request_id=obj.pk, note='No')
        with self.assertRaises(ValidationError):
            withdraw(request=self.session(0), request_id=obj.pk, note='No')
        self.assertEqual(PartyVersionTerminalEvent.objects.count(), 1)
        self.assertEqual(event.actor_id, PartyVersionTerminalEvent.objects.get().actor_id)

    def test_approved_invalidation_releases_slot_and_blocks_application(self):
        obj, decision = self.approved('replacement')
        self.assertEqual(get_request_lifecycle(request=self.session(0), request_id=obj.pk)['status'], 'approved')
        with self.assertRaises(ValidationError):
            withdraw(request=self.session(0), request_id=obj.pk, note='No')
        with self.assertRaises(ValidationError):
            reject(request=self.session(1), request_id=obj.pk, note='No')
        invalidate(request=self.session(2), request_id=obj.pk, note='Outdated')
        with self.assertRaises(ValidationError):
            verified_approval(request=self.session(1), request_id=obj.pk)
        with self.assertRaises(ValidationError):
            apply_approved_quote_change(request=self.session(2), request_id=obj.pk)
        self.assertTrue(PartyVersionApproval.objects.filter(pk=decision.pk).exists())
        self.assertTrue(self.proposal().is_active)

    def test_database_uniqueness_and_rollback(self):
        obj = self.proposal()
        with self.assertRaises(IntegrityError), transaction.atomic():
            PartyVersionRequest._base_manager.filter(pk=obj.pk).update(is_active=True)
            values = {field.attname: getattr(obj, field.attname) for field in obj._meta.concrete_fields
                      if field.name not in {'id', 'created_at'}}
            values['base_fingerprint'] = '0' * 64
            PartyVersionRequest._base_manager.create(**values)
        with patch('crm.party_version.PartyVersionTerminalEvent.objects.create', side_effect=RuntimeError('failed')):
            with self.assertRaises(RuntimeError):
                reject(request=self.session(1), request_id=obj.pk, note='Fail')
        self.assertTrue(PartyVersionRequest.objects.get(pk=obj.pk).is_active)
        self.assertFalse(PartyVersionTerminalEvent.objects.filter(request=obj).exists())

    def test_order_and_purchase_reapply_use_effective_version_baseline(self):
        from copy import deepcopy
        from crm.models import PurchaseOrder
        from crm.party_version import baseline, propose
        from crm.party_document_version import apply as apply_document
        Order.objects.filter(pk=self.order.pk).update(customer_name_snapshot='Buyer', customer_address_snapshot='Original')
        PurchaseOrder.objects.filter(pk=self.purchase.pk).update(supplier_name_snapshot='Supplier', supplier_address_snapshot='Original')
        for kind, target in (('order', self.order), ('purchase_order', self.purchase)):
            with self.subTest(kind=kind):
                for number in (1, 2):
                    current = baseline(request=self.session(0), target_type=kind, target_id=target.pk)
                    self.assertEqual(current['snapshot']['address'], 'Original' if number == 1 else 'Version 1')
                    proposed = deepcopy(current['snapshot']); proposed['address'] = f'Version {number}'
                    obj = propose(request=self.session(0), target_type=kind, target_id=target.pk,
                        expected_base_fingerprint=current['fingerprint'], proposed_snapshot=proposed,
                        change_type='correction', reason='Reason', evidence='Evidence', source_trust='unknown')
                    approve(request=self.session(1), request_id=obj.pk,
                        expected_content_fingerprint=obj.content_fingerprint, note='Reviewed')
                    version = apply_document(request=self.session(2), request_id=obj.pk)
                    self.assertEqual(version.version_no, number)
                    self.assertEqual(get_request_lifecycle(request=self.session(0), request_id=obj.pk)['status'], 'applied')
                    # Fault injection: even a corrupted active marker must
                    # never let an already-effective SO/PO version terminate.
                    PartyVersionRequest._base_manager.filter(pk=obj.pk).update(is_active=True)
                    with self.assertRaisesMessage(ValidationError, '已应用'):
                        invalidate(request=self.session(2), request_id=obj.pk, note='Must reject')
                    PartyVersionRequest._base_manager.filter(pk=obj.pk).update(is_active=False)
                current = baseline(request=self.session(0), target_type=kind, target_id=target.pk)
                self.assertEqual(current['snapshot']['address'], 'Version 2')
                target.refresh_from_db()
                self.assertEqual(getattr(target, 'customer_address_snapshot' if kind == 'order' else 'supplier_address_snapshot'), 'Original')

    def test_legacy_order_request_keeps_original_basis_and_cannot_apply(self):
        from crm.party_version import _content, _digest, baseline, propose
        from crm.party_document_version import apply as apply_document
        Order.objects.filter(pk=self.order.pk).update(customer_name_snapshot='Buyer', customer_address_snapshot='Original')
        original = baseline(request=self.session(0), target_type='order', target_id=self.order.pk)['snapshot']
        proposed = {**original, 'address': 'Current version'}
        first = propose(request=self.session(0), target_type='order', target_id=self.order.pk,
            expected_base_fingerprint=_digest(original), proposed_snapshot=proposed,
            change_type='correction', reason='Reason', evidence='Evidence', source_trust='unknown')
        approve(request=self.session(1), request_id=first.pk,
            expected_content_fingerprint=first.content_fingerprint, note='Review')
        apply_document(request=self.session(2), request_id=first.pk)
        self.assertEqual(baseline(request=self.session(0), target_type='order', target_id=self.order.pk)['snapshot']['address'], 'Current version')
        # A pre-identity synthetic request retains original-basis verification.
        legacy = PartyVersionRequest(order=self.order, initiator=first.initiator,
            base_snapshot=original, proposed_snapshot={**original, 'address': 'Old proposal'},
            base_fingerprint=_digest(original), change_type='correction', reason='Old reason',
            evidence='Old evidence', source_trust='unknown')
        legacy.content_fingerprint = _digest(_content(legacy)); legacy.save(force_insert=True)
        approve(request=self.session(1), request_id=legacy.pk,
            expected_content_fingerprint=legacy.content_fingerprint, note='Old review')
        self.assertEqual(verified_approval(request=self.session(2), request_id=legacy.pk).request_id, legacy.pk)
        with self.assertRaisesMessage(ValidationError, '身份指纹'):
            apply_document(request=self.session(2), request_id=legacy.pk)

    def test_applied_history_remains_replayable_and_cannot_be_invalidated(self):
        obj, _ = self.approved()
        application = apply_approved_quote_change(request=self.session(2), request_id=obj.pk)
        self.assertEqual(get_request_lifecycle(request=self.session(0), request_id=obj.pk)['status'], 'applied')
        with self.assertRaises(ValidationError):
            invalidate(request=self.session(2), request_id=obj.pk, note='No')
        self.assertEqual(apply_approved_quote_change(request=self.session(1), request_id=obj.pk).pk, application.pk)


@skipUnless(connection.vendor == 'postgresql', 'requires PostgreSQL independent connections')
@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class PartyLifecyclePostgresTests(ApplicationFixture, TransactionTestCase):
    def setUp(self):
        self.create_fixture()

    def _parallel(self, functions):
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
                    return pid, 'ok', functions[index]()
                except (ValidationError, PermissionDenied) as exc:
                    return pid, 'rejected', str(exc)
            finally:
                connections['default'].close()
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(worker, i) for i in range(2)]
            results = [f.result(timeout=25) for f in futures]
        self.assertNotEqual(results[0][0], results[1][0])
        return results

    def test_approval_races_rejection_once(self):
        obj = self.proposal()
        results = self._parallel([
            lambda: approve(request=self.session(1), request_id=obj.pk, expected_content_fingerprint=obj.content_fingerprint, note='Review'),
            lambda: reject(request=self.session(2), request_id=obj.pk, note='Reject')])
        self.assertEqual(sorted(row[1] for row in results), ['ok', 'rejected'])
        self.assertEqual(PartyVersionApproval.objects.filter(request=obj).count() + PartyVersionTerminalEvent.objects.filter(request=obj).count(), 1)

    def test_approval_races_withdrawal_and_invalidation(self):
        for kind in ('withdraw', 'invalidate'):
            with self.subTest(kind=kind):
                self.quote = Quote.objects.create(quote_no='RACE-' + kind, customer=self.customer,
                    quote_date=date(2026, 1, 1), status='sent', buyer_company_name='Buyer')
                obj = self.proposal()
                terminal = (lambda: withdraw(request=self.session(0), request_id=obj.pk, note='Withdraw')) if kind == 'withdraw' else (lambda: invalidate(request=self.session(2), request_id=obj.pk, note='Invalidate'))
                results = self._parallel([
                    lambda: approve(request=self.session(1), request_id=obj.pk,
                        expected_content_fingerprint=obj.content_fingerprint, note='Review'), terminal])
                statuses = sorted(row[1] for row in results)
                approvals = PartyVersionApproval.objects.filter(request=obj)
                events = PartyVersionTerminalEvent.objects.filter(request=obj)
                if kind == 'invalidate' and statuses == ['ok', 'ok']:
                    # Invalidation is explicitly allowed after approval, so a
                    # serialized approval followed by invalidation is valid.
                    self.assertEqual(approvals.count(), 1)
                    self.assertEqual(events.count(), 1)
                    self.assertEqual(events.get().kind, 'invalidated')
                    self.assertLessEqual(approvals.get().created_at, events.get().created_at)
                    obj.refresh_from_db()
                    self.assertFalse(obj.is_active)
                else:
                    self.assertEqual(statuses, ['ok', 'rejected'])
                    self.assertEqual(approvals.count() + events.count(), 1)

    def test_identical_terminal_retries_return_one_event(self):
        obj = self.proposal()
        def same():
            return reject(request=self.session(1), request_id=obj.pk, note='Reject once')
        results = self._parallel([same, same])
        self.assertEqual([row[1] for row in results], ['ok', 'ok'])
        self.assertEqual(results[0][2].pk, results[1][2].pk)
        self.assertEqual(PartyVersionTerminalEvent.objects.filter(request=obj).count(), 1)

    def test_reapply_competes_under_database_uniqueness(self):
        obj = self.proposal()
        withdraw(request=self.session(0), request_id=obj.pk, note='Withdraw')
        results = self._parallel([self.proposal, self.proposal])
        self.assertEqual(sorted(row[1] for row in results), ['ok', 'rejected'])
        self.assertEqual(PartyVersionRequest.objects.filter(quote=self.quote, is_active=True).count(), 1)
        self.assertEqual(PartyVersionRequest.objects.filter(quote=self.quote).count(), 2)

    def test_replay_vs_formalization_paths(self):
        # Force the historical lock inversion: formalization holds the child
        # while replay begins, then formalization proceeds to lock the parent.
        for action in ('mark-sent', 'accept', 'order-confirm'):
            with self.subTest(action=action):
                # Separate transaction test methods are preferable to resetting
                # immutable history; use a fresh source quote for each iteration.
                source = Quote.objects.create(quote_no='CROSS-'+action, customer=self.customer,
                    quote_date=date(2026, 1, 1), status='sent', buyer_company_name='Buyer')
                self.quote = source
                source_item = self.order.quote.items.first()
                from crm.models import QuoteItem
                QuoteItem.objects.create(quote=source, sku=source_item.sku, quantity=1, unit_price=1)
                obj, _ = self.approved()
                application = apply_approved_quote_change(request=self.session(2), request_id=obj.pk)
                child = application.result_quote
                order = None
                if action == 'order-confirm':
                    order = Order.objects.create(order_no='CROSS-ORDER', customer=self.customer, quote=child,
                        order_date=date(2026, 1, 1), currency=child.currency, exchange_rate=child.exchange_rate,
                        shipping_fee=child.shipping_fee, discount=child.discount, notes=child.notes)
                    line = child.items.get()
                    OrderItem.objects.create(order=order, sku=line.sku, quantity=line.quantity,
                        unit_price=line.unit_price, notes=line.notes, trade_unit=line.trade_unit,
                        trade_quantity=line.trade_quantity, trade_unit_price=line.trade_unit_price,
                        trade_snapshot=line.trade_snapshot)
                held, go, attempted = Event(), Event(), Event()
                pids = {}
                def formalize():
                    close_old_connections()
                    try:
                        with connections['default'].cursor() as cursor:
                            cursor.execute("SET statement_timeout = '15000ms'")
                            cursor.execute("SET lock_timeout = '10000ms'")
                            cursor.execute('SELECT pg_backend_pid()')
                            pids['formal'] = cursor.fetchone()[0]
                        with transaction.atomic():
                            Quote.objects.select_for_update().get(pk=child.pk)
                            held.set()
                            if not go.wait(10):
                                raise RuntimeError('replay did not start')
                            client = APIClient()
                            client.cookies[settings.SESSION_COOKIE_NAME] = self.keys[1]
                            url = f'/api/orders/{order.pk}/confirm/' if order else f'/api/quotes/{child.pk}/{action}/'
                            response = client.post(url, {}, format='json')
                            return response.status_code, response.data
                    finally:
                        connections['default'].close()
                def replay():
                    close_old_connections()
                    try:
                        if not held.wait(10):
                            raise RuntimeError('child was not locked')
                        with connections['default'].cursor() as cursor:
                            cursor.execute("SET statement_timeout = '15000ms'")
                            cursor.execute("SET lock_timeout = '10000ms'")
                            cursor.execute('SELECT pg_backend_pid()')
                            pids['replay'] = cursor.fetchone()[0]
                        attempted.set()
                        return apply_approved_quote_change(request=self.session(2), request_id=obj.pk).pk
                    finally:
                        connections['default'].close()
                with ThreadPoolExecutor(max_workers=2) as pool:
                    left = pool.submit(formalize)
                    right = pool.submit(replay)
                    try:
                        self.assertTrue(attempted.wait(10))
                        deadline = monotonic() + 8
                        blocked = False
                        while monotonic() < deadline:
                            with connection.cursor() as cursor:
                                cursor.execute('SELECT %s = ANY(pg_blocking_pids(%s))', [pids['formal'], pids['replay']])
                                blocked = cursor.fetchone()[0]
                            if blocked:
                                break
                            sleep(0.05)
                        self.assertTrue(blocked, 'replay must actually wait on the formalization connection')
                    finally:
                        go.set()
                    status, body = left.result(timeout=25)
                    self.assertEqual(status, 200, body)
                    self.assertEqual(right.result(timeout=25), application.pk)
