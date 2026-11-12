"""Prepare pending party requests from a synthetic fixture-only principal."""
from datetime import date
import json

import django

django.setup()

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, RequestFactory
from crm.models import Customer, Product, Quote, SKU
from crm.party_version import baseline, propose
from crm.quote_snapshots import create_quote_items
from test_support.isolated_runtime import verify_isolated_runtime

verify_isolated_runtime(settings=settings, database_must_exist=True)
maker = get_user_model().objects.create_user(username="q6-fixture-proposer")
client = Client()
client.force_login(maker)
session = RequestFactory().post("/")
session.session = client.session

customer = Customer.objects.create(code="Q6-PARTY-BUYER", name="Q6 Party Buyer", country="Germany")
target = Customer.objects.create(code="Q6-PARTY-TARGET", name="Q6 Replacement Buyer", country="France")
product = Product.objects.create(code="Q6-PARTY-PRODUCT", name="Q6 Party Lamp")
sku = SKU.objects.create(product=product, sku="Q6-PARTY-SKU", sales_model="Q6-PARTY-MODEL", unit="pcs")
cases = []
for index in range(6):
    fixtures = {}
    for action in ("reject", "apply", "invalidate", "replace"):
        if index not in (0, 3) and action in ("reject", "replace"):
            continue
        quote = Quote.objects.create(
            quote_no=f"Q6-PARTY-{action.upper()}-{index}", customer=customer, quote_date=date.today(),
            status="sent", buyer_company_name=customer.name, buyer_country_snapshot="Germany", buyer_tax_id="",
        )
        create_quote_items(quote, [{"sku": sku, "quantity": 1, "unit_price": 10}])
        original = baseline(request=session, target_type="quote", target_id=quote.pk)
        snapshot = {**original["snapshot"], "address": "Q6 approved address"}
        if action == "replace":
            snapshot.update(name=target.name, country="France")
        proposal = propose(
            request=session, target_type="quote", target_id=quote.pk,
            expected_base_fingerprint=original["fingerprint"], proposed_snapshot=snapshot,
            change_type="replacement" if action == "replace" else "correction",
            replacement_target_id=target.pk if action == "replace" else None,
            reason="Q6 synthetic review", evidence="Q6 fixture evidence", source_trust="unverified",
        )
        fixtures[action] = {"quote": quote.pk, "proposal": proposal.pk}
    cases.append(fixtures)
print(json.dumps({"cases": cases, "sku": sku.pk, "target": target.pk}))
