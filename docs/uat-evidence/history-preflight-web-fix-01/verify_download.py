"""Check the browser-saved CSV order identifiers against workbook B."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parent
workbook_path = ROOT / "workbook-B-duplicate.xlsx"
csv_path = ROOT / "history-preflight.csv"

workbook = load_workbook(workbook_path, read_only=True, data_only=True)
sheet = workbook["销售订单"]
headers = next(sheet.iter_rows(min_row=1, max_row=1, values_only=True))
source_id_column = headers.index("原系统记录编号")
workbook_ids = [
    row[source_id_column]
    for row in sheet.iter_rows(min_row=2, values_only=True)
    if row[source_id_column]
]
workbook.close()

with csv_path.open("r", encoding="utf-8-sig", newline="") as stream:
    csv_rows = list(csv.DictReader(stream))
csv_ids = [row["原系统记录编号"] for row in csv_rows if row["工作表"] == "销售订单"]

assert Counter(csv_ids) == Counter(workbook_ids), (csv_ids, workbook_ids)
assert csv_ids and all(value.startswith("FIXB-") for value in csv_ids), csv_ids
assert not any(value.startswith("FIXA-") for value in csv_ids), csv_ids

result = {
    "downloaded_file": csv_path.name,
    "size_bytes": csv_path.stat().st_size,
    "sha256": hashlib.sha256(csv_path.read_bytes()).hexdigest(),
    "csv_row_count": len(csv_rows),
    "workbook_B_sales_order_source_ids": workbook_ids,
    "downloaded_csv_sales_order_source_ids": csv_ids,
    "multiset_matches_workbook_B": True,
    "contains_workbook_A_order_ids": False,
}
(ROOT / "download-verification.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(json.dumps(result, ensure_ascii=False, indent=2))
