from django.test import SimpleTestCase
from crm.views import finance_replay_with_current_scope


class FinanceReplayScopeTests(SimpleTestCase):
    def test_replay_keeps_original_amounts_but_removes_newly_inaccessible_relations(self):
        prior = {"id": 1, "customer": 10, "customer_name": "Customer", "amount": "100", "allocations": [
            {"id": 2, "order": 20, "contract_no": "VISIBLE", "amount": "60", "remaining_amount": "40"},
            {"id": 3, "order": 30, "contract_no": "PRIVATE", "amount": "40", "remaining_amount": "10"}],
            "writeoffs": [{"id": 4, "plan": 8, "contract_no": "PRIVATE", "amount": "2"}], "receipt_refunds": []}
        current = {"customer": None, "customer_name": "", "allocations": [
            {"id": 2, "order": None, "contract_no": "", "amount": "60", "remaining_amount": "0"}],
            "writeoffs": [], "receipt_refunds": []}
        result = finance_replay_with_current_scope(prior, current)
        self.assertIsNone(result["customer"])
        self.assertEqual(result["allocations"], [{"id": 2, "order": None, "contract_no": "", "amount": "60", "remaining_amount": "40"}])
        self.assertEqual(result["writeoffs"], [])
        self.assertEqual(result["amount"], "100")
