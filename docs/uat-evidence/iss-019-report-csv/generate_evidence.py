"""Generate the ISS-019 CSV/API reconciliation artifact from the live Django endpoint."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import sys
from decimal import Decimal
from pathlib import Path


EVIDENCE = Path(__file__).resolve().parent
ROOT = EVIDENCE.parents[2]
BACKEND = ROOT / "backend"
DB_PATH = Path(r"C:\Users\Johnson\.codex\visualizations\2026\10\23\01a1690a-0a0e-7b72-826e-17ae19ef53e2\iss019-csv-evidence.sqlite3")
DB_PATH.unlink(missing_ok=True)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH.as_posix()}"
os.environ["APP_STAGE"] = "development"
os.environ["DJANGO_DEBUG"] = "true"
os.environ["DEVELOPMENT_SUPERADMIN"] = "true"
os.environ["RBAC_ENFORCEMENT"] = "false"
sys.path.insert(0, str(BACKEND))

import django  # noqa: E402

django.setup()

from django.core.management import call_command  # noqa: E402
from rest_framework.test import APIClient  # noqa: E402

from crm.models import Customer, Order, Product, ProductCategory, SKU  # noqa: E402


call_command("migrate", interactive=False, verbosity=0)

customer = Customer.objects.create(code="ISS019-FORMULA", name="=2+2", country="中国")
other_customer = Customer.objects.create(code="ISS019-PLAIN", name="普通客户", country="中国")
category = ProductCategory.objects.create(name="ISS-019测试分类")
product = Product.objects.create(code="ISS019-P", name="CSV测试灯具", category=category)
pcs = SKU.objects.create(sku="ISS019-PCS", product=product, unit="pcs")
box = SKU.objects.create(sku="ISS019-BOX", product=product, unit="box")

order = Order.objects.create(
    order_no="ISS019-SO-001",
    customer=customer,
    order_date="2026-09-10",
    currency="CNY",
    exchange_rate=Decimal("1"),
    status="confirmed",
)
order.items.create(sku=pcs, quantity=Decimal("2"), unit_price=Decimal("20"))

other_order = Order.objects.create(
    order_no="ISS019-SO-002",
    customer=other_customer,
    order_date="2026-09-11",
    currency="USD",
    exchange_rate=Decimal("7"),
    status="confirmed",
)
other_order.items.create(sku=box, quantity=Decimal("3"), unit_price=Decimal("5"))

client = APIClient()
params = {
    "source": "sales",
    "group_by": "customer",
    "date_field": "order_date",
    "date_from": "2026-09-01",
    "date_to": "2026-09-30",
    "export": "csv",
}
response = client.get("/api/reports/data/", params)
if response.status_code != 200:
    raise SystemExit(f"report export failed: {response.status_code} {response.content!r}")

csv_path = EVIDENCE / "report-sales-customer.csv"
csv_path.write_bytes(response.content)
text = response.content.decode("utf-8-sig")
rows = list(csv.reader(io.StringIO(text)))
total_row = next(row for row in rows if row and row[0] == "合计（单据去重）")
api_response = client.get("/api/reports/data/", {key: value for key, value in params.items() if key != "export"})
if api_response.status_code != 200:
    raise SystemExit(f"report API failed: {api_response.status_code} {api_response.content!r}")

api_amount = Decimal(str(api_response.data["totals"]["amount"]))
csv_amount = Decimal(total_row[1])
if api_amount != csv_amount:
    raise SystemExit(f"CSV/API amount mismatch: {api_amount} != {csv_amount}")
if not response.content.startswith(b"\xef\xbb\xbf"):
    raise SystemExit("CSV is missing UTF-8 BOM")
if "'=2+2" not in text:
    raise SystemExit("formula-like customer label was not protected")

(EVIDENCE / "report-api.json").write_text(
    json.dumps(api_response.data, default=str, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
(EVIDENCE / "csv-byte-check.json").write_text(
    json.dumps(
        {
            "path": csv_path.name,
            "bytes": len(response.content),
            "sha256": hashlib.sha256(response.content).hexdigest(),
            "prefix_hex": response.content[:3].hex(),
            "encoding": "UTF-8 with BOM (utf-8-sig)",
            "formula_protection": "'=2+2",
            "api_total_amount": str(api_amount),
            "csv_total_amount": str(csv_amount),
            "api_total_count": api_response.data["totals"]["count"],
            "csv_total_count": int(total_row[2]),
            "api_total_quantities": {key: str(value) for key, value in api_response.data["totals"]["quantities"].items()},
            "csv_total_quantities": total_row[3],
        },
        ensure_ascii=False,
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)
print(json.dumps({"csv": str(csv_path), "api": str(EVIDENCE / "report-api.json"), "bytes": len(response.content)}, ensure_ascii=False))
