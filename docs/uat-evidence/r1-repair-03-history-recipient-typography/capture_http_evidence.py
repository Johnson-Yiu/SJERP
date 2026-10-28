"""Capture response metadata from the isolated local API used by R1-REPAIR-03."""

import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

base_url = os.environ.get("R1_REPAIR_BASE_URL", "http://127.0.0.1:8303")
paths = [
    "/api/reports/historical/?date_from=2017-01-01&date_to=2026-12-31",
    "/api/session/current-operator/",
]
records = []
for path in paths:
    request = Request(f"{base_url}{path}", headers={"Accept": "application/json"})
    with urlopen(request, timeout=10) as response:
        body = response.read().decode("utf-8")
        records.append(
            {
                "method": "GET",
                "url": f"{base_url}{path}",
                "status": response.status,
                "content_type": response.headers.get("Content-Type"),
                "body_prefix": body[:240],
                "json": json.loads(body),
            }
        )

output = Path(__file__).resolve().parent / "http-evidence.json"
output.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
print(output)
