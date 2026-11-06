from copy import deepcopy
from datetime import date

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.contrib.auth import get_user_model
from django.test import Client, RequestFactory, SimpleTestCase, TestCase, override_settings

from crm.party_document_details import (unknown_details, validate_details, validate_initial_details,
    document_party_fingerprint, verify_document_party_fingerprint, read_document_details, save_draft_details)
from crm.party_version import _digest
from crm.party_document_details_models import PartyDocumentDetailsStorage
from crm.models import Customer, Quote, Order


class PartyDocumentDetailsValidationTests(SimpleTestCase):
    def test_legacy_fingerprint_preserves_original_snapshot_hash(self):
        for snapshot in ({'name': '旧名称', 'address': ''}, {'name': 'Buyer', 'country': None}):
            descriptor = document_party_fingerprint(snapshot, version=1)
            self.assertEqual(descriptor, {'version': 1, 'sha256': _digest(snapshot)})
            self.assertTrue(verify_document_party_fingerprint(snapshot, descriptor))
            with self.assertRaises(ValidationError):
                verify_document_party_fingerprint(snapshot, descriptor, details=unknown_details())

    def test_v2_binds_both_parties_snapshot_and_document_identity(self):
        snapshot = {'name': 'Buyer', 'address': 'Original'}
        details = unknown_details()
        kw = {'target_type': 'order', 'target_id': 7, 'details': details}
        descriptor = document_party_fingerprint(snapshot, version=2, **kw)
        self.assertTrue(verify_document_party_fingerprint(snapshot, descriptor, **kw))
        for side in ('buyer', 'seller'):
            changed = deepcopy(details)
            changed[side]['tax_id'] = ''
            with self.subTest(side=side), self.assertRaises(ValidationError):
                verify_document_party_fingerprint(snapshot, descriptor, **{**kw, 'details': changed})
        for changed in ({**kw, 'target_id': 8}, {**kw, 'target_type': 'purchase_order'}):
            with self.assertRaises(ValidationError):
                verify_document_party_fingerprint(snapshot, descriptor, **changed)
        with self.assertRaises(ValidationError):
            verify_document_party_fingerprint({**snapshot, 'address': 'Changed'}, descriptor, **kw)

    def test_fingerprint_rejects_unsupported_versions_and_malformed_descriptors(self):
        snapshot = {'name': 'Buyer'}
        for descriptor in ({'version': True, 'sha256': '0' * 64},
                           {'version': 3, 'sha256': '0' * 64},
                           {'version': 1, 'sha256': 'invalid'},
                           {'version': 1, 'sha256': '0' * 64, 'extra': 1}):
            with self.subTest(descriptor=descriptor), self.assertRaises(ValidationError):
                verify_document_party_fingerprint(snapshot, descriptor)
    def test_historical_unknown_and_explicit_empty_are_distinct(self):
        details = unknown_details()
        self.assertIsNone(details['buyer']['tax_id'])
        details['buyer']['tax_id'] = ''
        result = validate_initial_details(persisted_status='draft', details=details)
        self.assertEqual(result['buyer']['tax_id'], '')
        self.assertIsNone(result['seller']['tax_id'])
        self.assertEqual(unknown_details()['buyer']['tax_id'], None)

    def test_formal_document_cannot_enter_initial_details(self):
        for status in ('confirmed', 'ordered', 'historical', 'cancelled', None):
            with self.subTest(status=status), self.assertRaises(ValidationError):
                validate_initial_details(persisted_status=status, details=unknown_details())

    def test_reject_unknown_schema_missing_and_invalid_fields(self):
        for mutation in ('schema', 'missing', 'extra', 'type', 'length'):
            value = deepcopy(unknown_details())
            if mutation == 'schema': value['schema'] = 'future'
            if mutation == 'missing': del value['buyer']['country']
            if mutation == 'extra': value['seller']['other'] = 'x'
            if mutation == 'type': value['buyer']['tax_id'] = 1
            if mutation == 'length': value['seller']['name'] = 'x' * 201
            with self.subTest(mutation=mutation), self.assertRaises(ValidationError):
                validate_details(value)


class DormantPartyDetailsStorageTests(TestCase):
    @override_settings(APP_STAGE='development', DEBUG=True, DEVELOPMENT_SUPERADMIN=True, RBAC_ENFORCEMENT=False)
    def test_development_identity_can_edit_draft_without_fake_login(self):
        customer = Customer.objects.create(code='DETAILS-DEV', name='Synthetic')
        quote = Quote.objects.create(quote_no='DETAILS-DEV', customer=customer, quote_date=date(2026, 1, 1))
        request = RequestFactory().put('/')
        details = unknown_details()
        self.assertEqual(save_draft_details(request=request, target_type='quote', target_id=quote.pk, details=details), details)

    def test_authenticated_read_returns_unknown_not_master_data(self):
        customer = Customer.objects.create(code='DETAILS-READ', name='Master name')
        quote = Quote.objects.create(quote_no='DETAILS-READ', customer=customer, quote_date=date(2026, 1, 1))
        user = get_user_model().objects.create_superuser(username='details-reader', password='test-only')
        client = Client()
        client.force_login(user)
        request = RequestFactory().get('/')
        request.session = client.session
        self.assertIsNone(read_document_details(request=request, target_type='quote', target_id=quote.pk))
        PartyDocumentDetailsStorage.objects.create(quote=quote)
        self.assertIsNone(read_document_details(request=request, target_type='quote', target_id=quote.pk))
        response = client.get(f'/api/quotes/{quote.pk}/party-details/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'details': None, 'original_details': None})

    def test_draft_write_then_formal_database_guard_rejects_update(self):
        customer = Customer.objects.create(code='DETAILS-C', name='Synthetic')
        quote = Quote.objects.create(quote_no='DETAILS-Q', customer=customer, quote_date=date(2026, 1, 1))
        details = unknown_details()
        row = PartyDocumentDetailsStorage.objects.create(quote=quote, details=details)
        Quote.objects.filter(pk=quote.pk).update(status='sent')
        with self.assertRaises(IntegrityError), transaction.atomic():
            PartyDocumentDetailsStorage.objects.filter(pk=row.pk).update(details={})
        row.refresh_from_db()
        self.assertEqual(row.details, details)

    def test_authenticated_draft_service_rejects_formal_and_preserves_original(self):
        customer = Customer.objects.create(code='DETAILS-WRITE', name='Master')
        quote = Quote.objects.create(quote_no='DETAILS-WRITE', customer=customer, quote_date=date(2026, 1, 1))
        user = get_user_model().objects.create_superuser(username='details-writer', password='test-only')
        client = Client(); client.force_login(user)
        request = RequestFactory().put('/'); request.session = client.session
        facts = unknown_details(); facts['buyer']['name'] = 'Explicit'
        self.assertEqual(save_draft_details(request=request, target_type='quote', target_id=quote.pk, details=facts), facts)
        self.assertEqual(read_document_details(request=request, target_type='quote', target_id=quote.pk), facts)
        Quote.objects.filter(pk=quote.pk).update(status='sent')
        with self.assertRaises(ValidationError):
            save_draft_details(request=request, target_type='quote', target_id=quote.pk, details=unknown_details())
        self.assertEqual(PartyDocumentDetailsStorage.objects.get(quote=quote).details, facts)

    def test_storage_requires_exactly_one_target(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            PartyDocumentDetailsStorage.objects.create()

    def test_historical_flag_blocks_even_draft_status(self):
        customer = Customer.objects.create(code='DETAILS-HIST', name='Synthetic')
        order = Order.objects.create(order_no='DETAILS-HIST', customer=customer,
                                     order_date=date(2026, 1, 1), status='draft', historical_only=True)
        with self.assertRaises(IntegrityError), transaction.atomic():
            PartyDocumentDetailsStorage.objects.create(order=order, details=unknown_details())
