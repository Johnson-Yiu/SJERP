"""Cross-migration rollback must stop before discarding protected party facts."""
from datetime import date

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.recorder import MigrationRecorder
from django.test import TransactionTestCase


class PartyQuoteMigrationRollbackTests(TransactionTestCase):
    def test_empty_rollback_and_each_protected_fact_blocks_before_schema_changes(self):
        old = [('crm', '0108_history_append_only_truncate')]
        current = [('crm', '0112_party_quote_application')]
        try:
            # Empty state can cross the entire boundary in both directions.
            MigrationExecutor(connection).migrate(old)
            MigrationExecutor(connection).migrate(current)
            apps = MigrationExecutor(connection).loader.project_state(current).apps
            customer_model = apps.get_model('crm', 'Customer')
            quote_model = apps.get_model('crm', 'Quote')
            request_model = apps.get_model('crm', 'PartyVersionRequest')
            approval_model = apps.get_model('crm', 'PartyVersionApproval')
            application_model = apps.get_model('crm', 'PartyQuoteApplication')
            user_model = apps.get_model('auth', 'User')
            customer = customer_model.objects.create(code='APM-C', name='Migration customer')
            quote = quote_model.objects.create(quote_no='APM-Q', customer_id=customer.pk,
                quote_date=date(2026, 1, 1), buyer_country_snapshot=None, buyer_tax_id=None)
            user = user_model.objects.create(username='migration-synthetic-user')

            def state():
                names = [quote_model._meta.db_table, request_model._meta.db_table,
                         approval_model._meta.db_table, application_model._meta.db_table]
                with connection.cursor() as cursor:
                    tables = set(connection.introspection.table_names(cursor))
                    columns = {name: tuple(c.name for c in connection.introspection.get_table_description(cursor, name))
                               for name in names if name in tables}
                return tables, columns, set(MigrationRecorder(connection).applied_migrations())

            def rejected():
                before = state()
                with self.assertRaises(RuntimeError):
                    MigrationExecutor(connection).migrate(old)
                self.assertEqual(state(), before)

            for field, value in (('buyer_country_snapshot', 'Germany'), ('buyer_country_snapshot', ''),
                                 ('buyer_tax_id', 'TAX-1'), ('buyer_tax_id', '')):
                with self.subTest(field=field, value=value):
                    quote_model.objects.filter(pk=quote.pk).update(**{field: value})
                    rejected()
                    self.assertEqual(quote_model.objects.values_list(field, flat=True).get(pk=quote.pk), value)
                    quote_model.objects.filter(pk=quote.pk).update(**{field: None})

            def new_request(**extra):
                return request_model.objects.create(quote_id=quote.pk, initiator_id=user.pk,
                    base_snapshot={}, proposed_snapshot={}, base_fingerprint='b' * 64,
                    content_fingerprint='c' * 64, change_type='correction', reason='Synthetic',
                    evidence='Synthetic', source_trust='unknown', **extra)

            for extra in ({}, {'quote_customer_id': customer.pk}, {'source_document_fingerprint': 'd' * 64}):
                with self.subTest(request_fields=extra):
                    req = new_request(**extra)
                    rejected()
                    self.assertTrue(request_model.objects.filter(pk=req.pk).exists())
                    request_model.objects.filter(pk=req.pk).delete()
            req = new_request()
            decision = approval_model.objects.create(request_id=req.pk, approver_id=user.pk,
                approved_fingerprint='c' * 64, note='Synthetic')
            rejected()
            self.assertTrue(approval_model.objects.filter(pk=decision.pk).exists())
            # Keep this last: the production PostgreSQL trigger protects application rows.
            result = quote_model.objects.create(quote_no='APM-RESULT', customer_id=customer.pk,
                quote_date=date(2026, 1, 1), buyer_country_snapshot=None, buyer_tax_id=None)
            application = application_model.objects.create(approval_id=decision.pk, source_quote_id=quote.pk,
                result_quote_id=result.pk, applied_by_id=user.pk, approved_fingerprint='c' * 64,
                approval_attestation_fingerprint='a' * 64, source_fingerprint='d' * 64,
                revision_fingerprint='e' * 64, application_fingerprint='f' * 64)
            rejected()
            self.assertTrue(application_model.objects.filter(pk=application.pk).exists())
        finally:
            executor = MigrationExecutor(connection)
            executor.migrate(executor.loader.graph.leaf_nodes())
