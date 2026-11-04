"""Publish only synthetic quote status and buyer fields, excluding template bank data."""
import json
from pathlib import Path

root = Path(__file__).resolve().parent / "closeout-logs" / "browser" / "iss029-recipient-snapshot.spec"
api = json.loads((root / "api-evidence.json").read_text(encoding="utf-8"))
records = []
for item in api["records"]:
    row = {key: item[key] for key in ("method", "url", "status")}
    body = item.get("body")
    if isinstance(body, dict):
        row["id"] = body.get("id")
        if "buyer" in body:
            row["buyer"] = body["buyer"]
            row["totals"] = body.get("totals")
        elif "recipient_name" in body:
            row["recipient_name"] = body.get("recipient_name")
            row["buyer_email"] = body.get("buyer_email")
            row["buyer_address"] = body.get("buyer_address")
    records.append(row)
print(json.dumps({"scope": "synthetic isolated Chrome/API; bank and full template omitted", "records": records},
                 ensure_ascii=False, indent=2))
