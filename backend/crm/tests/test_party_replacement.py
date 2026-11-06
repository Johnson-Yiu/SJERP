from copy import deepcopy
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connection, transaction
from django.test import override_settings
from rest_framework.test import APIClient

from crm.models import Customer, Order, PurchaseOrder, Quote, Supplier
from crm.party_replacement_models import PartyReplacementLink
from crm.tests.test_quote_buyer_tax_id import QuoteBuyerTaxTests


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class PartyReplacementTests(QuoteBuyerTaxTests):
    def setUp(self):
        super().setUp()
        users = get_user_model()
        users.objects.create_user(username='replacement-maker', password='test-only')
        users.objects.create_user(username='replacement-reviewer', password='test-only')
        self.maker = APIClient()
        self.reviewer = APIClient()
        self.assertTrue(self.maker.login(username='replacement-maker', password='test-only'))
        self.assertTrue(self.reviewer.login(username='replacement-reviewer', password='test-only'))
        self.source = self.create_quote()
        Quote.objects.filter(pk=self.source.pk).update(status='sent')
        self.target = Customer.objects.create(code='RPT', name='Synthetic Replacement', country='France')
        self.url = f'/api/quotes/{self.source.pk}/party-change/'

    def proposal(self):
        baseline = self.maker.get(self.url).data['baseline']
        proposed = deepcopy(baseline['snapshot'])
        proposed.update(name=self.target.name, country='France', address='', contact='', phone='', email='', tax_id='')
        data = {'expected_base_fingerprint': baseline['fingerprint'], 'proposed_snapshot': proposed,
                'change_type': 'replacement', 'reason': 'Synthetic reason', 'evidence': 'Synthetic evidence',
                'source_trust': 'unverified', 'replacement_target_id': self.target.pk}
        result = self.maker.post(self.url, data, format='json')
        self.assertEqual(result.status_code, 201, result.data)
        return result.data

    def payload(self):
        return {'customer': self.target.pk, 'quote_date': '2026-11-05', 'currency': 'USD', 'exchange_rate': '7.2',
            'shipping_fee': '0', 'discount': '0', 'deposit_ratio': '0.3', 'trading_terms': '', 'shipping_details': '',
            'recipient_name': '', 'buyer_address': '', 'buyer_email': '', 'buyer_phone': '', 'buyer_tax_id': '',
            'items': [{'sku': self.sku.pk, 'quantity': '2', 'unit_price': '3'}]}

    def test_approved_replacement_creates_new_draft_without_changing_source(self):
        source = Quote.objects.get(pk=self.source.pk)
        before = (source.customer_id, source.status, list(source.items.values_list('sku_id', 'quantity', 'unit_price')))
        proposal = self.proposal()
        decision = self.reviewer.post(f"{self.url}{proposal['id']}/approve/", {'expected_content_fingerprint': proposal['content_fingerprint'], 'note': 'Synthetic review'}, format='json')
        self.assertEqual(decision.status_code, 200, decision.data)
        result = self.maker.post(f"{self.url}{proposal['id']}/create-replacement/", self.payload(), format='json')
        self.assertEqual(result.status_code, 200, result.data)
        created = Quote.objects.get(pk=result.data['result_quote_id'])
        self.assertEqual((created.status, created.customer_id, created.parent_quote_id), ('draft', self.target.pk, None))
        self.assertEqual(list(created.items.values_list('sku_id', 'quantity', 'unit_price'))[0][1:], (2, 3))
        source.refresh_from_db()
        self.assertEqual((source.customer_id, source.status, list(source.items.values_list('sku_id', 'quantity', 'unit_price'))), before)
        self.assertEqual(PartyReplacementLink.objects.count(), 1)
        current = self.maker.get(self.url).data['requests'][0]
        self.assertEqual(current['status'], 'applied')
        self.assertEqual(current['replacement_result']['result_quote_id'], created.pk)
        for operation in ('withdraw', 'invalidate'):
            denied = self.maker.post(f"{self.url}{proposal['id']}/{operation}/", {'note': 'Synthetic'}, format='json')
            self.assertEqual(denied.status_code, 400, denied.data)
        replay = self.maker.post(f"{self.url}{proposal['id']}/create-replacement/", self.payload(), format='json')
        self.assertEqual(replay.status_code, 200, replay.data)
        self.assertEqual(replay.data, result.data)
        changed = self.payload()
        changed['items'][0]['quantity'] = '9'
        self.assertEqual(self.maker.post(f"{self.url}{proposal['id']}/create-replacement/", changed, format='json').status_code, 400)
        Quote.objects.filter(pk=created.pk).update(buyer_address='Tampered')
        created.refresh_from_db()
        created.status = 'sent'
        with self.assertRaises(ValidationError):
            created.save(update_fields=['status'])
        created.refresh_from_db()
        self.assertEqual(created.status, 'draft')
        Quote.objects.filter(pk=created.pk).update(buyer_address='')
        created.refresh_from_db()
        response = self.maker.post(f'/api/quotes/{created.pk}/mark-sent/', {}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(Quote.objects.get(pk=created.pk).status, 'sent')

    def test_missing_binding_and_unapproved_or_incomplete_payload_rejected(self):
        proposal = self.proposal()
        url = f"{self.url}{proposal['id']}/create-replacement/"
        self.assertEqual(self.maker.post(url, self.payload(), format='json').status_code, 400)
        self.assertEqual(self.maker.post(f"{self.url}{proposal['id']}/approve/", {'expected_content_fingerprint': proposal['content_fingerprint'], 'note': 'Self'}, format='json').status_code, 400)
        approval = self.reviewer.post(f"{self.url}{proposal['id']}/approve/", {'expected_content_fingerprint': proposal['content_fingerprint'], 'note': 'Review'}, format='json')
        self.assertEqual(approval.status_code, 200, approval.data)
        invalid = self.payload()
        invalid['items'] = []
        self.assertEqual(self.maker.post(url, invalid, format='json').status_code, 400)
        self.assertFalse(PartyReplacementLink.objects.exists())

    def test_approved_replacement_creation_records_link(self):
        proposal = self.proposal()
        decision = self.reviewer.post(f"{self.url}{proposal['id']}/approve/", {'expected_content_fingerprint': proposal['content_fingerprint'], 'note': 'Review'}, format='json')
        self.assertEqual(decision.status_code, 200, decision.data)
        before = Quote.objects.count()
        result = self.maker.post(f"{self.url}{proposal['id']}/create-replacement/", self.payload(), format='json')
        self.assertEqual(result.status_code, 200, result.data)
        self.assertEqual(Quote.objects.count(), before + 1)
        self.assertEqual(PartyReplacementLink.objects.count(), 1)

    def _synthetic_link_for_formalization(self):
        from crm.models import PartyVersionApproval, PartyVersionRequest
        from crm.party_replacement import _hash_payload, _link_hash
        from crm.party_version import _approval_attestation_fingerprint
        proposal = self.proposal()
        decision = self.reviewer.post(f"{self.url}{proposal['id']}/approve/", {'expected_content_fingerprint': proposal['content_fingerprint'], 'note': 'Review'}, format='json')
        self.assertEqual(decision.status_code, 200, decision.data)
        obj = PartyVersionRequest.objects.get(pk=proposal['id'])
        approval = PartyVersionApproval.objects.get(request=obj)
        result = Quote.objects.create(quote_no='SYN-REPLACEMENT-LINK', customer=self.target, quote_date='2026-11-05',
            recipient_name='', buyer_address='', buyer_phone='', buyer_email='', buyer_tax_id='')
        link = PartyReplacementLink(target=obj.replacement_target, approval=approval, result_quote=result,
            created_by=obj.initiator, approved_fingerprint=obj.content_fingerprint,
            approval_fingerprint=_approval_attestation_fingerprint(approval), payload_fingerprint=_hash_payload(self.payload()))
        link.link_fingerprint = _link_hash(link)
        link.save()
        PartyVersionRequest._base_manager.filter(pk=obj.pk).update(is_active=False)
        return result, link

    def test_formalization_requires_same_transaction_source_first_token(self):
        from crm.party_replacement import prepare_formalization, snapshot_for_confirmation
        result, _link = self._synthetic_link_for_formalization()
        self.target.name = 'Synthetic master renamed'
        self.target.save(update_fields=['name'])
        with transaction.atomic():
            with self.assertRaisesMessage(ValidationError, '必须先按来源顺序'):
                snapshot_for_confirmation(result, 'quote')
            token = prepare_formalization('quote', result.pk)
            snapshot = snapshot_for_confirmation(result, 'quote', context=token)
            self.assertEqual(snapshot['buyer_company_name'], 'Synthetic Replacement')
            with transaction.atomic():
                nested = prepare_formalization('quote', result.pk)
            with self.assertRaises(ValidationError):
                snapshot_for_confirmation(result, 'quote', context=nested)
        with transaction.atomic(), self.assertRaises(ValidationError):
            snapshot_for_confirmation(result, 'quote', context=token)

    def test_formalization_rechecks_source_and_approval_evidence(self):
        from crm.party_replacement import prepare_formalization
        result, link = self._synthetic_link_for_formalization()
        original_address = self.source.buyer_address
        Quote.objects.filter(pk=self.source.pk).update(buyer_address='Synthetic changed source')
        with self.assertRaises(ValidationError), transaction.atomic():
            prepare_formalization('quote', result.pk)
        Quote.objects.filter(pk=self.source.pk).update(buyer_address=original_address)
        if connection.vendor == 'sqlite':
            with connection.cursor() as cursor:
                cursor.execute('UPDATE crm_partyreplacementlink SET approval_fingerprint=%s WHERE id=%s', ['0' * 64, link.pk])
            with self.assertRaises(ValidationError), transaction.atomic():
                prepare_formalization('quote', result.pk)

    def test_replay_preserves_later_edits_and_rejects_changed_payload_or_party(self):
        from crm.party_replacement import _hash_payload, _verify_replay
        result, link = self._synthetic_link_for_formalization()
        approval = link.approval
        proposal = approval.request.proposed_snapshot
        Quote.objects.filter(pk=result.pk).update(notes='Synthetic later edit')
        with transaction.atomic():
            same = _verify_replay(link, approval, 'quote', self.target.pk, _hash_payload(self.payload()), proposal)
        self.assertEqual(same.pk, link.pk)
        self.assertEqual(Quote.objects.get(pk=result.pk).notes, 'Synthetic later edit')
        with self.assertRaises(ValidationError), transaction.atomic():
            _verify_replay(link, approval, 'quote', self.target.pk, '0' * 64, proposal)
        from crm.party_document_details import unknown_details
        from crm.party_document_details_models import PartyDocumentDetailsStorage
        PartyDocumentDetailsStorage.objects.create(quote=result, details=unknown_details())
        with transaction.atomic():
            self.assertEqual(_verify_replay(link, approval, 'quote', self.target.pk, _hash_payload(self.payload()), proposal).pk, link.pk)
        with self.assertRaises(ValidationError), transaction.atomic():
            from crm.party_replacement import prepare_formalization
            prepare_formalization('quote', result.pk)
        Quote.objects.filter(pk=result.pk).update(buyer_address='Synthetic modified party')
        with self.assertRaises(ValidationError), transaction.atomic():
            _verify_replay(link, approval, 'quote', self.target.pk, _hash_payload(self.payload()), proposal)

    def test_order_and_purchase_source_snapshot_change_blocks_formalization(self):
        from crm.models import PartyVersionApproval, PartyVersionRequest
        from crm.party_replacement import _link_hash, prepare_formalization
        from crm.party_version import _approval_attestation_fingerprint

        old_supplier = Supplier.objects.create(code='S1', name='Synthetic original supplier')
        new_supplier = Supplier.objects.create(code='S2', name='Synthetic target supplier')
        old_order = Order.objects.create(order_no='SYN-SOURCE-SO', customer=self.customer,
            order_date='2026-11-05', status='confirmed', customer_name_snapshot=self.customer.name)
        old_po = PurchaseOrder.objects.create(purchase_no='SYN-SOURCE-PO', supplier=old_supplier,
            order_date='2026-11-05', status='ordered', supplier_name_snapshot=old_supplier.name)
        for kind, route, source, target in [('order', 'orders', old_order, self.target),
                                             ('purchase_order', 'purchase-orders', old_po, new_supplier)]:
            with self.subTest(kind=kind):
                url = f'/api/{route}/{source.pk}/party-change/'
                base = self.maker.get(url).data['baseline']
                proposed = dict(base['snapshot'], name=target.name)
                proposal = self.maker.post(url, {'expected_base_fingerprint': base['fingerprint'],
                    'proposed_snapshot': proposed, 'change_type': 'replacement', 'reason': 'Synthetic',
                    'evidence': 'Synthetic', 'source_trust': 'unverified', 'replacement_target_id': target.pk}, format='json')
                self.assertEqual(proposal.status_code, 201, proposal.data)
                decision = self.reviewer.post(f"{url}{proposal.data['id']}/approve/",
                    {'expected_content_fingerprint': proposal.data['content_fingerprint'], 'note': 'Synthetic'}, format='json')
                self.assertEqual(decision.status_code, 200, decision.data)
                obj = PartyVersionRequest.objects.get(pk=proposal.data['id'])
                approval = PartyVersionApproval.objects.get(request=obj)
                result = (Order.objects.create(order_no='SYN-RESULT-SO', customer=target, order_date='2026-11-05')
                          if kind == 'order' else PurchaseOrder.objects.create(purchase_no='SYN-RESULT-PO', supplier=target, order_date='2026-11-05'))
                link = PartyReplacementLink(target=obj.replacement_target, approval=approval, created_by=obj.initiator,
                    approved_fingerprint=obj.content_fingerprint, approval_fingerprint=_approval_attestation_fingerprint(approval),
                    payload_fingerprint='a' * 64, **{'result_' + kind: result})
                link.link_fingerprint = _link_hash(link)
                link.save()
                PartyVersionRequest._base_manager.filter(pk=obj.pk).update(is_active=False)
                with transaction.atomic():
                    self.assertIsNotNone(prepare_formalization(kind, result.pk))
                field = 'customer_address_snapshot' if kind == 'order' else 'supplier_address_snapshot'
                source.__class__.objects.filter(pk=source.pk).update(**{field: 'Synthetic changed source'})
                with self.assertRaises(ValidationError), transaction.atomic():
                    prepare_formalization(kind, result.pk)

    def test_structured_order_and_purchase_drafts_keep_only_explicit_approved_details(self):
        from crm.party_document_details import unknown_details
        from crm.party_document_details_models import PartyDocumentDetailsStorage

        supplier = Supplier.objects.create(code='D1', name='Synthetic old structured supplier')
        target_supplier = Supplier.objects.create(code='D2', name='Synthetic new structured supplier')
        source_order = Order.objects.create(order_no='SYN-DETAIL-SO', customer=self.customer, order_date='2026-11-05', customer_name_snapshot=self.customer.name)
        source_purchase = PurchaseOrder.objects.create(purchase_no='SYN-DETAIL-PO', supplier=supplier, order_date='2026-11-05', supplier_name_snapshot=supplier.name)
        for kind, route, source, target, side in [('order', 'orders', source_order, self.target, 'buyer'), ('purchase_order', 'purchase-orders', source_purchase, target_supplier, 'seller')]:
            with self.subTest(kind=kind):
                old = unknown_details()
                old[side]['name'] = source.customer.name if kind == 'order' else source.supplier.name
                old[side]['address'] = 'Synthetic old address must not be copied'
                PartyDocumentDetailsStorage.objects.create(**{kind: source}, details=old)
                source.__class__.objects.filter(pk=source.pk).update(status='confirmed' if kind == 'order' else 'ordered')
                url = f'/api/{route}/{source.pk}/party-change/'
                basis = self.maker.get(url).data['baseline']
                proposed = dict(basis['snapshot'], name=target.name)
                new = unknown_details()
                new[side]['name'] = target.name
                new[side]['address'] = ''
                proposed['party_details'] = new
                proposal = self.maker.post(url, {'expected_base_fingerprint': basis['fingerprint'], 'proposed_snapshot': proposed,
                    'change_type': 'replacement', 'reason': 'Synthetic', 'evidence': 'Synthetic', 'source_trust': 'unverified', 'replacement_target_id': target.pk}, format='json')
                self.assertEqual(proposal.status_code, 201, proposal.data)
                decision = self.reviewer.post(f"{url}{proposal.data['id']}/approve/", {'expected_content_fingerprint': proposal.data['content_fingerprint'], 'note': 'Reviewed'}, format='json')
                self.assertEqual(decision.status_code, 200, decision.data)
                payload = {('customer' if kind == 'order' else 'supplier'): target.pk, 'order_date': '2026-11-05',
                    'currency': 'USD', 'exchange_rate': '7.2', 'items': [{'sku': self.sku.pk, 'quantity': '2', 'unit_price': '3'}]}
                payload.update({'shipping_fee': '0', 'discount': '0', 'tail_goods_policy': 'SAME_CARTON'} if kind == 'order' else {'payment_terms_snapshot': []})
                endpoint = f"{url}{proposal.data['id']}/create-replacement/"
                result = self.maker.post(endpoint, payload, format='json')
                self.assertEqual(result.status_code, 200, result.data)
                result_id = result.data['result_order_id' if kind == 'order' else 'result_purchase_order_id']
                row = PartyDocumentDetailsStorage.objects.get(**{kind + '_id': result_id})
                self.assertEqual(row.details, new)
                self.assertIsNone(row.details[side]['phone'])
                self.assertEqual(row.details[side]['address'], '')
                self.assertEqual(PartyDocumentDetailsStorage.objects.get(**{kind: source}).details, old)
                replay = self.maker.post(endpoint, payload, format='json')
                self.assertEqual(replay.status_code, 200, replay.data)
                formal_url = f'/api/{route}/{result_id}/' + ('confirm/' if kind == 'order' else 'place/')
                changed = deepcopy(new)
                changed[side]['address'] = 'Unapproved change'
                row.details = changed
                row.save(update_fields=['details'])
                denied_replay = self.maker.post(endpoint, payload, format='json')
                self.assertEqual(denied_replay.status_code, 400, denied_replay.data)
                denied = self.maker.post(formal_url, {}, format='json')
                self.assertEqual(denied.status_code, 400, denied.data)
                self.assertEqual(source.__class__.objects.get(pk=result_id).status, 'draft')
                row.details = new
                row.save(update_fields=['details'])
                formal = self.maker.post(formal_url, {}, format='json')
                self.assertEqual(formal.status_code, 200, formal.data)
                draft = source.__class__.objects.get(pk=result_id)
                self.assertEqual(draft.status, 'confirmed' if kind == 'order' else 'ordered')
                self.assertEqual(draft.customer_id if kind == 'order' else draft.supplier_id, target.pk)
                self.assertIsNone(draft.quote_id if kind == 'order' else draft.order_id)
                from crm.party_document_version import effective_snapshot
                self.assertEqual(effective_snapshot(draft)['party_details'], new)
                source.refresh_from_db()
                self.assertEqual(source.status, 'confirmed' if kind == 'order' else 'ordered')
                self.assertEqual(PartyDocumentDetailsStorage.objects.get(**{kind: source}).details, old)

    def test_link_failure_rolls_back_created_quote(self):
        proposal = self.proposal()
        approval = self.reviewer.post(f"{self.url}{proposal['id']}/approve/", {'expected_content_fingerprint': proposal['content_fingerprint'], 'note': 'Review'}, format='json')
        self.assertEqual(approval.status_code, 200, approval.data)
        before = Quote.objects.count()
        with patch('crm.party_replacement.PartyReplacementLink.save', side_effect=ValidationError('Synthetic failure')):
            result = self.maker.post(f"{self.url}{proposal['id']}/create-replacement/", self.payload(), format='json')
        self.assertEqual(result.status_code, 400, result.data)
        self.assertEqual(Quote.objects.count(), before)
        self.assertFalse(PartyReplacementLink.objects.exists())

    def test_legacy_replacement_approval_does_not_allow_creation(self):
        from crm.models import PartyVersionRequest
        from crm.party_version import _content, _digest
        baseline = self.maker.get(self.url).data['baseline']
        proposed = dict(baseline['snapshot'], name='Synthetic old proposal')
        obj = PartyVersionRequest(quote=self.source, initiator=get_user_model().objects.get(username='replacement-maker'),
            base_snapshot=baseline['snapshot'], proposed_snapshot=proposed, base_fingerprint=baseline['fingerprint'],
            change_type='replacement', reason='Synthetic', evidence='Synthetic', source_trust='unknown')
        obj.content_fingerprint = _digest(_content(obj))
        obj.save()
        decision = self.reviewer.post(f'{self.url}{obj.pk}/approve/', {'expected_content_fingerprint': obj.content_fingerprint, 'note': 'Legacy'}, format='json')
        self.assertEqual(decision.status_code, 200, decision.data)
        result = self.maker.post(f'{self.url}{obj.pk}/create-replacement/', self.payload(), format='json')
        self.assertEqual(result.status_code, 400, result.data)
        self.assertFalse(PartyReplacementLink.objects.exists())

    def test_quote_revision_with_unapproved_structured_details_cannot_be_sent(self):
        from crm.party_document_details import unknown_details
        from crm.party_document_details_models import PartyDocumentDetailsStorage
        revision = self.maker.post(f'/api/quotes/{self.source.pk}/revise/', {'revision_summary': 'Synthetic'}, format='json')
        self.assertEqual(revision.status_code, 201, revision.data)
        PartyDocumentDetailsStorage.objects.create(quote_id=revision.data['id'], details=unknown_details())
        response = self.maker.post(f"/api/quotes/{revision.data['id']}/mark-sent/", {}, format='json')
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(Quote.objects.get(pk=revision.data['id']).status, 'draft')

    def test_order_and_purchase_preserve_approved_party_after_master_changes(self):
        supplier = Supplier.objects.create(code='R1', name='Synthetic Original Supplier')
        new_supplier = Supplier.objects.create(code='R2', name='Synthetic Replacement Supplier')
        order = Order.objects.create(order_no='SYN-REPLACE-SO', customer=self.customer, order_date='2026-11-05', status='confirmed', customer_name_snapshot=self.customer.name)
        purchase = PurchaseOrder.objects.create(purchase_no='SYN-REPLACE-PO', supplier=supplier, order_date='2026-11-05', status='ordered', supplier_name_snapshot=supplier.name)
        order.items.create(sku=self.sku, quantity='9', unit_price='11')
        purchase.items.create(sku=self.sku, quantity='8', unit_price='12')
        cases = [('orders', order, self.target, 'customer'), ('purchase-orders', purchase, new_supplier, 'supplier')]
        for route, source, target, party in cases:
            with self.subTest(route=route):
                url = f'/api/{route}/{source.pk}/party-change/'
                baseline = self.maker.get(url).data['baseline']
                proposed = dict(baseline['snapshot'], name=target.name)
                proposal = self.maker.post(url, {'expected_base_fingerprint': baseline['fingerprint'],
                    'proposed_snapshot': proposed, 'change_type': 'replacement', 'reason': 'Synthetic',
                    'evidence': 'Synthetic', 'source_trust': 'unverified', 'replacement_target_id': target.pk}, format='json')
                self.assertEqual(proposal.status_code, 201, proposal.data)
                approval = self.reviewer.post(f"{url}{proposal.data['id']}/approve/", {'expected_content_fingerprint': proposal.data['content_fingerprint'], 'note': 'Review'}, format='json')
                self.assertEqual(approval.status_code, 200, approval.data)
                payload = {party: target.pk, 'order_date': '2026-11-05', 'currency': 'USD', 'exchange_rate': '7.2',
                    'items': [{'sku': self.sku.pk, 'quantity': '2', 'unit_price': '3'}]}
                payload.update({'payment_terms_snapshot': []} if party == 'supplier' else {'shipping_fee': '0', 'discount': '0', 'tail_goods_policy': 'SAME_CARTON'})
                before = source.__class__.objects.count()
                result = self.maker.post(f"{url}{proposal.data['id']}/create-replacement/", payload, format='json')
                self.assertEqual(result.status_code, 200, result.data)
                key = 'result_purchase_order_id' if party == 'supplier' else 'result_order_id'
                draft = source.__class__.objects.get(pk=result.data[key])
                self.assertEqual(draft.status, 'draft')
                self.assertEqual(source.__class__.objects.count(), before + 1)
                self.assertEqual(list(draft.items.values_list('quantity', 'unit_price')), [(2, 3)])
                self.assertEqual(list(source.items.values_list('quantity', 'unit_price')),
                                 [(9, 11)] if party == 'customer' else [(8, 12)])
                self.assertFalse(draft.transactions.exists())
                self.assertFalse(draft.payment_plans.exists())
                target.name = 'Changed ' + target.name
                target.save(update_fields=['name'])
                link = PartyReplacementLink.objects.get(**{'result_' + ('order' if party == 'customer' else 'purchase_order'): draft})
                if connection.vendor == 'sqlite':
                    with connection.cursor() as cursor:
                        cursor.execute('UPDATE crm_partyreplacementlink SET approval_fingerprint=%s WHERE id=%s', ['0' * 64, link.pk])
                    with self.assertRaises(ValidationError):
                        if party == 'supplier':
                            from crm.services.purchase_lifecycle import place_purchase_order
                            place_purchase_order(draft)
                        else:
                            from crm.services.order_lifecycle import confirm_order
                            confirm_order(draft)
                    draft.refresh_from_db()
                    self.assertEqual(draft.status, 'draft')
                    with connection.cursor() as cursor:
                        cursor.execute('UPDATE crm_partyreplacementlink SET approval_fingerprint=%s WHERE id=%s', [link.approval_fingerprint, link.pk])
                if party == 'supplier':
                    from crm.services.purchase_lifecycle import place_purchase_order
                    formal = place_purchase_order(draft)
                    self.assertEqual(formal.supplier_name_snapshot, proposed['name'])
                else:
                    from crm.services.order_lifecycle import confirm_order
                    formal = confirm_order(draft)
                    self.assertEqual(formal.customer_name_snapshot, proposed['name'])
                source.refresh_from_db()
                self.assertEqual(source.status, 'ordered' if party == 'supplier' else 'confirmed')
