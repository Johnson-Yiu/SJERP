"""0113 must fail before downgrading any protected earlier party facts."""
from datetime import date
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.recorder import MigrationRecorder
from django.test import TransactionTestCase


class PartyLifecycleMigrationTests(TransactionTestCase):
    def test_cross_chain_preflight_and_empty_rollback(self):
        old = [('crm', '0108_history_append_only_truncate')]
        current = [('crm', '0113_party_request_lifecycle')]
        try:
            MigrationExecutor(connection).migrate(old)
            MigrationExecutor(connection).migrate(current)
            apps = MigrationExecutor(connection).loader.project_state(current).apps
            Customer = apps.get_model('crm', 'Customer'); Quote = apps.get_model('crm', 'Quote')
            Request = apps.get_model('crm', 'PartyVersionRequest'); Approval = apps.get_model('crm', 'PartyVersionApproval')
            Application = apps.get_model('crm', 'PartyQuoteApplication'); Event = apps.get_model('crm', 'PartyVersionTerminalEvent')
            User = apps.get_model('auth', 'User')
            customer = Customer.objects.create(code='PLM-C', name='Synthetic lifecycle customer')
            quote = Quote.objects.create(quote_no='PLM-Q', customer_id=customer.pk, quote_date=date(2026, 1, 1),
                buyer_country_snapshot=None, buyer_tax_id=None)
            user = User.objects.create(username='lifecycle-migration-synthetic')
            def state():
                names = [Quote._meta.db_table, Request._meta.db_table, Approval._meta.db_table,
                         Application._meta.db_table, Event._meta.db_table]
                with connection.cursor() as cursor:
                    tables = set(connection.introspection.table_names(cursor))
                    columns = {name: tuple(c.name for c in connection.introspection.get_table_description(cursor, name))
                               for name in names if name in tables}
                return tables, columns, set(MigrationRecorder(connection).applied_migrations())
            def blocked():
                prior = state()
                with self.assertRaises(RuntimeError):
                    MigrationExecutor(connection).migrate(old)
                self.assertEqual(prior, state())
            for field, value in [('buyer_country_snapshot', ''), ('buyer_country_snapshot', 'Germany'),
                                 ('buyer_tax_id', ''), ('buyer_tax_id', 'TAX')]:
                with self.subTest(field=field, value=value):
                    Quote.objects.filter(pk=quote.pk).update(**{field: value})
                    blocked()
                    self.assertEqual(Quote.objects.values_list(field, flat=True).get(pk=quote.pk), value)
                    Quote.objects.filter(pk=quote.pk).update(**{field: None})
            req = Request.objects.create(quote_id=quote.pk, initiator_id=user.pk, base_snapshot={}, proposed_snapshot={},
                base_fingerprint='b'*64, content_fingerprint='c'*64, change_type='correction', reason='r', evidence='e', source_trust='unknown')
            blocked(); self.assertTrue(Request.objects.filter(pk=req.pk).exists())
            decision = Approval.objects.create(request_id=req.pk, approver_id=user.pk, approved_fingerprint='c'*64, note='n')
            blocked(); self.assertTrue(Approval.objects.filter(pk=decision.pk).exists())
            result = Quote.objects.create(quote_no='PLM-R', customer_id=customer.pk, quote_date=date(2026, 1, 1),
                buyer_country_snapshot=None, buyer_tax_id=None)
            app = Application.objects.create(approval_id=decision.pk, source_quote_id=quote.pk, result_quote_id=result.pk,
                applied_by_id=user.pk, approved_fingerprint='c'*64, approval_attestation_fingerprint='a'*64,
                source_fingerprint='d'*64, revision_fingerprint='e'*64, application_fingerprint='f'*64)
            blocked(); self.assertTrue(Application.objects.filter(pk=app.pk).exists())
            event = Event.objects.create(request_id=req.pk, actor_id=user.pk, kind='invalidated', note='n', request_fingerprint='c'*64)
            blocked(); self.assertTrue(Event.objects.filter(pk=event.pk).exists())
        finally:
            executor = MigrationExecutor(connection)
            executor.migrate(executor.loader.graph.leaf_nodes())

    def test_legacy_ambiguous_active_requests_refuse_upgrade_without_schema_change(self):
        before = [('crm', '0112_party_quote_application')]
        after = [('crm', '0113_party_request_lifecycle')]
        try:
            MigrationExecutor(connection).migrate(before)
            apps = MigrationExecutor(connection).loader.project_state(before).apps
            Customer = apps.get_model('crm', 'Customer'); Quote = apps.get_model('crm', 'Quote')
            Request = apps.get_model('crm', 'PartyVersionRequest'); User = apps.get_model('auth', 'User')
            customer = Customer.objects.create(code='PLM-DUP', name='Synthetic duplicate')
            quote = Quote.objects.create(quote_no='PLM-DUP-Q', customer_id=customer.pk,
                quote_date=date(2026, 1, 1), buyer_country_snapshot=None, buyer_tax_id=None)
            user = User.objects.create(username='lifecycle-migration-duplicate')
            for token in ('a', 'b'):
                Request.objects.create(quote_id=quote.pk, initiator_id=user.pk, base_snapshot={}, proposed_snapshot={},
                    base_fingerprint=token*64, content_fingerprint='c'*64, change_type='correction', reason='r', evidence='e', source_trust='unknown')
            before_set = set(MigrationRecorder(connection).applied_migrations())
            with connection.cursor() as cursor:
                before_cols = tuple(c.name for c in connection.introspection.get_table_description(cursor, Request._meta.db_table))
            with self.assertRaisesMessage(RuntimeError, '多个未应用主体申请'):
                MigrationExecutor(connection).migrate(after)
            self.assertEqual(before_set, set(MigrationRecorder(connection).applied_migrations()))
            with connection.cursor() as cursor:
                self.assertEqual(before_cols, tuple(c.name for c in connection.introspection.get_table_description(cursor, Request._meta.db_table)))
            self.assertEqual(Request.objects.filter(quote_id=quote.pk).count(), 2)
            # Fixture cleanup only in the disposable test database, so other tests can migrate.
            Request.objects.filter(quote_id=quote.pk).delete()
        finally:
            executor = MigrationExecutor(connection)
            executor.migrate(executor.loader.graph.leaf_nodes())

    def test_existing_applied_approval_keeps_history_and_does_not_block_new_active(self):
        old = [('crm', '0112_party_quote_application')]
        new = [('crm', '0113_party_request_lifecycle')]
        try:
            MigrationExecutor(connection).migrate(old)
            apps = MigrationExecutor(connection).loader.project_state(old).apps
            Customer = apps.get_model('crm', 'Customer'); Quote = apps.get_model('crm', 'Quote')
            Request = apps.get_model('crm', 'PartyVersionRequest'); Approval = apps.get_model('crm', 'PartyVersionApproval')
            Application = apps.get_model('crm', 'PartyQuoteApplication'); User = apps.get_model('auth', 'User')
            customer = Customer.objects.create(code='PLM-OLD', name='Synthetic existing application')
            source = Quote.objects.create(quote_no='PLM-OLD-Q', customer_id=customer.pk,
                quote_date=date(2026, 1, 1), buyer_country_snapshot=None, buyer_tax_id=None)
            result = Quote.objects.create(quote_no='PLM-OLD-R', customer_id=customer.pk,
                quote_date=date(2026, 1, 1), buyer_country_snapshot=None, buyer_tax_id=None)
            user = User.objects.create(username='lifecycle-migration-existing')
            req = Request.objects.create(quote_id=source.pk, initiator_id=user.pk, base_snapshot={}, proposed_snapshot={},
                base_fingerprint='b'*64, content_fingerprint='c'*64, change_type='correction', reason='r', evidence='e', source_trust='unknown')
            approval = Approval.objects.create(request_id=req.pk, approver_id=user.pk, approved_fingerprint='c'*64, note='n')
            app = Application.objects.create(approval_id=approval.pk, source_quote_id=source.pk, result_quote_id=result.pk,
                applied_by_id=user.pk, approved_fingerprint='c'*64, approval_attestation_fingerprint='a'*64,
                source_fingerprint='d'*64, revision_fingerprint='e'*64, application_fingerprint='f'*64)
            MigrationExecutor(connection).migrate(new)
            newer = MigrationExecutor(connection).loader.project_state(new).apps
            saved = newer.get_model('crm', 'PartyVersionRequest').objects.get(pk=req.pk)
            self.assertFalse(saved.is_active)
            self.assertEqual(saved.content_fingerprint, 'c'*64)
            self.assertTrue(newer.get_model('crm', 'PartyQuoteApplication').objects.filter(pk=app.pk, approval_id=approval.pk).exists())
            self.assertFalse(newer.get_model('crm', 'PartyVersionTerminalEvent').objects.filter(request_id=req.pk).exists())
        finally:
            executor = MigrationExecutor(connection)
            executor.migrate(executor.loader.graph.leaf_nodes())
