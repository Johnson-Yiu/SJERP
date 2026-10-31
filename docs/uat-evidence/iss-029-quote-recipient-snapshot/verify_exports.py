"""Read and reconcile the actual browser downloads with saved DB versions."""
import hashlib
import json
import os
from pathlib import Path
import sys

out = Path(__file__).resolve().parent
fixture = json.loads((out / "fixture.json").read_text(encoding="utf-8"))
api = json.loads((out / "api-evidence.json").read_text(encoding="utf-8"))
if not fixture["database"].endswith("iss029-recipient-evidence.sqlite3"):
    raise RuntimeError("Dedicated evidence database required")
os.environ["DATABASE_URL"] = fixture["database"]
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
sys.path.insert(0, str(out.parents[2] / "backend"))
import django
django.setup()
from crm.models import Contact, Customer, Quote
from openpyxl import load_workbook

versions = {}
for key in ("a", "b"):
    quote = Quote.objects.get(pk=api[key])
    versions[key] = {field: getattr(quote, field) for field in (
        "id", "quote_no", "status", "recipient_name", "buyer_email", "buyer_phone", "buyer_address", "revision_summary")}
checks = []
for name, key in (("version-a.xlsx", "a"), ("version-b-empty-email.xlsx", "b"), ("version-b-with-unsaved-input.xlsx", "b")):
    file = out / name
    sheet = load_workbook(file)["PI"]
    quote = versions[key]
    for cell, field in (("B4", "recipient_name"), ("B5", "buyer_address"), ("B7", "buyer_email"), ("B8", "buyer_phone")):
        assert (sheet[cell].value or "") == quote[field], (name, cell, sheet[cell].value, quote[field])
    assert sheet["L9"].value == quote["quote_no"]
    text = "\n".join(str(cell.value or "") for row in sheet for cell in row)
    assert "changed-master@example.com" not in text
    assert "unsaved@example.com" not in text
    checks.append({"file": name, "bytes": file.stat().st_size, "sha256": hashlib.sha256(file.read_bytes()).hexdigest(),
                   "quote_id": quote["id"], "recipient_cells_match_database": True, "sheets": sheet.parent.sheetnames})
master = Contact.objects.get(pk=fixture["contact"])
result = {"versions": versions, "current_contact": {"name": master.name, "email": master.email, "phone": master.phone},
    "current_customer_address": Customer.objects.get(pk=fixture["customer"]).address, "downloads": checks,
    "scope": "Synthetic isolated SQLite; actual Chrome downloads from Django API; no production or Microsoft Excel application claim"}
(out / "export-reconciliation.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))
