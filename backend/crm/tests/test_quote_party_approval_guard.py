from datetime import date
from django.core.exceptions import ValidationError
from django.test import TestCase
from crm.models import Quote
from crm.tests.test_party_quote_application import ApplicationFixture
from crm.party_version import apply_approved_quote_change

class QuotePartyApprovalGuardTests(ApplicationFixture, TestCase):
    def setUp(self):
        self.create_fixture()

    def revision(self, parent, number, **changes):
        values = dict(customer=parent.customer, buyer_company_name=parent.buyer_company_name,
            buyer_country_snapshot=parent.buyer_country_snapshot, buyer_tax_id=parent.buyer_tax_id,
            recipient_name=parent.recipient_name, buyer_address=parent.buyer_address,
            buyer_email=parent.buyer_email, buyer_phone=parent.buyer_phone)
        values.update(changes)
        return Quote.objects.create(quote_no=f'GUARD-{number}', quote_date=date(2026, 1, 1),
            parent_quote=parent, root_quote=self.quote, revision_no=number, **values)

    def test_draft_chain_cannot_hide_party_change(self):
        first = self.revision(self.quote, 1, buyer_address='changed')
        second = self.revision(first, 2)
        second.status = 'sent'
        with self.assertRaises(ValidationError):
            second.save(update_fields=['status'])
        second.refresh_from_db()
        self.assertEqual(second.status, 'draft')
        with self.assertRaises(ValidationError):
            self.revision(first, 3, status='accepted')

    def test_unchanged_party_revision_can_be_sent(self):
        draft = self.revision(self.quote, 1)
        draft.status = 'sent'
        draft.save(update_fields=['status'])
        self.assertEqual(Quote.objects.get(pk=draft.pk).status, 'sent')

    def test_valid_application_and_unchanged_descendant_are_allowed(self):
        request, _ = self.approved()
        application = apply_approved_quote_change(request=self.session(2), request_id=request.pk)
        revision = application.result_quote
        revision.status = 'sent'
        revision.save(update_fields=['status'])
        descendant = self.revision(revision, 9)
        descendant.status = 'sent'
        descendant.save(update_fields=['status'])
        self.assertEqual(Quote.objects.get(pk=descendant.pk).status, 'sent')

    def test_changed_approved_result_is_rejected(self):
        request, _ = self.approved()
        application = apply_approved_quote_change(request=self.session(2), request_id=request.pk)
        revision = application.result_quote
        revision.buyer_address = 'not approved'
        revision.status = 'sent'
        with self.assertRaises(ValidationError):
            revision.save()

    def test_unrelated_quote_with_wrong_application_is_not_enough(self):
        request, _ = self.approved()
        application = apply_approved_quote_change(request=self.session(2), request_id=request.pk)
        other = self.revision(self.quote, 8, buyer_company_name=application.result_quote.buyer_company_name)
        other.status = 'sent'
        with self.assertRaises(ValidationError):
            other.save(update_fields=['status'])

    def test_order_confirmation_refuses_changed_draft_before_side_effects(self):
        from unittest.mock import patch
        from crm.models import Order
        from crm.services.order_lifecycle import confirm_order
        changed = self.revision(self.quote, 1, buyer_address='changed')
        order = Order.objects.create(order_no='GUARD-ORDER', customer=self.customer,
                                     quote=changed, order_date=date(2026, 1, 1))
        with patch('crm.services.order_lifecycle._validate_order_for_confirmation', return_value=[object()]):
            with self.assertRaises(ValidationError):
                confirm_order(order)
        order.refresh_from_db(); changed.refresh_from_db()
        self.assertEqual(order.status, 'draft')
        self.assertEqual(changed.status, 'draft')

    def test_modified_approval_record_is_rejected(self):
        from django.db import connection
        request, approval = self.approved()
        application = apply_approved_quote_change(request=self.session(2), request_id=request.pk)
        with connection.cursor() as cursor:
            cursor.execute('UPDATE crm_partyversionapproval SET note = %s WHERE id = %s', ['tampered', approval.pk])
        revision = application.result_quote
        revision.status = 'sent'
        with self.assertRaises(ValidationError):
            revision.save(update_fields=['status'])

    def test_approved_result_rejects_changed_revision_or_source_document(self):
        from crm.models import QuoteItem
        request, _ = self.approved()
        application = apply_approved_quote_change(request=self.session(2), request_id=request.pk)
        revision = application.result_quote
        QuoteItem.objects.filter(quote=revision).update(notes='changed after approval')
        revision.status = 'sent'
        with self.assertRaises(ValidationError):
            revision.save(update_fields=['status'])
        QuoteItem.objects.filter(quote=revision).update(notes='history')
        Quote.objects.filter(pk=self.quote.pk).update(notes='changed source')
        with self.assertRaises(ValidationError):
            revision.save(update_fields=['status'])

    def test_legacy_formal_revision_can_save_or_be_accepted_without_application(self):
        from unittest.mock import patch
        from crm.models import Order
        from crm.services.order_lifecycle import confirm_order
        legacy = self.revision(self.quote, 1, buyer_address='legacy changed')
        Quote.objects.filter(pk=legacy.pk).update(status='sent')
        legacy.refresh_from_db()
        legacy.status = 'accepted'
        legacy.save(update_fields=['status'])
        order = Order.objects.create(order_no='GUARD-LEGACY', customer=self.customer,
                                     quote=legacy, order_date=date(2026, 1, 1))
        line = order.items.create(sku=self.quote.items.first().sku, quantity=1, unit_price=10)
        with patch('crm.services.order_lifecycle._validate_order_for_confirmation', return_value=[line]), \
             patch('crm.services.order_lifecycle._order_item_payload', return_value=[]), \
             patch('crm.serializers.OrderSerializer._create_quote_revision_if_needed', return_value=legacy), \
             patch('crm.services.order_lifecycle.allocate_order'), \
             patch('crm.services.order_lifecycle.ensure_default_payment_plans'):
            confirm_order(order)
        order.refresh_from_db()
        self.assertEqual(order.status, 'confirmed')

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from threading import Event
from unittest import skipUnless
from django.db import close_old_connections, connection, connections, transaction
from django.test import TransactionTestCase

@skipUnless(connection.vendor == 'postgresql', 'requires PostgreSQL row locks')
class QuotePartyApprovalConcurrencyTests(ApplicationFixture, TransactionTestCase):
    def test_result_item_change_is_serialized_before_formalization(self):
        from crm.models import QuoteItem
        self.create_fixture()
        request, _ = self.approved()
        application = apply_approved_quote_change(request=self.session(2), request_id=request.pk)
        quote_id = application.result_quote_id
        item_id = QuoteItem.objects.get(quote_id=quote_id).pk
        held, release, attempted = Event(), Event(), Event()
        def edit_item():
            close_old_connections()
            try:
                with transaction.atomic():
                    item = QuoteItem.objects.select_for_update().get(pk=item_id)
                    item.notes = 'concurrent change'
                    item.save(update_fields=['notes'])
                    held.set()
                    if not release.wait(10):
                        raise RuntimeError('test did not release item lock')
            finally:
                connections['default'].close()
        def formalize():
            close_old_connections()
            try:
                if not held.wait(10):
                    raise RuntimeError('test did not acquire item lock')
                quote = Quote.objects.get(pk=quote_id)
                quote.status = 'sent'
                attempted.set()
                try:
                    quote.save(update_fields=['status'])
                except ValidationError:
                    return 'rejected'
                return 'unexpectedly accepted'
            finally:
                connections['default'].close()
        with ThreadPoolExecutor(max_workers=2) as pool:
            writer = pool.submit(edit_item)
            sender = pool.submit(formalize)
            self.assertTrue(attempted.wait(10))
            try:
                with self.assertRaises(FutureTimeout):
                    sender.result(timeout=0.3)
            finally:
                release.set()
            writer.result(timeout=15)
            self.assertEqual(sender.result(timeout=15), 'rejected')
        self.assertEqual(Quote.objects.get(pk=quote_id).status, 'draft')

class QuotePartyApprovalApiTests(ApplicationFixture, TestCase):
    def setUp(self):
        self.create_fixture()

    def test_anonymous_development_cannot_send_unapproved_revision(self):
        from rest_framework.test import APIClient
        revision = Quote.objects.create(quote_no='GUARD-API', quote_date=date(2026, 1, 1),
            parent_quote=self.quote, root_quote=self.quote, revision_no=1,
            customer=self.customer, buyer_company_name=self.quote.buyer_company_name,
            buyer_country_snapshot=self.quote.buyer_country_snapshot, buyer_tax_id=self.quote.buyer_tax_id,
            recipient_name=self.quote.recipient_name, buyer_address='unapproved',
            buyer_email=self.quote.buyer_email, buyer_phone=self.quote.buyer_phone)
        client = APIClient()
        client.raise_request_exception = False
        response = client.post(f'/api/quotes/{revision.pk}/mark-sent/', {}, format='json')
        revision.refresh_from_db()
        self.assertEqual(revision.status, 'draft')
        self.assertEqual(response.status_code, 400)
