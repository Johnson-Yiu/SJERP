from datetime import date

from django.test import TestCase

from crm.models import Customer, Quote
from crm.quote_numbers import allocate_revision_quote_no


class QuoteRevisionTreeNumberTests(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create(code="C-TREE", name="Tree Buyer", country="Germany")
        self.root = Quote.objects.create(quote_no="SJ20260901DE001", customer=self.customer, quote_date=date(2026, 9, 1))

    def create_revision(self, parent):
        quote_no, revision_no = allocate_revision_quote_no(parent)
        return Quote.objects.create(
            quote_no=quote_no,
            customer=self.customer,
            quote_date=self.root.quote_date,
            root_quote=self.root,
            parent_quote=parent,
            revision_no=revision_no,
        )

    def test_numbering_follows_the_direct_parent_branch(self):
        first = self.create_revision(self.root)
        nested_first = self.create_revision(first)
        nested_second = self.create_revision(first)
        root_second = self.create_revision(self.root)

        self.assertEqual(first.quote_no, "SJ20260901DE001-1")
        self.assertEqual(nested_first.quote_no, "SJ20260901DE001-1-1")
        self.assertEqual(nested_second.quote_no, "SJ20260901DE001-1-2")
        self.assertEqual(root_second.quote_no, "SJ20260901DE001-2")
        self.assertEqual([first.revision_no, nested_first.revision_no, nested_second.revision_no, root_second.revision_no], [1, 2, 3, 4])
