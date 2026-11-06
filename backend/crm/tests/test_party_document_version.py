from copy import deepcopy
from datetime import date
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import Client, RequestFactory, TestCase, override_settings
from crm.models import Customer, Order, Supplier, PurchaseOrder
from crm.party_document_models import PartyDocumentVersion
from crm.party_document_version import apply, effective_snapshot, identity_fingerprint
from crm.party_version import approve, baseline, propose, _content, _digest
from crm.party_version_models import PartyVersionRequest

@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class PartyDocumentVersionTests(TestCase):
    def setUp(self):
        a=Client(); b=Client(); User=get_user_model()
        self.maker=User.objects.create_user(username='doc-maker',password='test-only')
        User.objects.create_user(username='doc-review',password='test-only')
        self.assertTrue(a.login(username='doc-maker',password='test-only')); self.assertTrue(b.login(username='doc-review',password='test-only'))
        self.a=RequestFactory().post('/'); self.a.session=a.session
        self.b=RequestFactory().post('/'); self.b.session=b.session
        customer=Customer.objects.create(code='DV-C',name='Buyer',country='Germany')
        supplier=Supplier.objects.create(code='DV',name='Supplier')
        self.order=Order.objects.create(order_no='DV-SO',customer=customer,order_date=date(2026,1,1),status='confirmed',customer_name_snapshot='Buyer',customer_country_snapshot='Germany',customer_address_snapshot='Old',customer_contact_name_snapshot='Contact',customer_phone_snapshot='123',customer_email_snapshot='a@example.invalid')
        self.po=PurchaseOrder.objects.create(purchase_no='DV-PO',supplier=supplier,order_date=date(2026,1,1),status='ordered',supplier_name_snapshot='Supplier',supplier_address_snapshot='Old',supplier_contact_name_snapshot='Contact',supplier_phone_snapshot='123',supplier_email_snapshot='a@example.invalid')

    def proposal(self, kind, target, change='correction', field='address'):
        base=baseline(request=self.a,target_type=kind,target_id=target.pk)
        values=deepcopy(base['snapshot']); values[field]='Corrected'
        obj=PartyVersionRequest(**{kind:target}, initiator=self.maker, base_snapshot=base['snapshot'],
            proposed_snapshot=values, base_fingerprint=base['fingerprint'],
            source_document_fingerprint=identity_fingerprint(target), change_type=change,
            reason='Synthetic', evidence='Synthetic', source_trust='unverified')
        obj.content_fingerprint=_digest(_content(obj)); obj.save()
        approve(request=self.b,request_id=obj.pk,expected_content_fingerprint=obj.content_fingerprint,note='Reviewed')
        return obj

    def test_order_and_purchase_preserve_original(self):
        for kind,target in (('order',self.order),('purchase_order',self.po)):
            with self.subTest(kind=kind):
                original=effective_snapshot(target); req=self.proposal(kind,target)
                version=apply(request=self.a,request_id=req.pk)
                self.assertEqual(version.version_no,1); self.assertEqual(version.base_snapshot,original)
                self.assertEqual(effective_snapshot(target)['address'],'Corrected')
                target.refresh_from_db()
                self.assertEqual(getattr(target,'customer_address_snapshot' if kind=='order' else 'supplier_address_snapshot'),'Old')
                self.assertEqual(apply(request=self.b,request_id=req.pk).pk,version.pk)
                with self.assertRaises(ValidationError): version.delete()

    def test_replacement_and_anonymous_cannot_apply(self):
        obj=self.proposal('order',self.order,'replacement')
        with self.assertRaises(ValidationError): apply(request=self.a,request_id=obj.pk)
        with self.assertRaises(ValidationError): apply(request=RequestFactory().post('/'),request_id=obj.pk)
        self.assertFalse(PartyDocumentVersion.objects.exists())

    def test_unknown_snapshot_is_not_filled(self):
        Order.objects.filter(pk=self.order.pk).update(customer_phone_snapshot='')
        obj=self.proposal('order',self.order,field='phone')
        with self.assertRaises(ValidationError): apply(request=self.a,request_id=obj.pk)
        self.assertFalse(PartyDocumentVersion.objects.exists())

    def test_effective_read_rejects_approval_tampering(self):
        from django.db import connection
        obj=self.proposal('order',self.order)
        apply(request=self.a,request_id=obj.pk)
        with connection.cursor() as cursor:
            cursor.execute('UPDATE crm_partyversionapproval SET note=%s WHERE request_id=%s',['altered',obj.pk])
        with self.assertRaises(ValidationError): effective_snapshot(self.order)

    def test_missing_signed_party_identity_is_rejected(self):
        from django.db import connection
        obj=self.proposal('order',self.order)
        with connection.cursor() as cursor:
            cursor.execute('UPDATE crm_partyversionrequest SET source_document_fingerprint=NULL WHERE id=%s',[obj.pk])
        with self.assertRaises(ValidationError): apply(request=self.a,request_id=obj.pk)

    def test_replay_older_version_validates_entire_chain_without_new_record(self):
        first_request = self.proposal('order', self.order)
        first = apply(request=self.a, request_id=first_request.pk)
        basis = baseline(request=self.a, target_type='order', target_id=self.order.pk)
        base = basis['snapshot']
        self.assertEqual(base, effective_snapshot(self.order))
        proposed = deepcopy(base)
        proposed['address'] = 'Corrected again'
        second_request = propose(request=self.a, target_type='order', target_id=self.order.pk,
            expected_base_fingerprint=basis['fingerprint'], proposed_snapshot=proposed,
            change_type='correction', reason='Synthetic second', evidence='Synthetic second',
            source_trust='unverified')
        self.assertEqual(second_request.source_document_fingerprint, identity_fingerprint(self.order))
        approve(request=self.b, request_id=second_request.pk,
            expected_content_fingerprint=second_request.content_fingerprint, note='Reviewed again')
        second = apply(request=self.a, request_id=second_request.pk)
        self.assertEqual(second.previous_id, first.pk)
        self.assertEqual(apply(request=self.b, request_id=first_request.pk).pk, first.pk)
        self.assertEqual(PartyDocumentVersion.objects.filter(order=self.order).count(), 2)
        self.assertEqual(effective_snapshot(self.order), proposed)

    def test_full_details_use_existing_approved_version_chain(self):
        from crm.party_document_details import unknown_details, read_document_details
        from crm.party_document_details_models import PartyDocumentDetailsStorage
        from crm.party_version import propose
        Order.objects.filter(pk=self.order.pk).update(status='draft')
        details = unknown_details()
        details['buyer']['address'] = 'Old buyer address'
        PartyDocumentDetailsStorage.objects.create(order=self.order, details=details)
        Order.objects.filter(pk=self.order.pk).update(status='confirmed')
        basis = baseline(request=self.a, target_type='order', target_id=self.order.pk)
        proposed = deepcopy(basis['snapshot'])
        proposed['party_details']['buyer']['address'] = 'Corrected buyer address'
        obj = propose(request=self.a, target_type='order', target_id=self.order.pk,
            expected_base_fingerprint=basis['fingerprint'], proposed_snapshot=proposed,
            change_type='correction', reason='Synthetic', evidence='Synthetic', source_trust='unverified')
        approve(request=self.b, request_id=obj.pk, expected_content_fingerprint=obj.content_fingerprint, note='Reviewed')
        version = apply(request=self.a, request_id=obj.pk)
        self.assertEqual(version.snapshot, proposed)
        self.assertEqual(read_document_details(request=self.a, target_type='order', target_id=self.order.pk), proposed['party_details'])
        self.assertEqual(PartyDocumentDetailsStorage.objects.get(order=self.order).details, details)
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute('UPDATE crm_partyversionapproval SET note=%s WHERE request_id=%s', ['altered', obj.pk])
        with self.assertRaises(ValidationError):
            read_document_details(request=self.a, target_type='order', target_id=self.order.pk)

    def test_purchase_full_details_use_existing_version(self):
        from crm.party_document_details import unknown_details, read_document_details
        from crm.party_document_details_models import PartyDocumentDetailsStorage
        from crm.party_version import propose
        PurchaseOrder.objects.filter(pk=self.po.pk).update(status='draft')
        details = unknown_details(); details['seller']['address'] = 'Old address'
        PartyDocumentDetailsStorage.objects.create(purchase_order=self.po, details=details)
        PurchaseOrder.objects.filter(pk=self.po.pk).update(status='ordered')
        basis = baseline(request=self.a, target_type='purchase_order', target_id=self.po.pk)
        proposed = deepcopy(basis['snapshot']); proposed['party_details']['seller']['address'] = 'New address'
        obj = propose(request=self.a, target_type='purchase_order', target_id=self.po.pk,
            expected_base_fingerprint=basis['fingerprint'], proposed_snapshot=proposed,
            change_type='correction', reason='Synthetic', evidence='Synthetic', source_trust='unverified')
        approve(request=self.b, request_id=obj.pk, expected_content_fingerprint=obj.content_fingerprint, note='Reviewed')
        apply(request=self.a, request_id=obj.pk)
        self.assertEqual(read_document_details(request=self.a, target_type='purchase_order', target_id=self.po.pk), proposed['party_details'])
