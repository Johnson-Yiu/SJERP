"""Seed only the explicitly named ISS-020 isolated SQLite evidence database."""
import io
import json
import os
from pathlib import Path

database_url = os.environ.get("DATABASE_URL", "")
if not database_url.startswith("sqlite:///") or not database_url.endswith("iss020-quote-export-evidence.sqlite3"):
    raise RuntimeError("An explicitly selected ISS-020 isolated SQLite database is required")

ROOT = Path(__file__).resolve().parents[3]
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import sys
sys.path.insert(0, str(ROOT / "backend"))
import django
django.setup()

from django.core.files.base import ContentFile
from django.core.management import call_command
from PIL import Image

from crm.models import Customer, Product, Quote, SKU
from crm.quote_snapshots import create_quote_items


def image_bytes(color):
    output = io.BytesIO()
    Image.new("RGB", (24, 24), color).save(output, format="PNG")
    return output.getvalue()


call_command("migrate", interactive=False, verbosity=0)
customer = Customer.objects.create(
    code="ISS020-EVIDENCE-CUSTOMER",
    name="ISS-020 Historical Buyer",
    country="Germany",
    address="Original Berlin Address",
)
product = Product.objects.create(code="ISS020-EVIDENCE-PRODUCT", name="ISS-020 Historical Product")
sku = SKU.objects.create(
    product=product,
    sku="ISS020-EVIDENCE-SKU",
    sales_model="ISS020-MODEL-HISTORICAL",
    unit="pcs",
    default_price="123.00",
)
sku.image.save("iss020-historical.png", ContentFile(image_bytes("red")), save=True)

root = Quote.objects.create(
    quote_no="ISS020-Q-A",
    customer=customer,
    buyer_company_name="ISS-020 Historical Buyer",
    recipient_name="Version A Recipient",
    buyer_address="Version A Address",
    buyer_email="version-a@example.com",
    buyer_phone="+49 111 A",
    quote_date="2026-10-26",
    valid_until="2026-11-25",
    currency="USD",
    shipping_fee="5.00",
    discount="1.00",
    deposit_ratio="0.3000",
    trading_terms="FOB Shenzhen",
    shipping_details="Sea freight",
    notes="Version A saved terms.",
    status="sent",
)
create_quote_items(root, [{
    "sku": sku, "quantity": "2.00", "unit_price": "123.00", "description": "Historical red-image panel",
}])

revision = Quote.objects.create(
    quote_no="ISS020-Q-A-1",
    root_quote=root,
    parent_quote=root,
    revision_no=1,
    revision_summary="Version B keeps the saved image and clears optional email",
    customer=customer,
    buyer_company_name=root.buyer_company_name,
    recipient_name="Version B Recipient",
    buyer_address="Version B Address",
    buyer_email="",
    buyer_phone="+49 222 B",
    quote_date=root.quote_date,
    valid_until=root.valid_until,
    currency="EUR",
    shipping_fee="0.00",
    discount="0.00",
    deposit_ratio="0.4000",
    trading_terms="CIF Hamburg",
    shipping_details="DHL air freight",
    notes="Version B saved terms.",
    status="draft",
)
create_quote_items(revision, [{
    "sku": sku, "quantity": "3.00", "unit_price": "82.50", "description": "Historical red-image panel, revision B",
}], source_items=list(root.items.all()))

# Change current masters after both revisions are saved. The quote item image
# and commercial fields must remain sourced from their saved snapshots.
customer.address = "Changed Current Master Address"
customer.name = "Changed Current Master Buyer"
customer.save(update_fields=["address", "name", "updated_at"])
sku.sales_model = "ISS020-MODEL-CURRENT"
sku.image.save("iss020-current.png", ContentFile(image_bytes("blue")), save=True)

incomplete = Quote.objects.create(
    quote_no="ISS020-Q-INCOMPLETE",
    customer=customer,
    buyer_company_name="Temporary Buyer",
    quote_date="2026-10-26",
    currency="USD",
)
create_quote_items(incomplete, [{
    "sku": sku, "quantity": "1.00", "unit_price": "10.00", "description": "Incomplete legacy row",
}])
Quote.objects.filter(pk=incomplete.pk).update(buyer_company_name="", currency="")

out = Path(__file__).resolve().parent
(out / "fixture.json").write_text(json.dumps({
    "database": database_url,
    "customer": customer.pk,
    "sku": sku.pk,
    "root_quote": root.pk,
    "revision_quote": revision.pk,
    "incomplete_quote": incomplete.pk,
    "root_quote_no": root.quote_no,
    "revision_quote_no": revision.quote_no,
    "development_identity": True,
}, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"root_quote": root.pk, "revision_quote": revision.pk, "incomplete_quote": incomplete.pk}, ensure_ascii=False))
