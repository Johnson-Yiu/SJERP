from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from crm.models import Customer, Quote


class PartyLifecycleApiCloseoutTests(TestCase):
    def setUp(self):
        users = get_user_model()
        users.objects.create_user(username='lifecycle-a', password='synthetic-a')
        users.objects.create_user(username='lifecycle-b', password='synthetic-b')
        self.a, self.b = APIClient(), APIClient()
        self.assertTrue(self.a.login(username='lifecycle-a', password='synthetic-a'))
        self.assertTrue(self.b.login(username='lifecycle-b', password='synthetic-b'))
        customer = Customer.objects.create(code='LIFE-C', name='Synthetic buyer', country='Germany')
        quote = Quote.objects.create(quote_no='LIFE-Q', customer=customer, quote_date=date(2026, 11, 5), status='sent')
        self.url = f'/api/quotes/{quote.pk}/party-change/'

    def propose(self):
        base = self.a.get(self.url)
        self.assertEqual(base.status_code, 200)
        snapshot = dict(base.data['baseline']['snapshot'], address='New address')
        result = self.a.post(self.url, {'expected_base_fingerprint': base.data['baseline']['fingerprint'],
            'proposed_snapshot': snapshot, 'change_type': 'correction', 'reason': 'Synthetic reason',
            'evidence': 'Synthetic evidence', 'source_trust': 'unverified'}, format='json')
        self.assertEqual(result.status_code, 201, result.data)
        return result.data

    def test_reject_then_reapply_retains_history_and_identity(self):
        first = self.propose()
        url = f'{self.url}{first["id"]}/reject/'
        self.assertEqual(self.a.post(url, {'note': 'self rejection'}, format='json').status_code, 400)
        denied = self.b.post(url, {'note': 'Independent rejection'}, format='json')
        self.assertEqual(denied.status_code, 200, denied.data)
        self.assertEqual(self.b.post(url, {'note': 'Duplicate'}, format='json').status_code, 400)
        second = self.propose()
        self.assertNotEqual(first['id'], second['id'])
        listed = self.a.get(self.url)
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.data['requests']), 2)

    def test_withdraw_only_initiator_and_anonymous_is_rejected(self):
        first = self.propose()
        url = f'{self.url}{first["id"]}/withdraw/'
        self.assertEqual(APIClient().post(url, {'note': 'unauthorized'}, format='json').status_code, 401)
        self.assertIn(self.b.post(url, {'note': 'wrong actor'}, format='json').status_code, (400, 403))
        removed = self.a.post(url, {'note': 'Withdraw request'}, format='json')
        self.assertEqual(removed.status_code, 200, removed.data)
        self.assertNotEqual(first['id'], self.propose()['id'])

    def test_approved_invalidation_prevents_apply_and_allows_fresh_request(self):
        first = self.propose()
        approve = self.b.post(f'{self.url}{first["id"]}/approve/',
            {'expected_content_fingerprint': first['content_fingerprint'], 'note': 'Reviewed'}, format='json')
        self.assertEqual(approve.status_code, 200, approve.data)
        invalid = self.b.post(f'{self.url}{first["id"]}/invalidate/', {'note': 'Evidence superseded'}, format='json')
        self.assertEqual(invalid.status_code, 200, invalid.data)
        apply = self.a.post(f'{self.url}{first["id"]}/apply/', {}, format='json')
        self.assertEqual(apply.status_code, 400)
        self.assertNotEqual(first['id'], self.propose()['id'])
