"""Compatibility and fail-closed tests for isolated fingerprint primitives."""

from copy import deepcopy

from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings

from crm.models import Quote
from crm.party_version import _quote_fingerprint, apply_approved_quote_change, verified_approval
from crm.quote_party_fingerprint import quote_party_fingerprint, validate_party_details, verify_quote_party_fingerprint
from crm.tests.test_party_quote_application import ApplicationFixture
from crm.tests import test_quote_buyer_tax_id as tax_fixtures


def blank_address():
    return {"address": None, "recipient": None, "phone": None, "email": None}


def unknown_details():
    return {
        "buyer": {"registration_id": None, "registered_address": None, "billing": blank_address(), "shipping": blank_address()},
        "seller": {"country": None, "tax_id": None, "registration_id": None, "registered_address": None, "billing": blank_address(), "shipping": blank_address()},
    }


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class QuotePartyFingerprintVersionTests(ApplicationFixture, TestCase):
    def setUp(self):
        # Reuse the existing isolated synthetic seller/bank template factory.
        tax_fixtures.QuoteBuyerTaxTests.setUp(self)
        self.create_fixture()

    def test_legacy_approval_and_application_remain_valid_without_details(self):
        request, approval = self.approved()
        self.quote.refresh_from_db()
        items = list(self.quote.items.order_by("id"))
        old_digest = _quote_fingerprint(self.quote, items)
        descriptor = quote_party_fingerprint(self.quote, items, version=1)
        self.assertEqual(descriptor, {"version": 1, "sha256": old_digest})
        self.assertEqual(request.source_document_fingerprint, old_digest)
        self.assertTrue(verify_quote_party_fingerprint(self.quote, items, descriptor))
        self.assertEqual(verified_approval(request=self.session(1), request_id=request.pk).pk, approval.pk)
        application = apply_approved_quote_change(request=self.session(2), request_id=request.pk)
        self.assertEqual(application.source_fingerprint, old_digest)
        revision = Quote.objects.get(pk=application.result_quote_id)
        self.assertTrue(verify_quote_party_fingerprint(revision, list(revision.items.order_by("id")),
            {"version": 1, "sha256": application.revision_fingerprint}))
        self.assertEqual(apply_approved_quote_change(request=self.session(1), request_id=request.pk).pk, application.pk)

    def test_v2_binds_each_party_role_and_preserves_null(self):
        items = list(self.quote.items.order_by("id"))
        details = unknown_details()
        descriptor = quote_party_fingerprint(self.quote, items, version=2, details=details)
        self.assertTrue(verify_quote_party_fingerprint(self.quote, items, descriptor, details=details))
        for role, path in (("buyer", ("registration_id",)), ("buyer", ("registered_address",)),
                           ("buyer", ("billing", "recipient")), ("buyer", ("shipping", "address")),
                           ("seller", ("country",)), ("seller", ("tax_id",)),
                           ("seller", ("registered_address",)), ("seller", ("billing", "email")),
                           ("seller", ("shipping", "phone"))):
            with self.subTest(role=role, path=path):
                modified = deepcopy(details)
                node = modified[role]
                for part in path[:-1]:
                    node = node[part]
                node[path[-1]] = ""  # Explicit blank must not equal unknown.
                with self.assertRaises(ValidationError):
                    verify_quote_party_fingerprint(self.quote, items, descriptor, details=modified)
        self.assertIsNone(details["buyer"]["billing"]["recipient"])

    def test_no_downgrade_missing_fields_or_unrecognized_versions(self):
        items = list(self.quote.items.order_by("id"))
        details = unknown_details()
        legacy = quote_party_fingerprint(self.quote, items, version=1)
        with self.assertRaises(ValidationError):
            verify_quote_party_fingerprint(self.quote, items, legacy, details=details)
        v2 = quote_party_fingerprint(self.quote, items, version=2, details=details)
        with self.assertRaises(ValidationError):
            verify_quote_party_fingerprint(self.quote, items, v2)
        for invalid in ({"version": 3, "sha256": v2["sha256"]},
                        {"version": True, "sha256": v2["sha256"]},
                        {"version": 2, "sha256": "wrong"},
                        {"version": 2, "sha256": v2["sha256"], "extra": 1}):
            with self.subTest(descriptor=invalid), self.assertRaises(ValidationError):
                verify_quote_party_fingerprint(self.quote, items, invalid, details=details)
        missing = unknown_details()
        del missing["buyer"]["shipping"]["address"]
        with self.assertRaises(ValidationError):
            validate_party_details(missing)
        extra = unknown_details()
        extra["seller"]["unapproved"] = "hidden"
        with self.assertRaises(ValidationError):
            validate_party_details(extra)

    def test_v2_binds_the_original_quote_facts(self):
        items = list(self.quote.items.order_by("id"))
        details = unknown_details()
        descriptor = quote_party_fingerprint(self.quote, items, version=2, details=details)
        self.quote.notes = "Changed after fingerprint"
        with self.assertRaises(ValidationError):
            verify_quote_party_fingerprint(self.quote, items, descriptor, details=details)

    def test_v2_application_and_consumer_verify_approval(self):
        from crm.party_document_details import unknown_details as document_details, read_document_details
        from crm.party_document_details_models import PartyDocumentDetailsStorage
        from crm.party_version import baseline, propose, approve, verify_quote_details_application
        from django.db import connection, transaction
        Quote.objects.filter(pk=self.quote.pk).update(status='draft')
        details = document_details(); details['buyer']['address'] = 'Before'
        PartyDocumentDetailsStorage.objects.create(quote=self.quote, details=details)
        Quote.objects.filter(pk=self.quote.pk).update(status='sent')
        basis = baseline(request=self.session(0), target_type='quote', target_id=self.quote.pk)
        proposal = deepcopy(basis['snapshot']); proposal['party_details']['buyer']['address'] = 'After'
        req = propose(request=self.session(0), target_type='quote', target_id=self.quote.pk,
            expected_base_fingerprint=basis['fingerprint'], proposed_snapshot=proposal,
            change_type='correction', reason='Synthetic', evidence='Synthetic', source_trust='unverified')
        approve(request=self.session(1), request_id=req.pk, expected_content_fingerprint=req.content_fingerprint, note='Reviewed')
        application = apply_approved_quote_change(request=self.session(2), request_id=req.pk)
        revision = Quote.objects.get(pk=application.result_quote_id)
        self.quote.refresh_from_db()
        with transaction.atomic():
            self.assertEqual(verify_quote_details_application(self.quote, revision), proposal['party_details'])
        Quote.objects.filter(pk=revision.pk).update(status='sent')
        self.assertEqual(read_document_details(request=self.session(1), target_type='quote', target_id=revision.pk), proposal['party_details'])
        from crm.party_document_details import inherit_quote_details
        from crm.party_version import TARGETS
        fields = TARGETS['quote'][1]
        values = {field: getattr(revision, field) for field in fields.values()}
        with transaction.atomic():
            child = Quote.objects.create(quote_no='APPLY-CHILD', customer=revision.customer,
                quote_date=revision.quote_date, parent_quote=revision, status='draft', **values)
            inherit_quote_details(revision, child)
        self.assertEqual(read_document_details(request=self.session(1), target_type='quote', target_id=child.pk), proposal['party_details'])
        from django.conf import settings
        from django.test import Client
        client = Client()
        client.cookies[settings.SESSION_COOKIE_NAME] = self.keys[0]
        response = client.post(f'/api/quotes/{revision.pk}/revise/',
                               data={'revision_summary': 'Ordinary revision'}, content_type='application/json')
        self.assertEqual(response.status_code, 201, response.content)
        api_child = Quote.objects.get(pk=response.json()['id'])
        self.assertEqual(read_document_details(request=self.session(1), target_type='quote', target_id=api_child.pk), proposal['party_details'])
        with connection.cursor() as cursor:
            cursor.execute('UPDATE crm_partyversionapproval SET note=%s WHERE request_id=%s', ['altered', req.pk])
        with self.assertRaises(ValidationError):
            read_document_details(request=self.session(1), target_type='quote', target_id=revision.pk)
        with self.assertRaises(ValidationError):
            read_document_details(request=self.session(1), target_type='quote', target_id=child.pk)
