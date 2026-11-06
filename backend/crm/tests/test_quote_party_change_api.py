from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from crm.models import Customer, Product, Quote, SKU


class QuotePartyChangeApiTests(TestCase):
    def setUp(self):
        users = get_user_model()
        users.objects.create_user(username='party-api-a', password='synthetic-a')
        users.objects.create_user(username='party-api-b', password='synthetic-b')
        self.a, self.b = APIClient(), APIClient()
        self.assertTrue(self.a.login(username='party-api-a', password='synthetic-a'))
        self.assertTrue(self.b.login(username='party-api-b', password='synthetic-b'))
        customer = Customer.objects.create(code='PARTY-API-C', name='Synthetic buyer', country='Germany')
        product = Product.objects.create(code='PARTY-API-P', name='Synthetic product')
        sku = SKU.objects.create(product=product, sku='PARTY-API-SKU')
        self.quote = Quote.objects.create(quote_no='PARTY-API-Q', customer=customer,
                                          quote_date=date(2026, 11, 5), status='sent', buyer_address='Original')
        self.quote.items.create(sku=sku, quantity='1', unit_price='1.005')
        self.url = f'/api/quotes/{self.quote.pk}/party-change/'

    def test_authenticated_separate_approval_and_idempotent_quote_revision(self):
        self.assertEqual(APIClient().get(self.url).status_code, 401)
        initial = self.a.get(self.url)
        self.assertEqual(initial.status_code, 200, initial.data)
        proposed = dict(initial.data['baseline']['snapshot'], address='Corrected address')
        created = self.a.post(self.url, {'expected_base_fingerprint': initial.data['baseline']['fingerprint'],
            'proposed_snapshot': proposed, 'change_type': 'correction', 'reason': 'Correct address',
            'evidence': 'Synthetic supporting reference', 'source_trust': 'unverified'}, format='json')
        self.assertEqual(created.status_code, 201, created.data)
        request_id, fingerprint = created.data['id'], created.data['content_fingerprint']
        approve_url = f'{self.url}{request_id}/approve/'
        apply_url = f'{self.url}{request_id}/apply/'
        denied = self.a.post(approve_url, {'expected_content_fingerprint': fingerprint, 'note': 'Self'}, format='json')
        self.assertEqual(denied.status_code, 400, denied.data)
        approved = self.b.post(approve_url, {'expected_content_fingerprint': fingerprint, 'note': 'Reviewed'}, format='json')
        self.assertEqual(approved.status_code, 200, approved.data)
        applied = self.a.post(apply_url, {}, format='json')
        self.assertEqual(applied.status_code, 200, applied.data)
        repeated = self.a.post(apply_url, {}, format='json')
        self.assertEqual(repeated.status_code, 200, repeated.data)
        self.assertEqual(applied.data['result_quote_id'], repeated.data['result_quote_id'])
        self.quote.refresh_from_db()
        child = Quote.objects.get(pk=applied.data['result_quote_id'])
        self.assertEqual((self.quote.buyer_address, child.buyer_address, child.parent_quote_id, child.status),
                         ('Original', 'Corrected address', self.quote.pk, 'draft'))
        self.assertEqual(child.amount_calculation_version, self.quote.amount_calculation_version)
        self.assertEqual(child.total_amount, self.quote.total_amount)

    @override_settings(APP_STAGE='production', DEBUG=False, DEVELOPMENT_SUPERADMIN=False, RBAC_ENFORCEMENT=True)
    def test_authenticated_unprivileged_user_cannot_read_party_change(self):
        response = self.a.get(self.url)
        self.assertEqual(response.status_code, 403)
