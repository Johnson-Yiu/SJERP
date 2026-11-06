from unittest import skipUnless
from django.db import DatabaseError, connection, transaction
from django.test import TransactionTestCase
from crm.party_document_models import PartyDocumentVersion

@skipUnless(connection.vendor == 'postgresql', 'requires PostgreSQL')
class PartyDocumentVersionPostgresProtectionTests(TransactionTestCase):
    def test_truncate_is_denied_even_when_empty(self):
        table=connection.ops.quote_name(PartyDocumentVersion._meta.db_table)
        with self.assertRaises(DatabaseError):
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute('TRUNCATE TABLE '+table)
