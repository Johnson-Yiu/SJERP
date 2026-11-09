"""Seed synthetic rows for the isolated codex-superuser sales import browser check."""

from datetime import date
import json
import os
from pathlib import Path

import django

django.setup()

from django.conf import settings
from django.db import connection
from openpyxl import Workbook

from crm.models import Customer, Product, SKU, SKUTradeUnit, Order, PaymentPlan, FinanceAccount
from test_support.isolated_runtime import verify_isolated_runtime

repo_root = Path(__file__).resolve().parents[2]
verify_isolated_runtime(settings=settings, database_must_exist=True)
if connection.vendor != "sqlite":
    raise SystemExit("The browser fixture may only seed the isolated SQLite database.")

evidence_dir = Path(os.environ.get("SALES_ORDER_IMPORT_EVIDENCE_DIR", "")).resolve()
expected_evidence_dir = (
    repo_root / "docs" / "uat-evidence" / "sales-order-import-01" / "browser" / "sales-order-import-real.spec"
).resolve()
review_evidence_dir = (repo_root / "docs" / "uat-evidence" / "first-release-independent-review-02" / "browser" / "sales-order-import-real.spec").resolve()
release_evidence_dir = (repo_root / "docs" / "uat-evidence" / "release-integration-repair-01" / "browser" / "sales-order-import-real.spec").resolve()
if evidence_dir not in {expected_evidence_dir, review_evidence_dir, release_evidence_dir} or evidence_dir.is_symlink():
    raise SystemExit("The sales import browser fixture must use its allowlisted evidence directory.")
evidence_dir.mkdir(parents=True, exist_ok=True)

customer, _ = Customer.objects.get_or_create(
    code="UAT-IMP-C001", defaults={"name": "导入验收合成客户", "status": "customer"},
)
product, _ = Product.objects.get_or_create(
    code="UAT-IMP-P001", defaults={"name": "导入验收合成灯具"},
)
sku_box, _ = SKU.objects.get_or_create(
    sku="UAT-IMP-SKU-001",
    defaults={"product": product, "unit": "个", "cost_price": "4.25"},
)
sku_each, _ = SKU.objects.get_or_create(
    sku="UAT-IMP-SKU-002",
    defaults={"product": product, "unit": "个", "cost_price": "2.00"},
)
SKUTradeUnit.objects.get_or_create(
    sku=sku_box,
    unit="箱",
    defaults={"name": "10 件/箱", "factor": "10", "allow_fraction": False, "is_default": True},
)

for suffix, total in [('COMPANY',1000),('CUSTOMER',1000),('UNKNOWN',1000),('WRITEOFF',90),('REFUND',1000)]:
    order, created = Order.objects.get_or_create(order_no='SYN-FIN-'+suffix, defaults={'customer':customer,'order_date':date(2026,11,6),'status':'confirmed','currency':'USD','exchange_rate':'7.1'})
    if created:
        order.items.create(sku=sku_each,quantity=1,unit_price=total)
        PaymentPlan.objects.create(order=order,direction='receivable',currency='USD',planned_amount=total)
for code, currency in [('SYNTH_FX','USD'),('SYNTH_CNY','CNY')]:
    FinanceAccount.objects.get_or_create(code=code,defaults={'name':'Synthetic '+currency+' acceptance account','currency':currency,'account_type':'bank','ownership':'own','ownership_reason':'Synthetic isolated acceptance only'})

workbook = Workbook()
sheet = workbook.active
sheet.title = "订单明细"
sheet.append(["来源订单编号", "客户编号", "订单日期", "币种", "SKU", "交易单位", "数量", "单价", "对人民币汇率"])
sheet.append(["UAT-EXT-ORDER-001", customer.code, date(2026, 11, 6), "CNY", sku_box.sku, "箱", 2, "30", "1"])
sheet.append(["UAT-EXT-ORDER-001", customer.code, date(2026, 11, 6), "CNY", sku_each.sku, "个", 3, "12", "1"])
sheet.append(["UAT-EXT-ORDER-BAD", customer.code, date(2026, 11, 6), "CNY", "UAT-UNKNOWN-SKU", "个", 1, "50", "1"])
workbook_path = evidence_dir / "sales-order-import-input.xlsx"
workbook.save(workbook_path)
workbook.close()

fixture = {
    "database_vendor": connection.vendor,
    "customer_code": customer.code,
    "valid_source_order": "UAT-EXT-ORDER-001",
    "valid_lines": 2,
    "invalid_source_order": "UAT-EXT-ORDER-BAD",
    "invalid_sku": "UAT-UNKNOWN-SKU",
    "workbook": workbook_path.name,
}
(evidence_dir / "fixture.json").write_text(json.dumps(fixture, ensure_ascii=False, indent=2), encoding="utf-8")
print({"fixture": "synthetic sales order workbook seeded in the isolated SQLite database"})
