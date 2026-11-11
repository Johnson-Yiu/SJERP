from collections import defaultdict
import csv
from decimal import Decimal
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil

from openpyxl import load_workbook

root = Path(__file__).resolve().parent
data = root / "final-runs" / "chrome"
if os.name == "nt":
    data = Path(chr(92) * 2 + "?" + chr(92) + str(data))
destination = root / "verified-downloads"
destination.mkdir(exist_ok=True)
summary = []

def latest(name):
    return max(data.rglob(name), key=lambda path: path.stat().st_mtime)

def info(file, **fields):
    content = file.read_bytes()
    summary.append({"file": file.name, "runPath": file.relative_to(data).as_posix(),
                    "bytes": len(content), "sha256": sha256(content).hexdigest(), **fields})

for name, total, recipient in [
    ("downloaded-quote.xlsx", Decimal("12.50"), None),
    ("version-a.xlsx", Decimal("10.00"), "Version A Recipient"),
    ("version-b-empty-email.xlsx", Decimal("10.00"), "Version B Recipient"),
]:
    file = latest(name)
    with file.open("rb") as stream:
        book = load_workbook(stream, read_only=True, data_only=True)
        try:
            assert book.sheetnames == ["PI"], name
            sheet = book["PI"]
            quantity, unit_price, item_amount, freight, grand_total = (
                Decimal(str(sheet[cell].value)) for cell in ("J11", "L11", "M11", "M13", "M14")
            )
            assert quantity * unit_price == item_amount
            assert item_amount + freight == grand_total == total
            if recipient:
                assert sheet["B4"].value == recipient
            info(file, sheet="PI", quantity=str(quantity), unitPrice=str(unit_price), itemAmount=str(item_amount),
                 freight=str(freight), total=str(grand_total), recipient=recipient,
                 archivedBinary=False)
        finally:
            book.close()

file = latest("sales-order-import-template.xlsx")
with file.open("rb") as stream:
    book = load_workbook(stream, read_only=True, data_only=True)
    try:
        assert book.sheetnames == ["使用说明", "订单明细"]
        header = next(book["订单明细"].values)
        assert len(header) == 9 and all(header)
        info(file, sheets=book.sheetnames, header=header, archivedBinary=True)
        shutil.copyfile(file, destination / file.name)
    finally:
        book.close()

for name, required in [
    ("history-products.csv", {"统计口径", "商品金额", "币种", "关联状态"}),
    ("integrated-history-preflight.csv", {"工作表", "原系统记录编号", "来源关联组编号", "结果"}),
    ("sales-order-import-errors.csv", {"表格行号", "来源订单编号", "错误原因"}),
]:
    file = latest(name)
    assert file.read_bytes().startswith(bytes((239, 187, 191))), name
    with file.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        rows = list(reader)
        header = reader.fieldnames
    assert required <= set(header)
    assert rows
    fields = {"header": header, "records": len(rows), "archivedBinary": True}
    if name == "history-products.csv":
        totals = defaultdict(Decimal)
        for row in rows:
            totals[row["币种"]] += Decimal(row["商品金额"])
        assert totals == {"USD": Decimal("15.00"), "CNY": Decimal("200.00")}
        fields["totalsByCurrency"] = {currency: str(total) for currency, total in totals.items()}
    elif name == "integrated-history-preflight.csv":
        assert any(row["原系统记录编号"] == "FIXB-SO-1" for row in rows)
        assert all(row["原系统记录编号"] != "FIXA-SO-1" for row in rows)
        fields["source"] = "FIXB"
    else:
        assert rows == [{"表格行号": "4", "来源订单编号": "UAT-EXT-ORDER-BAD", "错误原因": "找不到 SKU：UAT-UNKNOWN-SKU。"}]
    info(file, **fields)
    shutil.copyfile(file, destination / file.name)

(destination / "manifest.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
