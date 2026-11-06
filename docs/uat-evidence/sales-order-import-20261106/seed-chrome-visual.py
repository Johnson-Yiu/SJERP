"""Seed synthetic rows and an XLSX file for a disposable Chrome visual check."""
import argparse
from datetime import date
from io import BytesIO
import os
from pathlib import Path
import sys
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--sqlite-file", required=True)
parser.add_argument("--xlsx-file", required=True)
args = parser.parse_args()
sqlite_source = Path(args.sqlite_file)
if sqlite_source.is_symlink():
    raise RuntimeError("Refuse to seed through a linked database path")
sqlite_file = sqlite_source.resolve(strict=True)
temp_root = Path(tempfile.gettempdir()).resolve()
if sqlite_file.parent.parent != temp_root or not sqlite_file.parent.name.startswith("sunjack-sales-order-import-chrome-") or sqlite_file.is_symlink():
    raise RuntimeError("Refuse to seed a database outside this disposable Chrome check")
os.environ["DATABASE_URL"] = "sqlite:///" + sqlite_file.as_posix()
os.environ["MEDIA_ROOT"] = str(sqlite_file.parent / "media")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))

import django
django.setup()

from django.conf import settings
from django.db import connection
from openpyxl import Workbook
from crm.models import Customer, Product, SKU, SKUTradeUnit

if connection.vendor != "sqlite" or Path(connection.settings_dict["NAME"]).resolve() != sqlite_file:
    raise RuntimeError("Chrome fixture database identity mismatch")

customer, _ = Customer.objects.get_or_create(
    code="UAT-IMP-C001", defaults={"name": "视觉验收合成客户", "status": "customer"},
)
product, _ = Product.objects.get_or_create(code="UAT-IMP-P001", defaults={"name": "视觉验收合成灯具"})
sku_a, _ = SKU.objects.get_or_create(
    sku="UAT-IMP-SKU-001", defaults={"product": product, "unit": "个", "cost_price": "4.25"},
)
sku_b, _ = SKU.objects.get_or_create(
    sku="UAT-IMP-SKU-002", defaults={"product": product, "unit": "个", "cost_price": "2.00"},
)
SKUTradeUnit.objects.get_or_create(
    sku=sku_a, unit="箱", defaults={"name": "10 件/箱", "factor": "10", "allow_fraction": False, "is_default": True},
)

workbook = Workbook()
sheet = workbook.active
sheet.title = "订单明细"
sheet.append(["来源订单编号", "客户编号", "订单日期", "币种", "SKU", "交易单位", "数量", "单价", "对人民币汇率"])
sheet.append(["UAT-EXT-ORDER-001", customer.code, date(2026, 11, 6), "CNY", sku_a.sku, "箱", 2, "30", "1"])
sheet.append(["UAT-EXT-ORDER-001", customer.code, date(2026, 11, 6), "CNY", sku_b.sku, "个", 3, "12", "1"])
sheet.append(["UAT-EXT-ORDER-BAD", customer.code, date(2026, 11, 6), "CNY", "UAT-UNKNOWN-SKU", "个", 1, "50", "1"])
xlsx_path = Path(args.xlsx_file)
if xlsx_path.is_symlink():
    raise RuntimeError("Refuse to write the XLSX through a linked path")
output = xlsx_path.resolve()
if output.parent != sqlite_file.parent:
    raise RuntimeError("Refuse to write the XLSX outside the disposable Chrome check root")
workbook.save(output)
workbook.close()
print({"database": str(sqlite_file), "database_vendor": connection.vendor, "media_root": str(settings.MEDIA_ROOT), "customer": customer.code, "valid_order_lines": 2, "invalid_order_lines": 1, "xlsx": str(output)})
