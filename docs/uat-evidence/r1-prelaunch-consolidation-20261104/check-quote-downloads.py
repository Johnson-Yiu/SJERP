"""Compare actual Chrome-downloaded synthetic XLSX files to saved API responses."""
import hashlib
import json
from pathlib import Path
from openpyxl import load_workbook

root = Path(__file__).resolve().parent / "closeout-logs" / "browser" / "iss029-recipient-snapshot.spec"
api = json.loads((root / "api-evidence.json").read_text(encoding="utf-8"))
versions = {}
for key in ("a", "b"):
    url = f"/quotes/{api[key]}/"
    rows = [r["body"] for r in api["records"] if r["method"] == "get" and r["url"] == url and r["status"] == 200]
    if len(rows) != 1:
        raise AssertionError(f"Expected exactly one saved detail response for {url}")
    versions[key] = rows[0]

results = []
for name, key in (("version-a.xlsx", "a"), ("version-b-empty-email.xlsx", "b"),
                  ("version-b-with-unsaved-input.xlsx", "b")):
    file = root / name
    sheet = load_workbook(file)["PI"]
    quote = versions[key]
    for cell, field in (("B4", "recipient_name"), ("B5", "buyer_address"),
                        ("B7", "buyer_email"), ("B8", "buyer_phone")):
        if (sheet[cell].value or "") != (quote[field] or ""):
            raise AssertionError((name, cell, field, sheet[cell].value, quote[field]))
    if sheet["L9"].value != quote["quote_no"]:
        raise AssertionError((name, "quote number"))
    text = "\n".join(str(cell.value or "") for row in sheet for cell in row)
    if "changed-master@example.com" in text or "unsaved@example.com" in text:
        raise AssertionError((name, "current master or draft leaked"))
    results.append({"file": name, "bytes": file.stat().st_size,
                    "sha256": hashlib.sha256(file.read_bytes()).hexdigest(),
                    "quote_id": quote["id"], "saved_api_fields_match": True})

print(json.dumps({"scope": "synthetic isolated API responses and actual Chrome downloads", "files": results}, indent=2))
