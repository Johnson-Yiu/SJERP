"""Create synthetic masters and a populated copy of the historical preflight template."""

import io
import json
import os
from datetime import date
from pathlib import Path

import django

django.setup()

from django.conf import settings
from openpyxl import load_workbook

from crm.history_import_preflight import SHEET_SCHEMAS
from crm.models import Customer, Product, SKU
from test_support.isolated_runtime import verify_isolated_runtime


verify_isolated_runtime(settings=settings, database_must_exist=True)
root = Path(__file__).resolve().parents[2]
evidence = Path(os.environ["FIRST_RELEASE_CONSOLIDATION_EVIDENCE_DIR"])
evidence.mkdir(parents=True, exist_ok=True)
customer, _ = Customer.objects.get_or_create(
    code="COD-ISO-HIST-C1",
    defaults={"name": "合成历史客户", "country": "US", "address": "Synthetic historical address"},
)
product, _ = Product.objects.get_or_create(
    code="COD-ISO-HIST-P1",
    defaults={"name": "合成历史产品", "sales_model_prefix": "CODH"},
)
sku, _ = SKU.objects.get_or_create(
    sku="COD-ISO-HIST-S1",
    defaults={"product": product, "display_name_cn": "合成历史 SKU", "unit": "pcs"},
)

rows = {
    "分组": [{
        "group_id": "COD-G-1", "source_system": "Synthetic legacy export",
        "exported_at": date(2025, 1, 2), "coverage_status": "complete",
        "truth_status": "真实", "evidence_reference": "synthetic://manifest",
    }],
    "销售订单": [{
        "group_id": "COD-G-1", "source_record_id": "COD-SO-SRC-1",
        "order_no": "COD-OLD-SO-1", "order_date": date(2024, 8, 1),
        "lifecycle_state": "open", "customer_code": customer.code,
        "customer_name_snapshot": customer.name, "customer_country_snapshot": "US",
        "customer_address_snapshot": "Synthetic historical address",
        "customer_contact_name_snapshot": "Synthetic contact",
        "customer_phone_snapshot": "555-0101", "customer_email_snapshot": "history@example.test",
        "currency": "USD",
        "exchange_rate": "1.000000", "shipping_fee": "0.0000", "discount": "0.0000",
        "truth_status": "真实", "voucher_reference": "synthetic://order",
    }],
    "销售明细": [{
        "group_id": "COD-G-1", "source_order_id": "COD-SO-SRC-1",
        "source_line_id": "1", "sku_code": sku.sku,
        "sku_name_snapshot": sku.display_name_cn, "sales_model_snapshot": "HIST-COD",
        "description_snapshot": "Synthetic historical item", "unit_snapshot": "pcs",
        "base_unit_snapshot": "pcs", "quantity_base": "10.00",
        "unit_price": "12.123456789012", "truth_status": "真实",
        "voucher_reference": "synthetic://order-line",
    }],
}

template_path = root / "docs/uat-evidence/r1-iss121-history-import-preflight-20261103/ISS-121-history-import-template.xlsx"
workbook = load_workbook(template_path, data_only=False)
try:
    for sheet_name, records in rows.items():
        columns = SHEET_SCHEMAS[sheet_name]
        for row_number, record in enumerate(records, start=2):
            for column_number, column in enumerate(columns, start=1):
                workbook[sheet_name].cell(row=row_number, column=column_number, value=record.get(column["key"]))
    workbook.save(evidence / "synthetic-history-preflight.xlsx")
finally:
    workbook.close()

(evidence / "fixture.json").write_text(json.dumps({
    "synthetic_only": True,
    "customer_id": customer.pk,
    "sku_id": sku.pk,
    "source_order_id": "COD-SO-SRC-1",
    "source_group_id": "COD-G-1",
}, ensure_ascii=False, indent=2), encoding="utf-8")
print("Synthetic historical preflight workbook prepared.")
