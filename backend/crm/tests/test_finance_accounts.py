from django.db import IntegrityError, transaction
from django.test import TestCase

from crm.models import FinanceAccount


class FinanceAccountTests(TestCase):
    def test_display_name_does_not_establish_ownership(self):
        account = FinanceAccount.objects.create(code="SYNTH-BANK", name="公司银行账户", account_type="bank")
        self.assertEqual(account.ownership, "unverified")

    def test_confirmed_ownership_requires_basis(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            FinanceAccount.objects.create(code="SYNTH-OWN", name="Synthetic", account_type="bank", ownership="own")
        account = FinanceAccount.objects.create(code="SYNTH-CASH", name="Synthetic", account_type="cash", ownership="own", ownership_reason="Synthetic account verification")
        self.assertEqual(account.account_type, "cash")

    def test_invalid_type_and_duplicate_identity_are_rejected(self):
        FinanceAccount.objects.create(code="SYNTH-A", name="Synthetic", account_type="bank")
        with self.assertRaises(IntegrityError), transaction.atomic():
            FinanceAccount.objects.create(code="SYNTH-A", name="Different label", account_type="cash")
        with self.assertRaises(IntegrityError), transaction.atomic():
            FinanceAccount.objects.create(code="SYNTH-B", name="Synthetic", account_type="other")
