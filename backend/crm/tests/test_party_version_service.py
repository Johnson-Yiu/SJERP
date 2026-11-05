from datetime import date
import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import connection
from django.test import Client, RequestFactory, TestCase, override_settings

from crm.models import (AccessRole, Customer, EmployeeProfile, Order, OrganizationUnit,
    PartyVersionApproval, PartyVersionRequest, Position, PurchaseOrder, Quote, RolePermission, Supplier)
from crm.party_version import _content, _digest, approve, baseline, propose, verified_approval


class PartyVersionServiceTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.initiator = user_model.objects.create_user(username='party-test-a', password='testing-password-123')
        self.approver = user_model.objects.create_user(username='party-test-b', password='testing-password-456')
        self.a = self.session_request('party-test-a', 'testing-password-123')
        self.b = self.session_request('party-test-b', 'testing-password-456')
        customer = Customer.objects.create(code='PVT', name='Buyer', country='Germany')
        supplier = Supplier.objects.create(code='PV', name='Supplier')
        self.quote = Quote.objects.create(quote_no='PVT-1', customer=customer, quote_date=date(2026, 1, 1), status='sent')
        self.order = Order.objects.create(order_no='PVT-SO', customer=customer, order_date=date(2026, 1, 1), customer_name_snapshot='Buyer')
        self.purchase = PurchaseOrder.objects.create(purchase_no='PVT-PO', supplier=supplier, order_date=date(2026, 1, 1), supplier_name_snapshot='Supplier')

    def session_request(self, username, password):
        client = Client()
        self.assertTrue(client.login(username=username, password=password))
        request = RequestFactory().post('/')
        request.session = client.session
        return request

    def make(self, target_type='quote', target_id=None, **overrides):
        target_id = target_id or self.quote.pk
        base = baseline(request=self.a, target_type=target_type, target_id=target_id)
        new = {k: (v if v is not None else '') for k, v in base['snapshot'].items()}
        new['name'] = 'Corrected name'
        args = dict(request=self.a, target_type=target_type, target_id=target_id,
            expected_base_fingerprint=base['fingerprint'], proposed_snapshot=new,
            change_type='correction', reason='Correct name', evidence='Document reference', source_trust='unverified')
        args.update(overrides)
        return propose(**args)

    def test_targets_persist_with_independent_approval_and_no_source_write(self):
        for target_type, target in [('quote', self.quote), ('order', self.order), ('purchase_order', self.purchase)]:
            with self.subTest(target=target_type):
                original = baseline(request=self.a, target_type=target_type, target_id=target.pk)
                obj = self.make(target_type, target.pk)
                result = approve(request=self.b, request_id=obj.pk, expected_content_fingerprint=obj.content_fingerprint, note='Checked evidence')
                self.assertEqual(result.approver_id, self.approver.pk)
                self.assertEqual(result.approved_fingerprint, obj.content_fingerprint)
                self.assertEqual(original, baseline(request=self.a, target_type=target_type, target_id=target.pk))
                with self.assertRaises(ValidationError):
                    approve(request=self.b, request_id=obj.pk, expected_content_fingerprint=obj.content_fingerprint, note='Again')
                with self.assertRaises(ValidationError):
                    self.make(target_type, target.pk)

    def test_requires_authenticated_session_and_separate_approver(self):
        anonymous = RequestFactory().post('/')
        anonymous.user = self.initiator
        with self.assertRaises(ValidationError):
            baseline(request=anonymous, target_type='quote', target_id=self.quote.pk)
        obj = self.make()
        with self.assertRaises(ValidationError):
            approve(request=self.a, request_id=obj.pk, expected_content_fingerprint=obj.content_fingerprint, note='No')
        self.assertFalse(PartyVersionApproval.objects.exists())

    def test_incomplete_inputs_rejected(self):
        for invalid in [dict(reason=' '), dict(evidence=''), dict(change_type=''), dict(source_trust='verified'), dict(proposed_snapshot={'name': 'X'}), dict(expected_base_fingerprint='bad')]:
            with self.subTest(invalid=invalid), self.assertRaises(ValidationError):
                self.make(**invalid)
        self.assertFalse(PartyVersionRequest.objects.exists())

    def test_changed_baseline_or_approval_content_rejected(self):
        obj = self.make(change_type='replacement')
        with self.assertRaises(ValidationError):
            approve(request=self.b, request_id=obj.pk, expected_content_fingerprint='wrong', note='Review')
        Quote.objects.filter(pk=self.quote.pk).update(buyer_address='Changed')
        with self.assertRaises(ValidationError):
            approve(request=self.b, request_id=obj.pk, expected_content_fingerprint=obj.content_fingerprint, note='Review')
        self.assertFalse(PartyVersionApproval.objects.exists())

    def test_records_immutable_and_approval_failure_rolls_back(self):
        obj = self.make()
        with patch('crm.party_version.PartyVersionApproval.objects.create', side_effect=RuntimeError('audit failure')):
            with self.assertRaises(RuntimeError):
                approve(request=self.b, request_id=obj.pk, expected_content_fingerprint=obj.content_fingerprint, note='Review')
        self.assertFalse(PartyVersionApproval.objects.exists())
        approval = approve(request=self.b, request_id=obj.pk, expected_content_fingerprint=obj.content_fingerprint, note='Review')
        with self.assertRaises(ValidationError):
            PartyVersionRequest.objects.filter(pk=obj.pk).update(reason='changed')
        with self.assertRaises(ValidationError):
            approval.delete()

    def _inject_request_field(self, obj, field, value):
        # Fault injection only: bypass the model/QuerySet guards inside the test DB.
        table = connection.ops.quote_name(PartyVersionRequest._meta.db_table)
        column = connection.ops.quote_name(field)
        with connection.cursor() as cursor:
            cursor.execute(f'UPDATE {table} SET {column} = %s WHERE id = %s', [value, obj.pk])
            self.assertEqual(cursor.rowcount, 1)

    def _legacy_quote_request(self, base_snapshot=None):
        # 0111 leaves pre-existing quote tax IDs unknown (NULL).
        Quote.objects.filter(pk=self.quote.pk).update(buyer_tax_id=None)
        base = baseline(request=self.a, target_type='quote', target_id=self.quote.pk)['snapshot']
        base.pop('tax_id')
        if base_snapshot is not None:
            base = base_snapshot(base)
        proposed = dict(base)
        proposed['name'] = 'Legacy correction'
        obj = PartyVersionRequest(quote=self.quote, initiator=self.initiator,
            base_snapshot=base, proposed_snapshot=proposed, base_fingerprint=_digest(base),
            change_type='correction', reason='Legacy reason', evidence='Legacy source', source_trust='unknown')
        obj.content_fingerprint = _digest(_content(obj))
        obj.save(force_insert=True)
        return obj

    def test_legacy_quote_basis_approval_and_verification_preserve_fingerprints(self):
        obj = self._legacy_quote_request()
        original = (obj.base_snapshot.copy(), obj.base_fingerprint, obj.content_fingerprint)
        decision = approve(request=self.b, request_id=obj.pk,
            expected_content_fingerprint=obj.content_fingerprint, note='Reviewed')
        self.assertEqual(decision.approver_id, self.approver.pk)
        self.assertNotEqual(decision.approver_id, obj.initiator_id)
        verified = verified_approval(request=self.a, request_id=obj.pk)
        self.assertEqual(verified.pk, decision.pk)
        saved = PartyVersionRequest.objects.get(pk=obj.pk)
        self.assertEqual((saved.base_snapshot, saved.base_fingerprint, saved.content_fingerprint), original)
        self.assertNotIn('tax_id', saved.base_snapshot)
        self.assertNotIn('tax_id', saved.proposed_snapshot)
        self.assertEqual(decision.approved_fingerprint, original[2])

    def test_legacy_basis_requires_tax_id_still_unknown_for_approval_and_verification(self):
        obj = self._legacy_quote_request()
        self.assertIsNone(Quote.objects.get(pk=self.quote.pk).buyer_tax_id)
        original = (obj.base_snapshot.copy(), obj.base_fingerprint, obj.content_fingerprint)
        for value in ('TAX-123', ''):
            with self.subTest(stage='approve', tax_id=value):
                Quote.objects.filter(pk=self.quote.pk).update(buyer_tax_id=value)
                with self.assertRaisesMessage(ValidationError, '基准快照已变更'):
                    approve(request=self.b, request_id=obj.pk,
                        expected_content_fingerprint=obj.content_fingerprint, note='Reviewed')
                self.assertFalse(PartyVersionApproval.objects.filter(request=obj).exists())
        Quote.objects.filter(pk=self.quote.pk).update(buyer_tax_id=None)
        approve(request=self.b, request_id=obj.pk,
            expected_content_fingerprint=obj.content_fingerprint, note='Reviewed')
        self.assertEqual(verified_approval(request=self.a, request_id=obj.pk).request_id, obj.pk)
        for value in ('TAX-123', ''):
            with self.subTest(stage='verify', tax_id=value):
                Quote.objects.filter(pk=self.quote.pk).update(buyer_tax_id=value)
                with self.assertRaisesMessage(ValidationError, '基准快照已变更'):
                    verified_approval(request=self.a, request_id=obj.pk)
        saved = PartyVersionRequest.objects.get(pk=obj.pk)
        self.assertEqual((saved.base_snapshot, saved.base_fingerprint, saved.content_fingerprint), original)

    def test_legacy_quote_basis_rejects_changed_target_at_both_stages(self):
        obj = self._legacy_quote_request()
        Quote.objects.filter(pk=self.quote.pk).update(buyer_address='Changed')
        with self.assertRaisesMessage(ValidationError, '基准快照已变更'):
            approve(request=self.b, request_id=obj.pk,
                expected_content_fingerprint=obj.content_fingerprint, note='Reviewed')
        self.assertFalse(PartyVersionApproval.objects.filter(request=obj).exists())
        Quote.objects.filter(pk=self.quote.pk).update(buyer_address=obj.base_snapshot['address'])
        approve(request=self.b, request_id=obj.pk,
            expected_content_fingerprint=obj.content_fingerprint, note='Reviewed')
        Quote.objects.filter(pk=self.quote.pk).update(buyer_address='Changed again')
        with self.assertRaisesMessage(ValidationError, '基准快照已变更'):
            verified_approval(request=self.a, request_id=obj.pk)

    def test_legacy_quote_invalid_field_sets_rejected_at_both_stages(self):
        cases = (lambda base: {k: v for k, v in base.items() if k != 'country'},
                 lambda base: {**base, 'unexpected': 'value'})
        for make_invalid in cases:
            with self.subTest(case=make_invalid):
                obj = self._legacy_quote_request(base_snapshot=make_invalid)
                with self.assertRaisesMessage(ValidationError, '基准快照字段无效'):
                    approve(request=self.b, request_id=obj.pk,
                        expected_content_fingerprint=obj.content_fingerprint, note='Reviewed')
                # Isolated-test fault fixture: an existing approval does not make
                # an invalid saved field set acceptable to the read-side verifier.
                PartyVersionApproval.objects.create(request=obj, approver=self.approver,
                    approved_fingerprint=obj.content_fingerprint, note='Synthetic')
                with self.assertRaisesMessage(ValidationError, '基准快照字段无效'):
                    verified_approval(request=self.a, request_id=obj.pk)

    def test_approval_rejects_tampered_persisted_request_content(self):
        obj = self.make()
        original_snapshot = obj.proposed_snapshot.copy()
        tampered_snapshot = {**original_snapshot, 'name': 'Tampered party'}
        for field, original, tampered in (
            ('reason', obj.reason, 'Tampered reason'),
            ('evidence', obj.evidence, 'Tampered evidence'),
            ('proposed_snapshot', json.dumps(original_snapshot), json.dumps(tampered_snapshot)),
        ):
            with self.subTest(field=field):
                self._inject_request_field(obj, field, tampered)
                with self.assertRaisesMessage(ValidationError, '申请内容指纹不一致'):
                    approve(request=self.b, request_id=obj.pk,
                        expected_content_fingerprint=obj.content_fingerprint, note='Review')
                self.assertFalse(PartyVersionApproval.objects.filter(request=obj).exists())
                self._inject_request_field(obj, field, original)
        decision = approve(request=self.b, request_id=obj.pk,
            expected_content_fingerprint=obj.content_fingerprint, note='Review')
        self.assertEqual(decision.approved_fingerprint, obj.content_fingerprint)

    def test_verified_approval_rejects_tampered_request(self):
        obj = self.make()
        decision = approve(request=self.b, request_id=obj.pk,
            expected_content_fingerprint=obj.content_fingerprint, note='Review')
        verified = verified_approval(request=self.a, request_id=obj.pk)
        self.assertEqual(verified.pk, decision.pk)
        self.assertEqual(verified.request.reason, obj.reason)
        self._inject_request_field(obj, 'reason', 'Tampered after approval')
        # Direct ORM access is not a verification boundary.
        self.assertEqual(PartyVersionRequest.objects.get(pk=obj.pk).reason, 'Tampered after approval')
        with self.assertRaisesMessage(ValidationError, '批准内容指纹不一致'):
            verified_approval(request=self.a, request_id=obj.pk)
        self.assertEqual(PartyVersionApproval.objects.filter(request=obj).count(), 1)

    def test_verified_approval_rejects_unapproved_and_tampered_approval(self):
        obj = self.make()
        with self.assertRaisesMessage(ValidationError, '申请尚未批准'):
            verified_approval(request=self.a, request_id=obj.pk)
        decision = approve(request=self.b, request_id=obj.pk,
            expected_content_fingerprint=obj.content_fingerprint, note='Review')
        table = connection.ops.quote_name(PartyVersionApproval._meta.db_table)
        with connection.cursor() as cursor:
            cursor.execute(f'UPDATE {table} SET approved_fingerprint = %s WHERE id = %s', ['0' * 64, decision.pk])
            self.assertEqual(cursor.rowcount, 1)
        with self.assertRaisesMessage(ValidationError, '批准内容指纹不一致'):
            verified_approval(request=self.a, request_id=obj.pk)

    def test_verified_approval_rejects_changed_target_and_session(self):
        obj = self.make()
        approve(request=self.b, request_id=obj.pk,
            expected_content_fingerprint=obj.content_fingerprint, note='Review')
        anonymous = RequestFactory().get('/')
        anonymous.user = self.initiator
        with self.assertRaises(ValidationError):
            verified_approval(request=anonymous, request_id=obj.pk)
        Quote.objects.filter(pk=self.quote.pk).update(buyer_address='Changed after approval')
        with self.assertRaisesMessage(ValidationError, '基准快照已变更'):
            verified_approval(request=self.a, request_id=obj.pk)

    @override_settings(RBAC_ENFORCEMENT=True, DEVELOPMENT_SUPERADMIN=False)
    def test_session_permissions_and_customer_scope_for_all_entrypoints(self):
        unit = OrganizationUnit.objects.create(name='Test unit', code='PV-UNIT')
        position = Position.objects.create(unit=unit, name='Test position', code='PV-POS')
        role = AccessRole.objects.create(name='Party test', code='PV-ROLE', default_data_scope='all')
        for user in (self.initiator, self.approver):
            profile = EmployeeProfile.objects.create(user=user, display_name=user.username, unit=unit, position=position)
            profile.roles.add(role)
        permissions = {}
        for module in ('quotes', 'orders', 'customers', 'purchases', 'suppliers'):
            permissions[module] = RolePermission.objects.create(role=role, module=module, can_view=True, can_update=True)

        for kind, target, module, related in [
            ('quote', self.quote, 'quotes', 'customers'),
            ('order', self.order, 'orders', 'customers'),
            ('purchase_order', self.purchase, 'purchases', 'suppliers'),
        ]:
            with self.subTest(kind=kind):
                initial = baseline(request=self.a, target_type=kind, target_id=target.pk)
                changed = {key: value if value is not None else '' for key, value in initial['snapshot'].items()}
                changed['name'] = 'Updated party'
                args = dict(request=self.a, target_type=kind, target_id=target.pk,
                    expected_base_fingerprint=initial['fingerprint'], proposed_snapshot=changed,
                    change_type='correction', reason='Reason', evidence='Evidence', source_trust='unknown')
                for denied_module in (module, related):
                    row = permissions[denied_module]
                    row.can_view = False
                    row.save(update_fields=['can_view'])
                    with self.assertRaises(PermissionDenied):
                        baseline(request=self.a, target_type=kind, target_id=target.pk)
                    with self.assertRaises(PermissionDenied):
                        propose(**args)
                    row.can_view = True
                    row.save(update_fields=['can_view'])
                permissions[module].can_update = False
                permissions[module].save(update_fields=['can_update'])
                self.assertEqual(initial, baseline(request=self.a, target_type=kind, target_id=target.pk))
                with self.assertRaises(PermissionDenied):
                    propose(**args)
                permissions[module].can_update = True
                permissions[module].save(update_fields=['can_update'])
                obj = propose(**args)
                for denied_module, field in ((module, 'can_view'), (related, 'can_view'), (module, 'can_update')):
                    row = permissions[denied_module]
                    setattr(row, field, False)
                    row.save(update_fields=[field])
                    with self.assertRaises(PermissionDenied):
                        approve(request=self.b, request_id=obj.pk, expected_content_fingerprint=obj.content_fingerprint, note='Checked')
                    setattr(row, field, True)
                    row.save(update_fields=[field])
                if kind != 'purchase_order':
                    role.default_data_scope = 'self'
                    role.save(update_fields=['default_data_scope'])
                    with self.assertRaises(PermissionDenied):
                        baseline(request=self.a, target_type=kind, target_id=target.pk)
                    with self.assertRaises(PermissionDenied):
                        propose(**args)
                    with self.assertRaises(PermissionDenied):
                        approve(request=self.b, request_id=obj.pk, expected_content_fingerprint=obj.content_fingerprint, note='Checked')
                    role.default_data_scope = 'all'
                    role.save(update_fields=['default_data_scope'])
                self.assertFalse(PartyVersionApproval.objects.filter(request=obj).exists())
                approve(request=self.b, request_id=obj.pk, expected_content_fingerprint=obj.content_fingerprint, note='Checked')
                verified_approval(request=self.b, request_id=obj.pk)
                permissions[module].can_update = False
                permissions[module].save(update_fields=['can_update'])
                verified_approval(request=self.b, request_id=obj.pk)
                permissions[module].can_update = True
                permissions[module].save(update_fields=['can_update'])
                for denied_module in (module, related):
                    row = permissions[denied_module]
                    row.can_view = False
                    row.save(update_fields=['can_view'])
                    with self.assertRaises(PermissionDenied):
                        verified_approval(request=self.b, request_id=obj.pk)
                    row.can_view = True
                    row.save(update_fields=['can_view'])
                if kind != 'purchase_order':
                    role.default_data_scope = 'self'
                    role.save(update_fields=['default_data_scope'])
                    with self.assertRaises(PermissionDenied):
                        verified_approval(request=self.b, request_id=obj.pk)
                    role.default_data_scope = 'all'
                    role.save(update_fields=['default_data_scope'])

    def test_replacement_proposal_and_independent_approval_do_not_replace_party(self):
        original = baseline(request=self.a, target_type='quote', target_id=self.quote.pk)
        obj = self.make(change_type='replacement')
        self.assertEqual(obj.change_type, 'replacement')
        self.assertEqual(obj.initiator_id, self.initiator.pk)
        decision = approve(request=self.b, request_id=obj.pk,
            expected_content_fingerprint=obj.content_fingerprint, note='Review replacement proposal')
        self.assertEqual(decision.approver_id, self.approver.pk)
        self.assertNotEqual(decision.approver_id, obj.initiator_id)
        self.assertEqual(verified_approval(request=self.b, request_id=obj.pk).pk, decision.pk)
        # This only records a proposal and approval; no legal party replacement is applied.
        self.assertEqual(baseline(request=self.a, target_type='quote', target_id=self.quote.pk), original)
