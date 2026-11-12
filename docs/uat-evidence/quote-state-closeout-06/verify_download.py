"""Reconcile a downloaded Q6 workbook against its saved quote's PI response."""
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
import sys

from openpyxl import load_workbook

file = Path(sys.argv[1])
pi = json.load(sys.stdin)
sheet = load_workbook(file, data_only=True)["PI"]
assert sheet["L9"].value == pi["invoice_no"]
assert sheet["B3"].value == pi["buyer"]["company_name"]
assert sheet["I3"].value == pi["seller"]["name"]
currency = pi["totals"]["currency"]
assert any(cell.value == f"Total\n{currency}" for row in sheet for cell in row)
items = []
for product in pi["products"]:
    (row,) = [cell.row for cell in sheet["C"] if cell.value == product["model"]]
    assert sheet[f"D{row}"].value == (product["description"] or product["product_name"])
    assert sheet[f"K{row}"].value == product["unit"]
    for column, field in (("J", "quantity"), ("L", "unit_price"), ("M", "amount")):
        assert Decimal(str(sheet[f"{column}{row}"].value)) == Decimal(str(product[field]))
    items.append({column: sheet[f"{column}{row}"].value for column in ("C", "D", "J", "K", "L", "M")})
(total_row,) = [cell.row for cell in sheet["A"] if str(cell.value).startswith("SAY TOTAL")]
total = sheet[f"M{total_row - 1}"].value
assert Decimal(str(total)) == Decimal(str(pi["totals"]["total_amount"]))
print(json.dumps({
    "file": file.name, "bytes": file.stat().st_size, "sha256": sha256(file.read_bytes()).hexdigest(),
    "quote": sheet["L9"].value, "buyer": sheet["B3"].value, "seller_matches_snapshot": True,
    "currency": currency, "total": total, "items": items, "template_sha256": pi["template_sha256"],
}))
