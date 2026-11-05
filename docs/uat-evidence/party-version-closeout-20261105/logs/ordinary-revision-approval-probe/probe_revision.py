"""Synthetic in-process APIClient probe; no network HTTP or browser."""
import hashlib
import json
from pathlib import Path

from crm.models import PartyVersionApproval, PartyVersionRequest, Quote
from crm.tests.test_quote_buyer_tax_id import QuoteBuyerTaxTests


class OrdinaryRevisionApprovalProbe(QuoteBuyerTaxTests):
    def test_sent_quote_party_revision(self):
        root = Path(__file__).resolve().parents[5]
        print("\nTRANSPORT=in-process Django REST framework APIClient; no real HTTP/browser", flush=True)
        for path in ("backend/crm/views.py", "backend/crm/serializers.py", "backend/crm/party_version.py"):
            print(f"SHA256 {path} {hashlib.sha256((root / path).read_bytes()).hexdigest()}", flush=True)
        payload = {
            "customer": self.customer.pk, "quote_date": "2026-11-05", "currency": "USD",
            "buyer_address": "Synthetic address A", "recipient_name": "Synthetic recipient A",
            "buyer_email": "a@example.invalid", "buyer_phone": "000-A",
            "items": [{"sku": self.sku.pk, "quantity": "1", "unit_price": "10"}],
        }
        original = self.client.post("/api/quotes/", payload, format="json")
        print(f"POST /api/quotes/ HTTP {original.status_code}", flush=True)
        self.assertEqual(original.status_code, 201, original.data)
        quote_id = original.data["id"]
        sent = self.client.post(f"/api/quotes/{quote_id}/mark-sent/", {}, format="json")
        print(f"POST /api/quotes/{quote_id}/mark-sent/ HTTP {sent.status_code}", flush=True)
        self.assertEqual(sent.status_code, 200, sent.data)
        revision = self.client.post(f"/api/quotes/{quote_id}/revise/", {
            "revision_summary": "Synthetic address and contact change",
            "buyer_address": "Synthetic address B", "recipient_name": "Synthetic recipient B",
            "buyer_email": "b@example.invalid", "buyer_phone": "000-B",
        }, format="json")
        print(f"POST /api/quotes/{quote_id}/revise/ HTTP {revision.status_code}", flush=True)
        if revision.status_code != 201:
            print("REVISION_RESPONSE " + json.dumps(revision.data, ensure_ascii=False, default=str), flush=True)
            self.fail("Ordinary revision did not create a version; see response above")
        revision_id = revision.data["id"]
        print("REVISION_VALUES " + json.dumps({key: revision.data[key] for key in (
            "status", "buyer_address", "recipient_name", "buyer_email", "buyer_phone")}, ensure_ascii=False), flush=True)
        result = self.client.post(f"/api/quotes/{revision_id}/mark-sent/", {}, format="json")
        print(f"POST /api/quotes/{revision_id}/mark-sent/ HTTP {result.status_code}", flush=True)
        if result.status_code != 200:
            print("SEND_RESPONSE " + json.dumps(result.data, ensure_ascii=False, default=str), flush=True)
        source = Quote.objects.get(pk=quote_id)
        child = Quote.objects.get(pk=revision_id)
        counts = {"requests": PartyVersionRequest.objects.count(), "approvals": PartyVersionApproval.objects.count()}
        print("SOURCE " + json.dumps({"status": source.status, "address": source.buyer_address, "recipient": source.recipient_name}), flush=True)
        print("CHILD " + json.dumps({"status": child.status, "address": child.buyer_address, "recipient": child.recipient_name, "parent_id": child.parent_quote_id}), flush=True)
        print("PARTY_APPROVAL_COUNTS " + json.dumps(counts), flush=True)
        self.assertEqual(result.status_code, 200, result.data)
        self.assertEqual((source.status, source.buyer_address, source.recipient_name), ("sent", "Synthetic address A", "Synthetic recipient A"))
        self.assertEqual((child.status, child.buyer_address, child.recipient_name), ("sent", "Synthetic address B", "Synthetic recipient B"))
        self.assertEqual(counts, {"requests": 0, "approvals": 0})
