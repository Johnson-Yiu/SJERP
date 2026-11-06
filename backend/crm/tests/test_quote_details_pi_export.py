from copy import deepcopy
from decimal import Decimal
from io import BytesIO

from django.test import TestCase
from openpyxl import load_workbook

from crm.models import Quote
from crm.party_document_details import unknown_details
from crm.party_document_details_models import PartyDocumentDetailsStorage
from crm.quote_template_snapshot import resolve_quote_template
from crm.tests.test_iss020_quote_export import ISS020QuoteExportConsistencyTests
from crm.tests.test_party_quote_application import ApplicationFixture
from crm.party_version import apply_approved_quote_change, approve, baseline, propose


class QuoteDetailsPIExportTests(ISS020QuoteExportConsistencyTests):
    def details_for(self, quote):
        details = unknown_details()
        seller = resolve_quote_template(quote, 'standard_en_no_discount')['seller']
        for field, key in {'name': 'name', 'address': 'address', 'contact': 'saler', 'email': 'email', 'phone': 'phone'}.items():
            details['seller'][field] = seller[key]
        details['buyer'].update(name='Approved buyer', recipient='Approved recipient', contact=None,
                                address='Approved address', tax_id='', email='', phone='123')
        return details

    def test_preview_and_xlsx_use_details_without_master_fallback(self):
        quote = self.make_quote()
        details = self.details_for(quote)
        PartyDocumentDetailsStorage.objects.create(quote=quote, details=details)
        self.customer.name = 'Changed master'
        self.customer.save()
        preview = self.client.get(f'/api/quotes/{quote.pk}/pi-data/')
        self.assertEqual(preview.status_code, 200, preview.data)
        self.assertEqual(preview.data['buyer'], {'company_name': 'Approved buyer', 'name': 'Approved recipient',
            'address': 'Approved address', 'tax_id': '', 'email': '', 'phone': '123'})
        self.assertNotIn('None', preview.data['print_html'])
        response = self.client.get(f'/api/quotes/{quote.pk}/export/')
        self.assertEqual(response.status_code, 200)
        sheet = load_workbook(BytesIO(response.content))['PI']
        self.assertEqual([sheet[f'B{i}'].value for i in range(3, 9)],
                         ['Approved buyer', 'Approved recipient', 'Approved address', None, None, '123'])
        snapshot = resolve_quote_template(quote, 'standard_en_no_discount')
        self.assertEqual(sheet['I3'].value, snapshot['seller']['name'])
        self.assertEqual(sheet['C22'].value or '', snapshot['bank'][0][1])

    def test_seller_unknown_or_conflict_and_formula_are_rejected(self):
        quote = self.make_quote()
        details = self.details_for(quote)
        row = PartyDocumentDetailsStorage.objects.create(quote=quote, details=details)
        for side, field, value in [('seller', 'name', None), ('seller', 'name', 'Other seller'), ('seller', 'tax_id', 'NEW-TAX'),
                                    ('buyer', 'address', '=1+1'), ('buyer', 'name', None), ('buyer', 'name', '')]:
            changed = deepcopy(details)
            changed[side][field] = value
            row.details = changed
            row.save(update_fields=['details'])
            for endpoint in ('pi-data', 'export'):
                response = self.client.get(f'/api/quotes/{quote.pk}/{endpoint}/')
                self.assertEqual(response.status_code, 422, (side, field, value, endpoint))

    def test_no_details_keeps_legacy_snapshot(self):
        quote = self.make_quote()
        preview = self.client.get(f'/api/quotes/{quote.pk}/pi-data/')
        self.assertEqual(preview.data['buyer']['address'], 'ISS-020 Address')
        response = self.client.get(f'/api/quotes/{quote.pk}/export/')
        self.assertEqual(load_workbook(BytesIO(response.content))['PI']['B5'].value, 'ISS-020 Address')

    def test_unknown_and_explicit_blank_never_fall_back(self):
        quote = self.make_quote()
        original = self.details_for(quote)
        row = PartyDocumentDetailsStorage.objects.create(quote=quote, details=original)
        for field, api_key, cell in [('recipient', 'name', 'B4'), ('address', 'address', 'B5'),
                                     ('tax_id', 'tax_id', 'B6'), ('email', 'email', 'B7'), ('phone', 'phone', 'B8')]:
            for value in (None, ''):
                details = deepcopy(original)
                details['buyer'][field] = value
                row.details = details
                row.save(update_fields=['details'])
                preview = self.client.get(f'/api/quotes/{quote.pk}/pi-data/')
                if value is None:
                    self.assertEqual(preview.status_code, 422)
                    self.assertIn(field, preview.data['fields']['buyer'])
                    self.assertEqual(self.client.get(f'/api/quotes/{quote.pk}/export/').status_code, 422)
                    continue
                self.assertEqual(preview.status_code, 200)
                self.assertEqual(preview.data['buyer'][api_key], value)
                response = self.client.get(f'/api/quotes/{quote.pk}/export/')
                self.assertEqual(response.status_code, 200)
                self.assertIsNone(load_workbook(BytesIO(response.content))['PI'][cell].value)

    def test_historical_unknown_tax_is_not_silently_rendered(self):
        quote = self.make_quote()
        Quote.objects.filter(pk=quote.pk).update(buyer_tax_id=None)
        for endpoint in ('pi-data', 'export'):
            response = self.client.get(f'/api/quotes/{quote.pk}/{endpoint}/')
            self.assertEqual(response.status_code, 422)
            self.assertIn('tax_id', response.data['fields']['buyer'])
            self.assertIn('未知', response.data['detail'])
            self.assertNotIn('无效', response.data['detail'])
        quote.refresh_from_db()
        self.assertIsNone(quote.buyer_tax_id)

    def test_null_details_record_does_not_fall_back_to_legacy(self):
        quote = self.make_quote()
        PartyDocumentDetailsStorage.objects.create(quote=quote, details=None)
        for endpoint in ('pi-data', 'export'):
            self.assertEqual(self.client.get(f'/api/quotes/{quote.pk}/{endpoint}/').status_code, 422)

    def test_unmapped_buyer_values_are_reported_for_both_templates(self):
        quote = self.make_quote()
        original = self.details_for(quote)
        row = PartyDocumentDetailsStorage.objects.create(quote=quote, details=original)
        for discount in ('0', '1.00'):
            Quote.objects.filter(pk=quote.pk).update(discount=Decimal(discount))
            for field in ('country', 'contact', 'billing_address', 'shipping_address'):
                details = deepcopy(original)
                details['buyer'][field] = 'Synthetic value'
                row.details = details
                row.save(update_fields=['details'])
                for endpoint in ('pi-data', 'export'):
                    response = self.client.get(f'/api/quotes/{quote.pk}/{endpoint}/')
                    self.assertEqual(response.status_code, 422, (discount, field, endpoint))
                    self.assertIn(field, response.data['fields']['buyer_unmapped'])
                    self.assertNotIn('Synthetic value', str(response.data))
        row.refresh_from_db()
        self.assertEqual(row.details['buyer']['shipping_address'], 'Synthetic value')
        details = deepcopy(original)
        for field in ('country', 'contact', 'billing_address', 'shipping_address'):
            details['buyer'][field] = 'Synthetic value'
        row.details = details
        row.save(update_fields=['details'])
        response = self.client.get(f'/api/quotes/{quote.pk}/pi-data/')
        self.assertEqual(response.status_code, 422)
        for field in ('country', 'contact', 'billing_address', 'shipping_address'):
            self.assertIn(field, response.data['fields']['buyer_unmapped'])

    def test_contact_never_replaces_recipient(self):
        quote = self.make_quote()
        details = self.details_for(quote)
        details['buyer']['recipient'] = ''
        details['buyer']['contact'] = 'Different contact'
        row = PartyDocumentDetailsStorage.objects.create(quote=quote, details=details)
        for endpoint in ('pi-data', 'export'):
            response = self.client.get(f'/api/quotes/{quote.pk}/{endpoint}/')
            self.assertEqual(response.status_code, 422)
            self.assertIn('contact', response.data['fields']['buyer_unmapped'])
        for value in (None, ''):
            details['buyer']['contact'] = value
            row.details = details
            row.save(update_fields=['details'])
            preview = self.client.get(f'/api/quotes/{quote.pk}/pi-data/')
            self.assertEqual(preview.status_code, 200)
            self.assertEqual(preview.data['buyer']['name'], '')
            response = self.client.get(f'/api/quotes/{quote.pk}/export/')
            self.assertEqual(response.status_code, 200)
            self.assertIsNone(load_workbook(BytesIO(response.content))['PI']['B4'].value)


class ApprovedQuoteDetailsPIExportTests(ApplicationFixture, TestCase):
    def setUp(self):
        self.create_fixture()
        item = self.quote.items.get()
        item.trade_snapshot = {**item.trade_snapshot, 'name': 'Pack'}
        item.save(update_fields=['trade_snapshot'])
        Quote.objects.filter(pk=self.quote.pk).update(status='draft')
        self.quote.refresh_from_db()
        details = unknown_details()
        seller = resolve_quote_template(self.quote, 'standard_en_with_discount')['seller']
        for field, key in {'name': 'name', 'address': 'address', 'contact': 'saler', 'email': 'email', 'phone': 'phone'}.items():
            details['seller'][field] = seller[key]
        details['buyer'].update(name='Original approved', recipient='Recipient', address='Before', tax_id='', email='', phone='')
        PartyDocumentDetailsStorage.objects.create(quote=self.quote, details=details)
        Quote.objects.filter(pk=self.quote.pk).update(status='sent')

    def check_approved_revision_and_tampering(self, discount, template_id):
        Quote.objects.filter(pk=self.quote.pk).update(discount=Decimal(discount))
        basis = baseline(request=self.session(0), target_type='quote', target_id=self.quote.pk)
        proposal = deepcopy(basis['snapshot'])
        proposal['party_details']['buyer']['address'] = 'After approval'
        request = propose(request=self.session(0), target_type='quote', target_id=self.quote.pk,
            expected_base_fingerprint=basis['fingerprint'], proposed_snapshot=proposal, change_type='correction',
            reason='Correction', evidence='Evidence', source_trust='unverified')
        approve(request=self.session(1), request_id=request.pk, expected_content_fingerprint=request.content_fingerprint, note='Reviewed')
        application = apply_approved_quote_change(request=self.session(2), request_id=request.pk)
        self.customer.name = 'Changed after approval'
        self.customer.country = 'Changed country'
        self.customer.save()
        client = self.client
        self.assertTrue(client.login(username='apply-maker', password='test-only-password'))
        for quote_id, address in ((self.quote.pk, 'Before'), (application.result_quote_id, 'After approval')):
            preview = client.get(f'/api/quotes/{quote_id}/pi-data/')
            self.assertEqual(preview.status_code, 200, preview.content)
            self.assertEqual(preview.json()['buyer']['address'], address)
            self.assertEqual(preview.json()['buyer']['company_name'], 'Original approved')
            self.assertIn(address, preview.json()['print_html'])
            self.assertNotIn('Changed after approval', preview.json()['print_html'])
            exported = client.get(f'/api/quotes/{quote_id}/export/')
            self.assertEqual(exported.status_code, 200)
            sheet = load_workbook(BytesIO(exported.content))['PI']
            self.assertEqual(sheet['B3'].value, 'Original approved')
            self.assertEqual(sheet['B4'].value, 'Recipient')
            self.assertEqual(sheet['B5'].value, address)
            quote = Quote.objects.get(pk=quote_id)
            snapshot = resolve_quote_template(quote, template_id)
            self.assertEqual(preview.json()['template_sha256'], snapshot['sha256'])
            self.assertEqual(sheet['I3'].value, snapshot['seller']['name'])
            bank_row = snapshot['config']['lower_block']['rows']['bank_header'] + 1
            self.assertEqual(sheet[f'C{bank_row}'].value or '', snapshot['bank'][0][1])
        row = PartyDocumentDetailsStorage.objects.get(quote_id=application.result_quote_id)
        changed = deepcopy(row.details)
        changed['buyer']['address'] = 'Tampered'
        PartyDocumentDetailsStorage.objects.filter(pk=row.pk).update(details=changed)
        for endpoint in ('pi-data', 'export'):
            self.assertEqual(client.get(f'/api/quotes/{application.result_quote_id}/{endpoint}/').status_code, 422)

    def test_approved_revision_with_no_discount_template(self):
        self.check_approved_revision_and_tampering('0', 'standard_en_no_discount')

    def test_approved_revision_with_discount_template(self):
        self.check_approved_revision_and_tampering('0.05', 'standard_en_with_discount')

    def test_approved_contact_is_not_substituted_for_recipient(self):
        Quote.objects.filter(pk=self.quote.pk).update(status='draft')
        row = PartyDocumentDetailsStorage.objects.get(quote=self.quote)
        details = deepcopy(row.details)
        details['buyer']['contact'] = 'Before contact'
        row.details = details
        row.save(update_fields=['details'])
        Quote.objects.filter(pk=self.quote.pk).update(status='sent')
        basis = baseline(request=self.session(0), target_type='quote', target_id=self.quote.pk)
        proposal = deepcopy(basis['snapshot'])
        proposal['party_details']['buyer']['contact'] = 'Approved contact'
        request = propose(request=self.session(0), target_type='quote', target_id=self.quote.pk,
            expected_base_fingerprint=basis['fingerprint'], proposed_snapshot=proposal, change_type='correction',
            reason='Correction', evidence='Evidence', source_trust='unverified')
        approve(request=self.session(1), request_id=request.pk, expected_content_fingerprint=request.content_fingerprint, note='Reviewed')
        application = apply_approved_quote_change(request=self.session(2), request_id=request.pk)
        self.assertEqual(PartyDocumentDetailsStorage.objects.get(quote_id=application.result_quote_id).details['buyer']['recipient'], 'Recipient')
        self.assertTrue(self.client.login(username='apply-maker', password='test-only-password'))
        for endpoint in ('pi-data', 'export'):
            response = self.client.get(f'/api/quotes/{application.result_quote_id}/{endpoint}/')
            self.assertEqual(response.status_code, 422)
            self.assertIn('contact', response.json()['fields']['buyer_unmapped'])
