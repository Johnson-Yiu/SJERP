"""Synthetic history operational backup fixture for the owned ISS-018 PG drill.

Evidence helper only; this is not product code. Run only after the stable
history source has been integrated, after the existing archive and finance
seeds, and before the source snapshot. On the restored database call verify()
and compare its returned manifest with seed().

Every formal historical, finance, inventory and fulfillment record is created
through the source workflow or its official service. Only synthetic master
data (category attributes, users, and API-created customer/supplier/product/
SKU rows) is prepared here. The shared ISS-018 database guard runs on both
seed() and verify(); PostgreSQL is required.
The two synthetic superusers are isolated service actors for this drill; they
do not constitute evidence that the ERP business login path was tested.
"""

from __future__ import annotations

import hashlib
import json
import os
import string
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection, transaction
from django.utils import timezone
from psycopg import sql
from rest_framework.test import APIClient

from crm import history_operational_contracts as contracts
from crm import history_operational_finance as history_finance
from crm import history_operational_inventory as history_inventory
from crm.history_takeover import execute_group, review_group, submit_workbook
from crm.models import (
    CategoryAttribute,
    Customer,
    FinanceAccount,
    FinanceAccountMapping,
    FinanceBankVoucherBinding,
    FinanceClassification,
    FinanceFact,
    FinanceHistoricalTransfer,
    FinanceInstruction,
    FinanceReview,
    FinanceTransferMatch,
    FinanceVoucher,
    GoodsReceipt,
    HistoryInventoryBaseline,
    HistoryInventoryBaselineReversal,
    HistoryOperationalContract,
    HistoryTakeoverApplication,
    HistoryTakeoverEvent,
    HistoryTakeoverGroup,
    HistoryTakeoverHandoff,
    HistoryTakeoverSourceRecord,
    InventoryMovement,
    InventoryReservation,
    OperationLog,
    Order,
    OrderItem,
    PaymentPlan,
    Product,
    ProductCategory,
    PurchaseOrder,
    PurchaseOrderItem,
    Shipment,
    ShipmentItem,
    SKU,
    Supplier,
)
from crm.services import finance_closeout
from crm.services.fulfillment import confirm_shipment, record_receipt
from crm.services.order_lifecycle import confirm_order
from crm.services.purchase_lifecycle import place_purchase_order
from crm.tests.iss018_drill_fixture import _assert_synthetic_database
from crm.tests.test_history_takeover import HistoryTakeoverFixtureMixin


HASH_FORMAT = (
    "sha256 of every concrete-field row as canonical UTF-8 JSON, ordered by "
    "primary key, one LF after each row; PostgreSQL sequence last_value/is_called"
)
MAIN_SUFFIX = "M"
REVERSAL_SUFFIX = "R"
WAREHOUSE_TYPE = "自有仓"


def _tag() -> str:
    root = Path(os.environ["ISS018_DRILL_ROOT"]).resolve(strict=True)
    return hashlib.sha256(root.name.encode("utf-8")).hexdigest()[:8].upper()


def _guard_owned_postgres() -> None:
    _assert_synthetic_database()
    if connection.vendor != "postgresql":
        raise RuntimeError("History operational seed requires the owned PostgreSQL drill")


def _names(tag: str, suffix: str) -> dict[str, str]:
    return {
        "group_id": f"HOP-{tag}-{suffix}",
        "source_system": f"ISS018_HISTORY_OP_{tag}_{suffix}",
        "sale_id": f"SO-{tag}-{suffix}",
        "purchase_id": f"PO-{tag}-{suffix}",
        "sales_plan_id": f"PLAN-SO-{tag}-{suffix}",
        "purchase_plan_id": f"PLAN-PO-{tag}-{suffix}",
        "sales_tx_id": f"TX-SO-{tag}-{suffix}",
        "purchase_tx_id": f"TX-PO-{tag}-{suffix}",
        "shipment_event_id": f"SHIP-{tag}-{suffix}",
        "receipt_event_id": f"GR-{tag}-{suffix}",
        "count_id": f"COUNT-{tag}-{suffix}",
    }


def _canonical(value):
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _canonical(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_canonical(item) for item in value]
    if isinstance(value, bytes):
        return {"bytes_hex": value.hex()}
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _row_payload(model, instance) -> dict:
    return {
        field.attname: _canonical(getattr(instance, field.attname))
        for field in model._meta.concrete_fields
    }


def _sequence_state(model):
    primary_key = model._meta.pk
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT pg_get_serial_sequence(%s, %s)",
            [model._meta.db_table, primary_key.column],
        )
        sequence_name = cursor.fetchone()[0]
        if not sequence_name:
            return None
        parts = [part.strip('"') for part in sequence_name.split(".")]
        cursor.execute(
            sql.SQL("SELECT last_value, is_called FROM {}").format(sql.Identifier(*parts))
        )
        last_value, is_called = cursor.fetchone()
    return {
        "name": sequence_name,
        "last_value": int(last_value),
        "is_called": bool(is_called),
    }


def _table_digest(model) -> dict:
    digest = hashlib.sha256()
    count = 0
    for instance in model._default_manager.order_by("pk").iterator(chunk_size=1000):
        encoded = json.dumps(
            _row_payload(model, instance),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        digest.update(encoded)
        digest.update(b"\n")
        count += 1
    return {
        "model": model._meta.label,
        "rows": count,
        "sha256": digest.hexdigest(),
        "sequence": _sequence_state(model),
    }


def _snapshot_models():
    return (
        get_user_model(),
        Customer,
        Supplier,
        ProductCategory,
        CategoryAttribute,
        Product,
        SKU,
        HistoryTakeoverApplication,
        HistoryTakeoverGroup,
        HistoryTakeoverSourceRecord,
        HistoryTakeoverHandoff,
        HistoryTakeoverEvent,
        HistoryInventoryBaseline,
        HistoryInventoryBaselineReversal,
        HistoryOperationalContract,
        FinanceAccount,
        FinanceAccountMapping,
        FinanceBankVoucherBinding,
        FinanceClassification,
        FinanceVoucher,
        FinanceInstruction,
        FinanceFact,
        FinanceReview,
        FinanceTransferMatch,
        FinanceHistoricalTransfer,
        Order,
        OrderItem,
        PurchaseOrder,
        PurchaseOrderItem,
        PaymentPlan,
        InventoryReservation,
        InventoryMovement,
        GoodsReceipt,
        Shipment,
        ShipmentItem,
        OperationLog,
    )


def _table_inventory() -> dict:
    models = sorted(_snapshot_models(), key=lambda model: model._meta.db_table)
    return {model._meta.db_table: _table_digest(model) for model in models}


def _new_table_rows(main_group, reversal_group) -> dict:
    group_ids = [main_group.pk, reversal_group.pk]
    rows = {
        HistoryInventoryBaseline._meta.db_table: list(
            HistoryInventoryBaseline.objects.filter(group_id__in=group_ids).order_by("pk")
        ),
        HistoryInventoryBaselineReversal._meta.db_table: list(
            HistoryInventoryBaselineReversal.objects.filter(group_id__in=group_ids).order_by("pk")
        ),
        HistoryOperationalContract._meta.db_table: list(
            HistoryOperationalContract.objects.filter(group_id=main_group.pk).order_by("pk")
        ),
    }
    model_by_table = {
        model._meta.db_table: model
        for model in (
            HistoryInventoryBaseline,
            HistoryInventoryBaselineReversal,
            HistoryOperationalContract,
        )
    }
    return {
        table_name: [
            _row_payload(model_by_table[table_name], instance)
            for instance in instances
        ]
        for table_name, instances in rows.items()
    }


def _private_file_manifest(voucher) -> dict:
    if not voucher.file or not voucher.file.name:
        raise RuntimeError(f"History voucher {voucher.pk} has no stored file")
    if voucher.scope != "account":
        raise RuntimeError(f"History voucher {voucher.pk} is not an account-scoped private voucher")
    media_root = Path(settings.MEDIA_ROOT).resolve(strict=True)
    try:
        path = Path(voucher.file.path).resolve(strict=True)
        path.relative_to(media_root)
    except (OSError, ValueError, NotImplementedError) as exc:
        raise RuntimeError(
            f"History voucher {voucher.pk} is outside the owned drill MEDIA_ROOT"
        ) from exc
    if not path.is_file():
        raise RuntimeError(f"History voucher {voucher.pk} is not a regular file")
    digest = hashlib.sha256()
    size = 0
    with voucher.file.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    file_sha256 = digest.hexdigest()
    if size != voucher.size or file_sha256 != voucher.sha256:
        raise RuntimeError(
            f"History voucher {voucher.pk} bytes disagree with FinanceVoucher metadata"
        )
    return {
        "id": voucher.pk,
        "name": voucher.file.name,
        "scope": voucher.scope,
        "stored_size": voucher.size,
        "file_size": size,
        "stored_sha256": voucher.sha256,
        "file_sha256": file_sha256,
    }


def _source_rows(fixture, tag: str, suffix: str, sku: SKU) -> tuple[dict, dict]:
    names = _names(tag, suffix)
    rows = fixture.source_rows(
        group_id=names["group_id"],
        source_system=names["source_system"],
    )
    for entries in rows.values():
        for row in entries:
            row["group_id"] = names["group_id"]

    rows["分组"][0]["source_system"] = names["source_system"]
    rows["分组"][0]["evidence_reference"] = (
        f"synthetic://history-backup/{tag}/{suffix}/manifest"
    )
    rows["销售订单"][0].update(
        source_record_id=names["sale_id"],
        order_no=f"HIST-SO-{tag}-{suffix}",
    )
    rows["销售明细"][0]["source_order_id"] = names["sale_id"]
    rows["采购订单"][0].update(
        source_record_id=names["purchase_id"],
        purchase_no=f"HIST-PO-{tag}-{suffix}",
    )
    rows["采购明细"][0]["source_purchase_id"] = names["purchase_id"]

    rows["收付款计划"][0].update(
        source_plan_id=names["sales_plan_id"],
        source_order_id=names["sale_id"],
        source_purchase_id=None,
    )
    rows["收付款计划"][1].update(
        source_plan_id=names["purchase_plan_id"],
        source_order_id=None,
        source_purchase_id=names["purchase_id"],
    )
    rows["收付款流水"][0].update(
        source_record_id=names["sales_tx_id"],
        transaction_no=f"HIST-TX-{tag}-{suffix}-S",
        source_order_id=names["sale_id"],
        source_purchase_id=None,
        source_plan_id=names["sales_plan_id"],
    )
    rows["收付款流水"][1].update(
        source_record_id=names["purchase_tx_id"],
        transaction_no=f"HIST-TX-{tag}-{suffix}-P",
        source_order_id=None,
        source_purchase_id=names["purchase_id"],
        source_plan_id=names["purchase_plan_id"],
    )
    rows["履约记录"][0].update(
        source_event_id=names["shipment_event_id"],
        parent_source_id=names["sale_id"],
    )
    rows["履约记录"][1].update(
        source_event_id=names["receipt_event_id"],
        parent_source_id=names["purchase_id"],
    )
    rows["库存盘点"][0].update(
        source_record_id=names["count_id"],
        sku_code=sku.sku,
        sku_name_snapshot=sku.display_name_cn or sku.sku,
        unit_snapshot=sku.unit,
        warehouse_type=WAREHOUSE_TYPE,
        warehouse=f"HBK-WH-{tag}-{suffix}",
        lot_reference=f"HBK-LOT-{tag}-{suffix}",
    )
    for sheet_rows in rows.values():
        for row in sheet_rows:
            if "sku_code" in row:
                row["sku_code"] = sku.sku
    return names, rows


def _api_create(client, path: str, payload: dict, label: str) -> dict:
    response = client.post(path, payload, format="json")
    if response.status_code != 201:
        raise RuntimeError(
            f"Synthetic master {label} creation failed: "
            f"HTTP {response.status_code}: {response.data}"
        )
    return response.data


def _supplier_code() -> str:
    alphabet = string.ascii_uppercase
    used = set(Supplier.objects.values_list("code", flat=True))
    for value in range(26 * 26):
        code = alphabet[value // 26] + alphabet[value % 26]
        if code not in used:
            return code
    raise RuntimeError("No unused two-letter supplier code is available in the owned drill")


def _create_master_data(maker, tag: str) -> tuple[Customer, Supplier, SKU, SKU]:
    category = ProductCategory.objects.create(name=f"History backup {tag}")
    CategoryAttribute.objects.create(
        category=category,
        name="Voltage",
        key="voltage",
        unit="V",
        include_in_sku=True,
        sort_order=1,
    )
    CategoryAttribute.objects.create(
        category=category,
        name="Width",
        key="width",
        unit="mm",
        include_in_sku=True,
        sort_order=2,
    )
    client = APIClient()
    client.force_authenticate(maker)
    customer_data = _api_create(
        client,
        "/api/customers/",
        {
            "name": f"History backup buyer {tag}",
            "country": "DE",
            "address": "Synthetic owned drill customer",
            "contacts": [{"name": f"Synthetic history contact {tag}",
                          "email": "history-backup@example.test", "is_primary": True}],
        },
        "customer",
    )
    supplier_data = _api_create(
        client,
        "/api/suppliers/",
        {
            "name": f"History backup supplier {tag}",
            "code": _supplier_code(),
            "address": "Synthetic owned drill supplier",
            "supply_categories": [category.pk],
        },
        "supplier",
    )
    skus = []
    for suffix in (MAIN_SUFFIX, REVERSAL_SUFFIX):
        prefix = f"HB{tag[:4]}{suffix}"
        product_data = _api_create(
            client,
            "/api/products/",
            {
                "name": f"History backup product {tag}-{suffix}",
                "sales_model_prefix": prefix,
                "category": category.pk,
            },
            f"product-{suffix}",
        )
        sku_data = _api_create(
            client,
            "/api/skus/",
            {
                "product": product_data["id"],
                "specification": "24V / 8mm",
                "parameter_values": {"voltage": "24", "width": "8"},
                "product_details": [{"model": "HIST-BACKUP"}],
                "sales_model": f"{prefix}-24-8",
                "unit": "pcs",
                "currency": "USD",
            },
            f"SKU-{suffix}",
        )
        skus.append(SKU.objects.get(pk=sku_data["id"]))
    return (
        Customer.objects.get(pk=customer_data["id"]),
        Supplier.objects.get(pk=supplier_data["id"]),
        skus[0],
        skus[1],
    )


def _archive_group(fixture, tag: str, suffix: str, sku: SKU, maker, reviewer):
    names, rows = _source_rows(fixture, tag, suffix, sku)
    application, _preflight, reused = submit_workbook(
        fixture.workbook_bytes(rows),
        f"synthetic-history-operational-{tag}-{suffix}.xlsx",
        maker,
    )
    if reused:
        raise RuntimeError("Unexpected duplicate source workbook in a fresh owned drill.")
    group = application.groups.get(source_group_id=names["group_id"])
    review_group(
        group,
        reviewer,
        "approve",
        "Synthetic owned-database history source, mapping and vouchers reviewed.",
        confirm_manual=True,
    )
    group.refresh_from_db()
    group, replay = execute_group(group, maker)
    if replay or group.status != "executed":
        raise RuntimeError("Official history archive did not execute exactly once.")
    if group.execution_result.get("finance_records_posted") != 0:
        raise RuntimeError("Historical archive seed unexpectedly posted finance facts.")
    return group, names


def _finance_fact(group, names, maker, reviewer, tag: str, created_files: list):
    account = finance_closeout.create_account(
        {
            "code": f"HBK-{tag}-BANK",
            "name": f"Synthetic history bank {tag}",
            "account_type": "bank",
            "ownership": "own",
            "ownership_reason": "Owned PostgreSQL history-backup drill synthetic account.",
        },
        maker,
    )
    pdf = (
        b"%PDF-1.4\n"
        + f"Synthetic history backup voucher {tag}\n".encode("ascii")
        + b"%%EOF\n"
    )
    voucher = finance_closeout.upload(
        SimpleUploadedFile(
            f"history-operational-{tag}.pdf",
            pdf,
            content_type="application/pdf",
        ),
        maker,
    )
    created_files.append((voucher.file.storage, voucher.file.name))
    source = group.source_records.get(
        record_type="收付款流水",
        source_record_id=names["sales_tx_id"],
    )
    instruction, created = history_finance.submit_source(
        group.pk,
        source.pk,
        {
            "account": account.pk,
            "voucher": voucher.pk,
            "actual_date": "2024-09-03",
            "amount": "287.43",
            "reason": "Synthetic historical source linked to private voucher for backup restore verification.",
        },
        maker,
    )
    if not created:
        raise RuntimeError("Unexpected duplicate historical finance instruction.")
    history_finance.advance_source(group.pk, source.pk, "approve", reviewer)
    history_finance.advance_source(
        group.pk,
        source.pk,
        "post",
        maker,
        voucher_checked=True,
    )
    return FinanceFact.objects.get(instruction_id=instruction.pk)


def _balance_payload(group, names, sku: SKU) -> dict:
    records = {
        (record.record_type, record.source_record_id): record
        for record in group.source_records.all()
    }
    sale = records[("销售订单", names["sale_id"])]
    purchase = records[("采购订单", names["purchase_id"])]
    sale_line = records[("销售明细", f'{names["sale_id"]}:1')]
    purchase_line = records[("采购明细", f'{names["purchase_id"]}:1')]
    sales_plan = records[("收付款计划", names["sales_plan_id"])]
    purchase_plan = records[("收付款计划", names["purchase_plan_id"])]
    return {
        "cutover_date": "2025-01-01",
        "reason": "Synthetic reviewed residual contract and opening balance backup fixture.",
        "contracts": [
            {
                "source_id": sale.pk,
                "balance_mode": "itemized",
                "evidence_reference": "synthetic://history-backup/receivable-plan",
                "plan_source_ids": [sales_plan.pk],
                "remaining_shipping_fee": "0",
                "remaining_discount": "0",
                "amount_evidence": "synthetic://history-backup/residual-sales-amount",
                "line_options": [
                    {
                        "source_id": sale_line.pk,
                        "unit_cost": "3.25",
                        "cost_currency": sku.currency,
                        "cost_evidence": "synthetic://history-backup/sku-cost",
                    }
                ],
            },
            {
                "source_id": purchase.pk,
                "balance_mode": "itemized",
                "evidence_reference": "synthetic://history-backup/payable-plan",
                "plan_source_ids": [purchase_plan.pk],
                "no_additional_costs": True,
                "costs_evidence": "synthetic://history-backup/no-extra-costs",
                "line_options": [
                    {
                        "source_id": purchase_line.pk,
                        "supplier_sku_id": None,
                        "manual_reason": "Synthetic verified source has no supplier SKU mapping.",
                        "target": "order",
                        "sales_source_id": sale.pk,
                    }
                ],
            },
        ],
    }


def _activate_inventory(group, names, sku, maker, reviewer, *, reverse_after=False):
    source = group.source_records.get(
        record_type="库存盘点",
        source_record_id=names["count_id"],
    )
    row = {
        "source_id": source.pk,
        "goods_ownership": "own",
        "unit_cost": "3.25",
        "cost_currency": sku.currency,
        "no_lot": False,
    }
    _proposal, replay = history_inventory.propose(
        group.pk,
        [row],
        "Synthetic complete SKU count and ownership/cost evidence.",
        True,
        maker,
    )
    if replay:
        raise RuntimeError("Unexpected inventory proposal replay.")
    history_inventory.approve(
        group.pk,
        "Synthetic independent inventory baseline review.",
        reviewer,
    )
    baseline_ids, replay = history_inventory.execute(group.pk, maker)
    if replay or len(baseline_ids) != 1:
        raise RuntimeError("Synthetic history inventory baseline did not execute exactly once.")
    if reverse_after:
        replay = history_inventory.reverse(
            group.pk,
            "Synthetic backup fixture for immutable inventory baseline reversal.",
            reviewer,
        )
        if replay:
            raise RuntimeError("Unexpected inventory baseline reversal replay.")
    return HistoryInventoryBaseline.objects.get(pk=baseline_ids[0])


def _fulfillment_rows(group, maker, tag: str):
    sales_link = HistoryOperationalContract.objects.get(
        group=group,
        archived_order__isnull=False,
    )
    purchase_link = HistoryOperationalContract.objects.get(
        group=group,
        archived_purchase__isnull=False,
    )
    sale = confirm_order(sales_link.continuation_order)
    purchase = place_purchase_order(
        purchase_link.continuation_purchase,
        operator=maker,
    )
    location = {
        "warehouse_type": WAREHOUSE_TYPE,
        "warehouse": f"HBK-WH-{tag}-{MAIN_SUFFIX}",
        "lot_reference": f"HBK-LOT-{tag}-{MAIN_SUFFIX}",
    }
    receipt = record_receipt(
        purchase.items.get(),
        {
            "receipt_date": timezone.localdate(),
            "quantity": Decimal("3.00"),
            "unit_cost": Decimal("3.25"),
            **location,
        },
    )
    shipment = confirm_shipment(
        sale,
        {
            "shipment_date": timezone.localdate(),
            "items": [
                {
                    "order_item": sale.items.get().pk,
                    "quantity": Decimal("6.00"),
                    **location,
                }
            ],
        },
    )
    return receipt, shipment


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _current_manifest(tag: str) -> dict:
    main_names = _names(tag, MAIN_SUFFIX)
    reversal_names = _names(tag, REVERSAL_SUFFIX)
    main_group = HistoryTakeoverGroup.objects.get(
        source_group_id=main_names["group_id"],
        source_system=main_names["source_system"],
    )
    reversal_group = HistoryTakeoverGroup.objects.get(
        source_group_id=reversal_names["group_id"],
        source_system=reversal_names["source_system"],
    )
    _require(
        main_group.status == "executed" and reversal_group.status == "executed",
        "Both synthetic history groups must be officially archived.",
    )
    main_baselines = list(
        HistoryInventoryBaseline.objects.filter(group=main_group)
        .select_related("sku")
        .order_by("pk")
    )
    reversal_baselines = list(
        HistoryInventoryBaseline.objects.filter(group=reversal_group)
        .select_related("sku")
        .order_by("pk")
    )
    _require(len(main_baselines) == 1, "Expected exactly one main-group baseline.")
    _require(len(reversal_baselines) == 1, "Expected exactly one reversal-group baseline.")
    _require(
        not HistoryInventoryBaselineReversal.objects.filter(
            baseline=main_baselines[0]
        ).exists(),
        "Main baseline must remain active for the warehouse/lot movements.",
    )
    reversal_row = HistoryInventoryBaselineReversal.objects.filter(
        baseline=reversal_baselines[0],
        group=reversal_group,
    ).first()
    _require(reversal_row is not None, "Second baseline must have an official reversal row.")

    operational_links = list(
        HistoryOperationalContract.objects.filter(group=main_group).order_by("pk")
    )
    _require(
        len(operational_links) == 2,
        "Expected official sales and purchase HistoryOperationalContract rows.",
    )

    source = main_group.source_records.get(
        record_type="收付款流水",
        source_record_id=main_names["sales_tx_id"],
    )
    finance_handoff = main_group.handoffs.get(kind="finance")
    instruction_id = finance_handoff.payload.get(
        "operational_instructions", {}
    ).get(str(source.pk))
    _require(instruction_id is not None, "Historical finance source has no instruction mapping.")
    instruction = FinanceInstruction.objects.get(pk=instruction_id)
    _require(instruction.status == "posted", "Historical finance instruction is not posted.")
    _require(
        instruction.payload.get("truth") == "verified"
        and instruction.payload.get("source_system") == history_finance.SOURCE_SYSTEM,
        "Historical finance instruction has the wrong source or truth contract.",
    )
    fact = FinanceFact.objects.filter(instruction=instruction).first()
    _require(fact is not None and fact.truth == "verified", "Official history FinanceFact is missing.")
    _require(
        fact.source_system == history_finance.SOURCE_SYSTEM
        and fact.source_key == instruction.payload.get("source_key"),
        "Historical FinanceFact source identity does not match its instruction.",
    )
    voucher = FinanceVoucher.objects.get(pk=instruction.payload["voucher"])
    _require(fact.voucher_id == voucher.pk, "FinanceFact is not linked to its submitted private voucher.")
    voucher_manifest = _private_file_manifest(voucher)

    main_sku = main_baselines[0].sku
    reversal_sku = reversal_baselines[0].sku
    location = {
        "warehouse_type": WAREHOUSE_TYPE,
        "warehouse": f"HBK-WH-{tag}-{MAIN_SUFFIX}",
        "lot_reference": f"HBK-LOT-{tag}-{MAIN_SUFFIX}",
    }
    movements = list(
        InventoryMovement.objects.filter(sku_id=main_sku.pk).order_by("pk")
    )
    location_movements = [
        movement
        for movement in movements
        if all(getattr(movement, key) == value for key, value in location.items())
    ]
    _require(
        len(location_movements) >= 2
        and {movement.type for movement in location_movements} >= {"purchase_in", "sale_out"},
        "Expected official receipt and shipment movements at the non-default warehouse/lot.",
    )
    _require(
        not InventoryMovement.objects.filter(sku_id=reversal_sku.pk).exists(),
        "Reversal-group SKU must have no later movement that invalidates safe reversal.",
    )

    sale_link = next(link for link in operational_links if link.archived_order_id)
    purchase_link = next(link for link in operational_links if link.archived_purchase_id)
    sale = sale_link.continuation_order
    purchase = purchase_link.continuation_purchase
    receipt = GoodsReceipt.objects.get(purchase_item__purchase_order_id=purchase.pk)
    shipment = Shipment.objects.get(order_id=sale.pk)
    _require(
        receipt.inventory_movement_id in {row.pk for row in location_movements}
        and shipment.items.filter(inventory_movement__in=location_movements).exists(),
        "Receipt/shipment rows do not point to the non-default location movements.",
    )

    tag_usernames = (
        f"history-op-maker-{tag.lower()}",
        f"history-op-reviewer-{tag.lower()}",
    )
    users = [get_user_model().objects.get(username=name) for name in tag_usernames]
    _require(users[0].pk != users[1].pk, "Synthetic maker and reviewer must be distinct users.")

    seeded = {
        "tag": tag,
        "group_ids": [main_group.pk, reversal_group.pk],
        "application_ids": [main_group.application_id, reversal_group.application_id],
        "user_ids": [user.pk for user in users],
        "sku_ids": [main_sku.pk, reversal_sku.pk],
        "group_source_ids": {
            "main": main_names["group_id"],
            "reversal": reversal_names["group_id"],
        },
        "baseline_ids": [row.pk for row in main_baselines + reversal_baselines],
        "baseline_reversal_id": reversal_row.pk,
        "operational_contract_ids": [row.pk for row in operational_links],
        "finance_instruction_id": instruction.pk,
        "finance_fact_id": fact.pk,
        "private_voucher_id": voucher.pk,
        "receipt_id": receipt.pk,
        "shipment_id": shipment.pk,
        "movement_ids": [row.pk for row in location_movements],
    }
    return {
        "schema_version": 1,
        "kind": "synthetic-history-operational-backup-manifest",
        "hash_format": HASH_FORMAT,
        "seed": seeded,
        "tables": _table_inventory(),
        "new_table_rows": _new_table_rows(main_group, reversal_group),
        "private_vouchers": [voucher_manifest],
        "checks": {
            "official_history_groups": 2,
            "active_inventory_baselines": 1,
            "reversed_inventory_baselines": 1,
            "operational_contracts": 2,
            "posted_verified_history_facts": 1,
            "non_default_location_movements": len(location_movements),
            "receipt_and_shipment_linked": True,
            "synthetic_maker_reviewer_distinct": True,
        },
    }


def verify() -> dict:
    """Return complete row/sequence hashes and private-file evidence."""
    _guard_owned_postgres()
    return _current_manifest(_tag())


def _seed_inside(tag: str, created_files: list) -> dict:
    User = get_user_model()
    maker = User.objects.create_superuser(
        username=f"history-op-maker-{tag.lower()}",
        email=f"history-op-maker-{tag.lower()}@example.invalid",
        password=None,
    )
    reviewer = User.objects.create_superuser(
        username=f"history-op-reviewer-{tag.lower()}",
        email=f"history-op-reviewer-{tag.lower()}@example.invalid",
        password=None,
    )
    customer, supplier, main_sku, reversal_sku = _create_master_data(maker, tag)
    fixture = object.__new__(HistoryTakeoverFixtureMixin)
    fixture.customer = customer
    fixture.supplier = supplier
    fixture.product = main_sku.product
    fixture.sku = main_sku
    main_group, main_names = _archive_group(
        fixture,
        tag,
        MAIN_SUFFIX,
        main_sku,
        maker,
        reviewer,
    )
    fixture.sku = reversal_sku
    reversal_group, reversal_names = _archive_group(
        fixture,
        tag,
        REVERSAL_SUFFIX,
        reversal_sku,
        maker,
        reviewer,
    )

    fact = _finance_fact(
        main_group,
        main_names,
        maker,
        reviewer,
        tag,
        created_files,
    )
    _activate_inventory(
        main_group,
        main_names,
        main_sku,
        maker,
        reviewer,
    )

    _proposal, replay = contracts.propose(
        main_group.pk,
        _balance_payload(main_group, main_names, main_sku),
        maker,
    )
    if replay:
        raise RuntimeError("Unexpected operational contract proposal replay.")
    contracts.approve(
        main_group.pk,
        "Synthetic independent review of residual contracts and opening balances.",
        reviewer,
    )
    contract_ids, replay = contracts.execute(main_group.pk, maker)
    if replay or len(contract_ids) != 2:
        raise RuntimeError("Official operational contract service did not create both links.")

    _activate_inventory(
        reversal_group,
        reversal_names,
        reversal_sku,
        maker,
        reviewer,
        reverse_after=True,
    )
    _require(
        HistoryInventoryBaselineReversal.objects.filter(group=reversal_group).count() == 1,
        "Official inventory reversal did not create its append-only row.",
    )
    _fulfillment_rows(main_group, maker, tag)
    _require(FinanceFact.objects.filter(pk=fact.pk).exists(), "Posted finance fact disappeared.")
    return _current_manifest(tag)


def _cleanup_files(created_files: list) -> None:
    errors = []
    media_root = Path(settings.MEDIA_ROOT).resolve(strict=True)
    for storage, name in reversed(created_files):
        try:
            path = Path(storage.path(name)).resolve(strict=True)
            path.relative_to(media_root)
            storage.delete(name)
        except FileNotFoundError:
            continue
        except Exception as exc:
            errors.append(f"{name}: {exc}")
    if errors:
        raise RuntimeError(
            "Seed rolled back but private file cleanup failed: " + "; ".join(errors)
        )


def seed() -> dict:
    """Create a synthetic two-group fixture through reviewed official services."""
    _guard_owned_postgres()
    tag = _tag()
    main = _names(tag, MAIN_SUFFIX)
    reversal = _names(tag, REVERSAL_SUFFIX)
    already_started = HistoryTakeoverGroup.objects.filter(
        source_system__in=[main["source_system"], reversal["source_system"]],
        source_group_id__in=[main["group_id"], reversal["group_id"]],
    ).exists()
    if already_started:
        return verify()

    created_files = []
    try:
        with transaction.atomic():
            manifest = _seed_inside(tag, created_files)
        return manifest
    except Exception as original:
        try:
            _cleanup_files(created_files)
        except Exception as cleanup_error:
            raise RuntimeError(
                "History operational seed failed and uploaded file cleanup also failed: "
                f"{cleanup_error}"
            ) from original
        raise
