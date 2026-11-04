"""Read-only assertions and sanitized SQLite copy for the 447d Chrome UAT."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
from decimal import Decimal
from pathlib import Path

import django

django.setup()

from django.conf import settings

from test_support.isolated_runtime import verify_isolated_runtime
from crm.models import (
    FinanceAccount,
    FinanceFact,
    FinanceInstruction,
    FinanceVoucher,
    FulfillmentIdempotency,
    GoodsReceipt,
    HistoryInventoryBaseline,
    HistoryOperationalContract,
    HistoryTakeoverApplication,
    HistoryTakeoverEvent,
    HistoryTakeoverGroup,
    HistoryTakeoverSourceRecord,
    InventoryMovement,
    OperationLog,
    Order,
    PaymentPlan,
    PurchaseOrder,
    Shipment,
    ShipmentItem,
    SKU,
)


APP_NAME = "synthetic-history-uAT.xlsx"
SOURCE_SYSTEM = "Synthetic browser UAT"
GROUP_ID = "HT-UAT-447D-1"
RECEIPT_KEY = "synthetic-history-receipt-uat-1"
SHIPMENT_KEY = "synthetic-history-shipment-uat-1"


def _json_value(value):
    if isinstance(value, bytes):
        return {"blob_sha256": hashlib.sha256(value).hexdigest(), "size": len(value)}
    return value


def _table_manifest(database: Path):
    connection = sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True)
    try:
        tables = [row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )]
        manifest = {}
        for table in tables:
            quoted = '"' + table.replace('"', '""') + '"'
            cursor = connection.execute(f"SELECT * FROM {quoted} ORDER BY rowid")
            digest = hashlib.sha256()
            count = 0
            for row in cursor:
                encoded = json.dumps([_json_value(value) for value in row], ensure_ascii=False,
                                     sort_keys=True, separators=(",", ":")).encode("utf-8")
                digest.update(encoded + b"\n")
                count += 1
            manifest[table] = {"rows": count, "sha256": digest.hexdigest()}
        return manifest
    finally:
        connection.close()


def _sanitize_database(destination: Path):
    source = Path(os.environ["ISOLATED_TEST_DATABASE"]).resolve(strict=True)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise RuntimeError(f"Refusing to overwrite existing published database copy: {destination}")
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    source_manifest = _table_manifest(source)
    source_connection = sqlite3.connect(f"file:{source.as_posix()}?mode=ro", uri=True)
    target_connection = sqlite3.connect(destination)
    try:
        source_connection.backup(target_connection)
        session_count = target_connection.execute("SELECT COUNT(*) FROM django_session").fetchone()[0]
        target_connection.execute("DELETE FROM django_session")
        target_connection.commit()
    finally:
        target_connection.close()
        source_connection.close()
    target_manifest = _table_manifest(destination)
    non_session_tables = sorted(set(source_manifest) | set(target_manifest) - {"django_session"})
    differences = [
        name for name in non_session_tables
        if name != "django_session" and source_manifest.get(name) != target_manifest.get(name)
    ]
    if differences:
        raise RuntimeError(f"Sanitized copy changed non-session tables: {differences}")
    published_hash = hashlib.sha256(destination.read_bytes()).hexdigest()
    return {
        "source_database": str(source),
        "source_sha256": source_hash,
        "published_database": str(destination),
        "published_sha256": published_hash,
        "django_session_rows_removed_from_published_copy": session_count,
        "source_table_count": len(source_manifest),
        "published_table_count": len(target_manifest),
        "business_and_audit_tables_unchanged": not differences,
        "business_and_audit_rows": sum(value["rows"] for name, value in target_manifest.items() if name != "django_session"),
        "business_and_audit_manifest_sha256": hashlib.sha256(json.dumps(
            {name: value for name, value in sorted(target_manifest.items()) if name != "django_session"},
            sort_keys=True, separators=(",", ":"),
        ).encode("utf-8")).hexdigest(),
    }


def _verify_business_state():
    verify_isolated_runtime(settings=settings, database_must_exist=True)
    application = HistoryTakeoverApplication.objects.get(source_file_name=APP_NAME)
    groups = list(application.groups.filter(source_group_id=GROUP_ID, source_system=SOURCE_SYSTEM))
    if application.groups.count() != 1 or len(groups) != 1:
        raise RuntimeError("Expected exactly one synthetic source group in one submitted application.")
    group = groups[0]
    if group.status != "executed":
        raise RuntimeError(f"History group did not reach executed state; actual={group.status!r}.")

    account = FinanceAccount.objects.get(code="UAT-HISTORY-CNY")
    voucher = FinanceVoucher.objects.get(original_name="synthetic-uat.pdf")
    voucher_path = Path(settings.MEDIA_ROOT) / voucher.file.name
    if not voucher_path.is_file() or voucher_path.is_symlink():
        raise RuntimeError("Synthetic finance voucher is missing or not a regular file.")
    voucher_bytes = voucher_path.read_bytes()
    voucher_sha = hashlib.sha256(voucher_bytes).hexdigest()
    if voucher_sha != voucher.sha256 or len(voucher_bytes) != voucher.size:
        raise RuntimeError("Synthetic finance voucher bytes do not match the stored digest/size.")

    idempotency = list(FulfillmentIdempotency.objects.filter(key__in=[RECEIPT_KEY, SHIPMENT_KEY]).order_by("key"))
    if len(idempotency) != 2 or {row.key for row in idempotency} != {RECEIPT_KEY, SHIPMENT_KEY}:
        raise RuntimeError("Expected one committed idempotency record for receipt and one for shipment.")
    if any(row.status != "succeeded" for row in idempotency):
        raise RuntimeError("A synthetic fulfillment idempotency record is not succeeded.")
    idempotency_by_key = {row.key: row for row in idempotency}
    if idempotency_by_key[RECEIPT_KEY].operation != "receive" or idempotency_by_key[SHIPMENT_KEY].operation != "ship":
        raise RuntimeError("Fulfillment idempotency operation names do not match the request keys.")
    receipt_payload = idempotency_by_key[RECEIPT_KEY].response_payload
    shipment_payload = idempotency_by_key[SHIPMENT_KEY].response_payload
    if not isinstance(receipt_payload, dict) or not isinstance(shipment_payload, dict):
        raise RuntimeError("Fulfillment idempotency response payloads are not structured objects.")
    # The API stores the idempotency key in FulfillmentIdempotency and returns
    # the linked record's primary key in response_payload. GoodsReceipt and
    # Shipment request_key fields are optional legacy model fields and remain
    # null for this service path.
    receipt = GoodsReceipt.objects.get(pk=receipt_payload.get("id"))
    shipment = Shipment.objects.get(pk=shipment_payload.get("id"))
    if idempotency_by_key[RECEIPT_KEY].target_id != receipt.purchase_item.purchase_order_id:
        raise RuntimeError("Receipt idempotency record points to a different purchase order.")
    if idempotency_by_key[SHIPMENT_KEY].target_id != shipment.order_id:
        raise RuntimeError("Shipment idempotency record points to a different order.")
    shipment_quantity = sum(ShipmentItem.objects.filter(shipment=shipment).values_list("quantity", flat=True), Decimal("0"))
    if receipt.quantity != Decimal("3.00") or shipment_quantity != Decimal("6.00"):
        raise RuntimeError(f"Expected receipt 3 and shipment 6; got {receipt.quantity} and {shipment_quantity}.")

    order = Order.objects.get(order_no="HIST-SO-HT-1")
    purchase = PurchaseOrder.objects.get(purchase_no="HIST-PO-HT-1")
    contracts = list(HistoryOperationalContract.objects.filter(group=group).select_related(
        "continuation_order", "continuation_purchase", "settlement_order", "settlement_purchase"
    ).order_by("id"))
    baselines = list(HistoryInventoryBaseline.objects.filter(group=group).order_by("id"))
    facts = list(FinanceFact.objects.filter(account=account).select_related("instruction").order_by("id"))
    if len(facts) != 2:
        raise RuntimeError(f"Expected two actual finance facts from the synthetic workflow; got {len(facts)}.")
    if len(baselines) != 1 or len(contracts) != 2:
        raise RuntimeError(f"Expected one inventory baseline and two continuation contracts; got {len(baselines)} and {len(contracts)}.")

    event_rows = list(HistoryTakeoverEvent.objects.filter(application=application).order_by("id").values(
        "event_type", "actor_label", "actor_kind"
    ))
    if not event_rows:
        raise RuntimeError("Synthetic history event audit rows are missing.")
    audit_count = OperationLog.objects.count()
    table_manifest = _table_manifest(Path(settings.DATABASES["default"]["NAME"]))
    summary = {
        "isolation": {
            "database_engine": settings.DATABASES["default"]["ENGINE"],
            "database_path": str(Path(settings.DATABASES["default"]["NAME"]).resolve()),
            "media_root": str(Path(settings.MEDIA_ROOT).resolve()),
            "audit_log_enabled": settings.AUDIT_LOG_ENABLED,
            "development_superadmin_enabled": settings.DEVELOPMENT_SUPERADMIN,
            "rbac_enforcement": settings.RBAC_ENFORCEMENT,
            "development_name_is_not_real_employee_identity": True,
            "synthetic_dual_session_is_not_real_employee_acceptance": True,
        },
        "history": {
            "application_id": application.pk,
            "source_file_name": application.source_file_name,
            "source_system": group.source_system,
            "source_group_id": group.source_group_id,
            "application_status": application.status,
            "group_status": group.status,
            "created_actor_kind": application.created_actor_kind,
            "created_by_label": application.created_by_label,
            "reviewed_actor_kind": application.reviewed_actor_kind,
            "reviewed_by_label": application.reviewed_by_label,
            "source_record_rows": HistoryTakeoverSourceRecord.objects.filter(group=group).count(),
            "event_rows": event_rows,
            "archived_order": {"id": order.pk, "order_no": order.order_no, "status": order.status},
            "archived_purchase": {"id": purchase.pk, "purchase_no": purchase.purchase_no, "status": purchase.status},
        },
        "finance": {
            "account_code": account.code,
            "account_ownership": account.ownership,
            "voucher_name": voucher.original_name,
            "voucher_file_relative_path": voucher.file.name,
            "voucher_size": voucher.size,
            "voucher_sha256": voucher_sha,
            "facts": [{"id": fact.pk, "kind": fact.kind, "direction": fact.direction,
                       "amount": str(fact.amount), "instruction_status": fact.instruction.status,
                       "source_system": fact.source_system, "source_key": fact.source_key} for fact in facts],
            "finance_instructions": FinanceInstruction.objects.count(),
        },
        "inventory": {
            "baseline_count": len(baselines),
            "baselines": [{"id": row.pk, "sku": row.sku.sku, "warehouse_type": row.warehouse_type,
                           "warehouse": row.warehouse, "lot_reference": row.lot_reference,
                           "quantity": str(row.quantity), "cost_currency": row.cost_currency} for row in baselines],
            "inventory_movements": InventoryMovement.objects.count(),
        },
        "continuation": {
            "contract_count": len(contracts),
            "contracts": [{"id": row.pk, "balance_mode": row.balance_mode,
                           "continuation_order_id": row.continuation_order_id,
                           "continuation_purchase_id": row.continuation_purchase_id,
                           "settlement_order_id": row.settlement_order_id,
                           "settlement_purchase_id": row.settlement_purchase_id} for row in contracts],
            "payment_plan_count": PaymentPlan.objects.count(),
        },
        "fulfillment": {
            "receipt_id": receipt.pk,
            "receipt_quantity": str(receipt.quantity),
            "shipment_id": shipment.pk,
            "shipment_quantity": str(shipment_quantity),
            "idempotency": [{"key": row.key, "operation": row.operation, "status": row.status,
                             "response_status": row.response_status} for row in idempotency],
        },
        "audit": {
            "history_event_count": len(event_rows),
            "operation_log_count": audit_count,
        },
        "database_tables": table_manifest,
    }
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--sanitize-db", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--allow-incomplete", action="store_true")
    args = parser.parse_args()
    if args.sanitize_db:
        result = _sanitize_database(args.sanitize_db.resolve())
    else:
        result = _verify_business_state()
    payload = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")


if __name__ == "__main__":
    main()
