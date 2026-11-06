"""Seed isolated masters and create distinct A/B preflight race workbooks."""

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
        code="PREFLIGHT-WFIX-C1",
        defaults={"name": "竞态验收合成客户", "country": "US", "address": "Synthetic address"},
    )
    product, _ = Product.objects.get_or_create(
        code="PREFLIGHT-WFIX-P1",
        defaults={"name": "竞态验收合成产品", "sales_model_prefix": "PFX1"},
    )
    sku, _ = SKU.objects.get_or_create(
        sku="PREFLIGHT-WFIX-S1",
        defaults={"product": product, "display_name_cn": "竞态验收合成 SKU", "unit": "pcs"},
    )

    def group(identifier: str) -> dict[str, object]:
        return {
            "group_id": f"{identifier}-G1", "source_system": "Synthetic race export",
            "exported_at": date(2025, 2, 3), "coverage_status": "complete",
            "truth_status": "真实", "evidence_reference": f"synthetic://race/{identifier}",
            "notes": "竞态验收合成工作簿，不对应真实业务。",
        }

    def order(identifier: str) -> dict[str, object]:
        return {
            "group_id": f"{identifier}-G1", "source_record_id": f"{identifier}-SO-1",
            "order_no": f"{identifier}-LEGACY-1", "order_date": date(2024, 9, 1),
            "lifecycle_state": "open", "customer_code": customer.code,
            "customer_name_snapshot": customer.name, "customer_country_snapshot": "US",
            "customer_address_snapshot": "Synthetic historical address",
            "customer_contact_name_snapshot": "Synthetic contact", "customer_phone_snapshot": "555-0102",
            "customer_email_snapshot": "synthetic@example.test", "currency": "USD",
            "exchange_rate": "1.000000", "shipping_fee": "0.0000", "discount": "0.0000",
            "truth_status": "真实", "voucher_reference": f"synthetic://race/{identifier}/order", "notes": "",
        }

    def line(identifier: str) -> dict[str, object]:
        return {
            "group_id": f"{identifier}-G1", "source_order_id": f"{identifier}-SO-1",
            "source_line_id": f"{identifier}-L1", "sku_code": sku.sku,
            "sku_name_snapshot": sku.display_name_cn, "sales_model_snapshot": "PFX1-HIST",
            "description_snapshot": f"Synthetic {identifier} line", "unit_snapshot": sku.unit,
            "base_unit_snapshot": sku.unit, "quantity_base": "3.00", "unit_price": "8.500000000000",
            "trade_quantity": None, "trade_unit_snapshot": None, "trade_unit_price": None,
            "trade_factor_snapshot": None, "allow_fraction_snapshot": None,
            "truth_status": "真实", "voucher_reference": f"synthetic://race/{identifier}/line", "notes": "",
        }

    def write(name: str, identifier: str, duplicate: bool = False) -> Path:
        workbook = Workbook()
        instructions = workbook.active
        instructions.title = "使用说明"
        instructions.append(["历史预检竞态合成工作簿"])
        instructions.append(["仅用于本地验收，不对应真实客户或历史业务。"])
        records: dict[str, list[dict[str, object]]] = {
            "分组": [group(identifier)],
            "销售订单": [order(identifier), order(identifier)] if duplicate else [order(identifier)],
            "销售明细": [line(identifier)],
        }
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
        return path

    write("workbook-A-valid.xlsx", "FIXA")
    write("workbook-B-duplicate.xlsx", "FIXB", duplicate=True)
    print("seeded 1 synthetic customer, 1 product and 1 SKU")


if __name__ == "__main__":
    main()
