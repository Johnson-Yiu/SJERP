"""Seed isolated development masters and create synthetic XLSX upload cases."""

from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path

from openpyxl import Workbook


PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from crm.history_import_preflight import SHEET_SCHEMAS
from crm.models import Customer, Product, SKU


def main() -> None:
    customer, _ = Customer.objects.get_or_create(
        code="PREFLIGHT-W01-C1",
        defaults={"name": "合成预检客户", "country": "US", "address": "Synthetic address"},
    )
    product, _ = Product.objects.get_or_create(
        code="PREFLIGHT-W01-P1",
        defaults={"name": "合成预检产品", "sales_model_prefix": "PFW1"},
    )
    sku, _ = SKU.objects.get_or_create(
        sku="PREFLIGHT-W01-S1",
        defaults={"product": product, "display_name_cn": "合成预检 SKU", "unit": "pcs"},
    )

    group = {
        "group_id": "W01-G1", "source_system": "Synthetic legacy export",
        "exported_at": date(2025, 1, 2), "coverage_status": "complete",
        "truth_status": "真实", "evidence_reference": "synthetic://manifest/W01",
        "notes": "合成验收资料，不对应真实客户或历史业务。",
    }
    sales_order = {
        "group_id": "W01-G1", "source_record_id": "W01-SO-1", "order_no": "W01-OLD-SO-1",
        "order_date": date(2024, 8, 1), "lifecycle_state": "open",
        "customer_code": customer.code, "customer_name_snapshot": customer.name,
        "customer_country_snapshot": "US", "customer_address_snapshot": "Synthetic historical address",
        "customer_contact_name_snapshot": "Synthetic contact", "customer_phone_snapshot": "555-0101",
        "customer_email_snapshot": "synthetic@example.test", "currency": "USD",
        "exchange_rate": "1.000000", "shipping_fee": "0.0000", "discount": "0.0000",
        "truth_status": "真实", "voucher_reference": "synthetic://order/W01-SO-1", "notes": "",
    }
    sales_line = {
        "group_id": "W01-G1", "source_order_id": "W01-SO-1", "source_line_id": "W01-L1",
        "sku_code": sku.sku, "sku_name_snapshot": sku.display_name_cn,
        "sales_model_snapshot": "PFW1-HIST", "description_snapshot": "Synthetic historical line",
        "unit_snapshot": sku.unit, "base_unit_snapshot": sku.unit,
        "quantity_base": "10.00", "unit_price": "12.123456789012",
        "trade_quantity": None, "trade_unit_snapshot": None, "trade_unit_price": None,
        "trade_factor_snapshot": None, "allow_fraction_snapshot": None,
        "truth_status": "真实", "voucher_reference": "synthetic://order-line/W01-L1", "notes": "",
    }
    duplicate_order = {**sales_order, "source_record_id": "W01-SO-DUP", "order_no": "W01-OLD-DUP"}

    def save_workbook(name: str, records: dict[str, list[dict[str, object]]]) -> None:
        workbook = Workbook()
        instructions = workbook.active
        instructions.title = "使用说明"
        instructions.append(["合成历史资料只读预检工作簿"])
        instructions.append(["仅用于本地验收，不对应真实客户或历史业务。"])
        for sheet_name, columns in SHEET_SCHEMAS.items():
            sheet = workbook.create_sheet(sheet_name)
            sheet.append([column["label"] for column in columns])
            for row_number, record in enumerate(records.get(sheet_name, []), start=2):
                for column_number, column in enumerate(columns, start=1):
                    sheet.cell(row=row_number, column=column_number, value=record.get(column["key"]))
        path = Path(__file__).resolve().parent / name
        workbook.save(path)
        workbook.close()
        print(f"created {path.name} ({path.stat().st_size} bytes)")

    save_workbook("synthetic-history-valid.xlsx", {
        "分组": [group], "销售订单": [sales_order], "销售明细": [sales_line],
    })
    save_workbook("synthetic-history-duplicate.xlsx", {
        "分组": [group], "销售订单": [duplicate_order, duplicate_order], "销售明细": [sales_line],
    })
    (Path(__file__).resolve().parent / "synthetic-history-malformed.xlsx").write_bytes(b"not a valid XLSX archive")
    (Path(__file__).resolve().parent / "synthetic-history-unsupported.csv").write_text("not an XLSX workbook\n", encoding="utf-8")
    print("seeded 1 synthetic customer, 1 product and 1 SKU")


if __name__ == "__main__":
    main()
