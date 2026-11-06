from copy import deepcopy
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from crm.models import Order, Quote
from crm.party_document_details import unknown_details
from crm.party_document_details_models import PartyDocumentDetailsStorage
from crm.party_version import apply_approved_quote_change, approve, baseline, propose
from crm.tests.test_party_quote_application import ApplicationFixture


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class QuoteDetailsFormalGuardTests(ApplicationFixture, TestCase):
    def setUp(self):
        self.create_fixture()

    def approved_revision(self):
        Quote.objects.filter(pk=self.quote.pk).update(status='draft')
        details = unknown_details()
        details['buyer']['address'] = 'Synthetic before'
        PartyDocumentDetailsStorage.objects.create(quote=self.quote, details=details)
        Quote.objects.filter(pk=self.quote.pk).update(status='sent')
        basis = baseline(request=self.session(0), target_type='quote', target_id=self.quote.pk)
        proposed = deepcopy(basis['snapshot'])
        proposed['party_details']['buyer']['address'] = 'Synthetic after'
        obj = propose(request=self.session(0), target_type='quote', target_id=self.quote.pk,
            expected_base_fingerprint=basis['fingerprint'], proposed_snapshot=proposed, change_type='correction',
            reason='Synthetic', evidence='Synthetic', source_trust='unverified')
        approve(request=self.session(1), request_id=obj.pk, expected_content_fingerprint=obj.content_fingerprint, note='Synthetic review')
        application = apply_approved_quote_change(request=self.session(2), request_id=obj.pk)
        return Quote.objects.get(pk=application.result_quote_id)

    def test_approved_v2_details_can_be_formalized(self):
        revision = self.approved_revision()
        revision.status = 'sent'
        revision.save(update_fields=['status'])
        self.assertEqual(Quote.objects.get(pk=revision.pk).status, 'sent')

    def test_tampered_v2_details_cannot_be_formalized(self):
        revision = self.approved_revision()
        row = PartyDocumentDetailsStorage.objects.get(quote=revision)
        details = deepcopy(row.details)
        details['buyer']['address'] = 'Synthetic tampering'
        PartyDocumentDetailsStorage.objects.filter(pk=row.pk).update(details=details)
        revision.status = 'sent'
        with self.assertRaises(ValidationError):
            revision.save(update_fields=['status'])
        self.assertEqual(Quote.objects.get(pk=revision.pk).status, 'draft')

    def test_ordinary_revision_inherits_and_formalizes_approved_details(self):
        revision = self.approved_revision()
        revision.status = 'sent'
        revision.save(update_fields=['status'])
        client = APIClient()
        self.assertTrue(client.login(username='apply-maker', password='test-only-password'))
        result = client.post(f'/api/quotes/{revision.pk}/revise/', {'revision_summary': 'Synthetic terms', 'notes': 'New synthetic terms'}, format='json')
        self.assertEqual(result.status_code, 201, result.data)
        child = Quote.objects.get(pk=result.data['id'])
        self.assertEqual(PartyDocumentDetailsStorage.objects.get(quote=child).details,
                         PartyDocumentDetailsStorage.objects.get(quote=revision).details)
        sent = client.post(f'/api/quotes/{child.pk}/mark-sent/', {}, format='json')
        self.assertEqual(sent.status_code, 200, sent.data)
        details = client.get(f'/api/quotes/{child.pk}/party-details/')
        self.assertEqual(details.status_code, 200, details.data)
        self.assertEqual(details.data['details']['buyer']['address'], 'Synthetic after')

    def test_order_triggered_revision_inherits_approved_details(self):
        from crm.services.order_lifecycle import confirm_order
        revision = self.approved_revision()
        revision.status = 'sent'
        revision.save(update_fields=['status'])
        order = Order.objects.create(order_no='SYN-DETAILS-SO', customer=self.customer, quote=revision,
                                     order_date='2026-11-05', currency='USD', exchange_rate='7.2')
        order.items.create(sku=self.quote.items.first().sku, quantity='3', unit_price='2')
        confirmed = confirm_order(order)
        self.assertNotEqual(confirmed.quote_id, revision.pk)
        self.assertEqual(confirmed.quote.status, 'accepted')
        self.assertEqual(PartyDocumentDetailsStorage.objects.get(quote=confirmed.quote).details,
                         PartyDocumentDetailsStorage.objects.get(quote=revision).details)
        client = APIClient()
        self.assertTrue(client.login(username='apply-maker', password='test-only-password'))
        details = client.get(f'/api/quotes/{confirmed.quote_id}/party-details/')
        self.assertEqual(details.status_code, 200, details.data)
        self.assertEqual(details.data['details']['buyer']['address'], 'Synthetic after')
