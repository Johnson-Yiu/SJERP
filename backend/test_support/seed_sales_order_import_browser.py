"""Seed synthetic rows for the isolated codex-superuser sales import browser check."""

from datetime import date
import json
import os
from pathlib import Path

import django

django.setup()

from django.conf import settings
from django.db import connection
from openpyxl import Workbook, load_workbook

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
followup_evidence_dir = (repo_root / "docs" / "uat-evidence" / "release-integration-repair-01-followup" / "browser" / "sales-order-import-real.spec").resolve()
completion_evidence_dir = (repo_root / "docs" / "uat-evidence" / "release-completion-acceptance-02" / "browser" / "sales-order-import-real.spec").resolve()
if evidence_dir not in {completion_evidence_dir, expected_evidence_dir, review_evidence_dir, release_evidence_dir, followup_evidence_dir} or evidence_dir.is_symlink():
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
if evidence_dir in {followup_evidence_dir, completion_evidence_dir}:
    long_customer = Customer.objects.create(
        code="UAT-LONG-CUSTOMER",
        name="North-West International Lighting and Architectural Project Procurement Services, Distribution and Customer Care Group",
    )
    long_order = Order.objects.create(
        customer=long_customer, order_no="UAT-FIN-2026-INTERNATIONAL-00000000001",
        status="confirmed", order_date=date(2026, 11, 6), currency="USD", exchange_rate="7.1",
        customer_name_snapshot=long_customer.name,
    )
    for quantity in (1, 2, 3, 4):
        long_order.items.create(sku=sku_each, quantity=quantity, unit_price="1000.50")

    if evidence_dir == completion_evidence_dir:
        other = Order.objects.create(
            customer=long_customer, order_no="UAT-FIN-2026-INTERNATIONAL-00000000002",
            status="confirmed", order_date=date(2026, 11, 6), currency="USD", exchange_rate="7.1",
        )
        other.items.create(sku=sku_each, quantity=1, unit_price=500)
        for order, total in ((long_order, "10005.00"), (other, "500.00")):
            PaymentPlan.objects.create(order=order, direction="receivable", currency="USD", planned_amount=total)

    source = repo_root / "docs/uat-evidence/history-preflight-web-fix-01/workbook-A-valid.xlsx"
    historical = load_workbook(source)
    historical_order = "SYNTH-HISTORY-ORDER-ARCHIVE-2024-00000000123"
    historical["销售订单"].cell(2, 2, historical_order)
    historical["销售订单"].cell(2, 7, long_customer.name)
    lines = historical["销售明细"]
    line = [cell.value for cell in lines[2]]
    for index in range(1, 5):
        values = [*line]
        values[1:3] = [historical_order, f"SYNTH-HISTORY-LONG-LINE-{index:010d}"]
        if index == 1:
            for column, value in enumerate(values, 1):
                lines.cell(2, column).value = value
        else:
            lines.append(values)
    historical.save(evidence_dir / "long-history-preflight.xlsx")
    historical.close()
    fixture["long_content"] = {
        "customer": long_customer.name, "order": long_order.order_no,
        "historical_order": historical_order, "workbook": "long-history-preflight.xlsx",
    }
    from django.contrib.auth import get_user_model
    from django.core.files.uploadedfile import SimpleUploadedFile
    from django.test import TestCase
    from crm.services import finance_closeout
    from crm.tests.test_history_takeover import HistoryTakeoverFixtureMixin

    class HistoryFixture(HistoryTakeoverFixtureMixin, TestCase):
        pass

    history = HistoryFixture()
    history.setUp()
    history.client.defaults["HTTP_HOST"] = "127.0.0.1"
    source_rows = history.source_rows()
    source_id = "SYNTH-HISTORY-RECEIPT-ARCHIVE-2024-000000001"
    source_rows["收付款流水"][0]["source_record_id"] = source_id
    source_rows["销售订单"][0]["customer_name_snapshot"] = long_customer.name
    source_rows["销售订单"][0]["order_no"] = "SYNTH-HISTORY-SALES-ARCHIVE-2024-0001"
    application, group, _ = history.application_and_group(source_rows)
    group_url = f"/api/import/history-takeovers/{application.pk}/groups/{group.pk}/"
    for operation, data in [
        ("review", {"decision": "approve", "note": "合成资料复核", "confirm_manual": True}),
        ("execute", {}),
    ]:
        response = history.client.post(group_url + operation + "/", data, format="json")
        if response.status_code != 200:
            raise RuntimeError(f"Synthetic history {operation} failed: {response.data}")

    users = get_user_model()
    codex = users.objects.get(username="codex")
    users.objects.create_superuser(
        username="codex-history-reviewer", password=os.environ["CODEX_TEST_PASSWORD"], first_name="历史测试复核员",
    )
    account = finance_closeout.create_account({
        "code": "SYN-HISTORY", "name": "合成历史账户", "account_type": "bank",
        "ownership": "own", "ownership_reason": "合成验收",
    }, codex)
    voucher = finance_closeout.upload(SimpleUploadedFile("history-receipt.pdf", b"%PDF-1.4\nSynthetic\n%%EOF"), codex)
    existing_voucher = finance_closeout.upload(SimpleUploadedFile("other-receipt.pdf", b"%PDF-1.4\nOther synthetic receipt\n%%EOF"), codex)
    existing, _ = finance_closeout.submit({
        "account": account.pk, "voucher": existing_voucher.pk, "actual_date": "2024-09-03",
        "amount": "287.43", "reason": "合成验收", "request_key": "existing-history-browser",
        "kind": "cash", "direction": "income", "nature": "unclassified", "truth": "verified",
        "source_system": "SYNTHETIC", "source_key": "SYNTHETIC-HISTORY-EXISTING", "allocations": [],
    }, codex)
    finance_closeout.post(existing.pk, codex, voucher_checked=True)
    fixture["history_finance"] = {"source": source_id, "account": account.pk, "voucher": voucher.pk}
(evidence_dir / "fixture.json").write_text(json.dumps(fixture, ensure_ascii=False, indent=2), encoding="utf-8")
print({"fixture": "synthetic sales order workbook seeded in the isolated SQLite database"})
