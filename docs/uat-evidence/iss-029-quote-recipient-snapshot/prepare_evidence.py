"""Prepare synthetic data only in an explicitly selected ISS-029 SQLite."""
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
database_url = os.environ.get("DATABASE_URL", "")
if not database_url.startswith("sqlite:///") or not database_url.endswith("iss029-recipient-evidence.sqlite3"):
    raise RuntimeError("An explicitly selected ISS-029 isolated SQLite database is required")
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

from django.core.management import call_command
from crm.models import Contact, Customer, Product, SKU

call_command("migrate", interactive=False, verbosity=0)
customer, _ = Customer.objects.get_or_create(code="ISS029-EVIDENCE", defaults={
    "name": "ISS029 Snapshot Buyer", "country": "Germany", "address": "Original Berlin Address"})
contact, _ = Contact.objects.get_or_create(customer=customer, name="Original Primary", defaults={
    "email": "primary@example.com", "phone": "+49 111", "is_primary": True})
product, _ = Product.objects.get_or_create(code="ISS029-P", defaults={"name": "ISS029 Panel"})
sku, _ = SKU.objects.get_or_create(sku="ISS029-SKU", defaults={"product": product,
    "sales_model": "SJ-029", "unit": "pcs", "default_price": "10.00"})
out = Path(__file__).resolve().parent
(out / "fixture.json").write_text(json.dumps({"customer": customer.pk, "contact": contact.pk,
    "sku": sku.pk, "database": database_url, "development_identity": True}, indent=2), encoding="utf-8")
print(json.dumps({"customer": customer.pk, "contact": contact.pk, "sku": sku.pk}))
