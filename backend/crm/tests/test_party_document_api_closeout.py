from datetime import date
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from crm.models import Customer, Order, PurchaseOrder, Supplier


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class DocumentPartyApiTests(TestCase):
    def setUp(self):
        users = get_user_model()
        users.objects.create_user(username='doc-api-a', password='synthetic')
        users.objects.create_user(username='doc-api-b', password='synthetic')
        self.a, self.b = APIClient(), APIClient()
        self.assertTrue(self.a.login(username='doc-api-a', password='synthetic'))
        self.assertTrue(self.b.login(username='doc-api-b', password='synthetic'))
        customer = Customer.objects.create(code='DAPIC', name='Synthetic Buyer', country='Germany')
        supplier = Supplier.objects.create(code='DA', name='Synthetic Supplier')
        self.order = Order.objects.create(order_no='DAPI-SO', customer=customer, order_date=date(2026, 11, 5),
            status='confirmed', customer_name_snapshot='Synthetic Buyer', customer_country_snapshot='Germany',
            customer_address_snapshot='Original', customer_contact_name_snapshot='Contact',
            customer_phone_snapshot='123', customer_email_snapshot='a@example.invalid')
        self.purchase = PurchaseOrder.objects.create(purchase_no='DAPI-PO', supplier=supplier,
            order_date=date(2026, 11, 5), status='ordered', supplier_name_snapshot='Synthetic Supplier',
            supplier_address_snapshot='Original', supplier_contact_name_snapshot='Contact',
            supplier_phone_snapshot='123', supplier_email_snapshot='a@example.invalid')

    def test_two_corrections_preserve_original_and_existing_business_facts(self):
        for document, url, field in ((self.order, f'/api/orders/{self.order.pk}/party-change/', 'customer_address_snapshot'),
                                     (self.purchase, f'/api/purchase-orders/{self.purchase.pk}/party-change/', 'supplier_address_snapshot')):
            with self.subTest(document=url):
                self.assertEqual(APIClient().get(url).status_code, 401)
                for expected in ('Corrected A', 'Corrected B'):
                    base = self.a.get(url)
                    self.assertEqual(base.status_code, 200, base.data)
                    proposed = dict(base.data['baseline']['snapshot'], address=expected)
                    created = self.a.post(url, {'expected_base_fingerprint': base.data['baseline']['fingerprint'],
                        'proposed_snapshot': proposed, 'change_type': 'correction', 'reason': 'Synthetic reason',
                        'evidence': 'Synthetic supporting record', 'source_trust': 'unverified'}, format='json')
                    self.assertEqual(created.status_code, 201, created.data)
                    identifier = created.data['id']
                    approved = self.b.post(f'{url}{identifier}/approve/', {'expected_content_fingerprint': created.data['content_fingerprint'],
                        'note': 'Independent synthetic review'}, format='json')
                    self.assertEqual(approved.status_code, 200, approved.data)
                    applied = self.a.post(f'{url}{identifier}/apply/', {}, format='json')
                    self.assertEqual(applied.status_code, 200, applied.data)
                    self.assertEqual(self.a.get(url).data['baseline']['snapshot']['address'], expected)
                    detail_url = url.removesuffix('party-change/')
                    detail = self.a.get(detail_url)
                    self.assertEqual(detail.status_code, 200, detail.data)
                    self.assertEqual(detail.data['effective_party']['address'], expected)
                document.refresh_from_db()
                self.assertEqual(getattr(document, field), 'Original')
                self.assertEqual(document.items.count(), 0)
                self.assertEqual(document.payment_plans.count(), 0)

    @override_settings(APP_STAGE='production', DEBUG=False, DEVELOPMENT_SUPERADMIN=False, RBAC_ENFORCEMENT=True)
    def test_effective_party_redacted_without_related_party_permission(self):
        from django.contrib.auth.models import AnonymousUser
        from crm.serializers import OrderSerializer, PurchaseOrderSerializer
        context = {'user': AnonymousUser()}
        self.assertIsNone(OrderSerializer(self.order, context=context).data['effective_party'])
        self.assertIsNone(PurchaseOrderSerializer(self.purchase, context=context).data['effective_party'])
