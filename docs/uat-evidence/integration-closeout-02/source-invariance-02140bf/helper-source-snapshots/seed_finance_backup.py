"""Synthetic finance fixtures and verifier for the ISS-018 owned PG drill.

This helper is evidence tooling, not application code. It may only run against
the task-owned temporary PostgreSQL cluster checked by the existing ISS-018
fixture guard. Financial facts are created through the finance_closeout and
cash_events services; the helper never writes finance models directly.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import uuid
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection, transaction
from django.test.utils import override_settings

from crm.models import (
    CashDuplicateReview,
    CashSourceAllocation,
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
    RmbCashEvent,
    Transaction,
)
from crm.services import cash_events, finance_closeout
from crm.tests.iss018_drill_fixture import _assert_synthetic_database


CORE_FINANCE_MODELS = (
    FinanceAccount,
    FinanceVoucher,
    FinanceBankVoucherBinding,
    FinanceInstruction,
    FinanceFact,
    FinanceAccountMapping,
    FinanceReview,
    FinanceTransferMatch,
    FinanceHistoricalTransfer,
    FinanceClassification,
)

# These existing cash-event tables are part of the references and private
# voucher path exercised by the new finance tables. Include them in the digest
# so a restore comparison also checks the old-bank mapping's source records.
SUPPORTING_CASH_MODELS = (
    RmbCashEvent,
    CashDuplicateReview,
    CashSourceAllocation,
)

HASHED_MODELS = CORE_FINANCE_MODELS + SUPPORTING_CASH_MODELS
HASH_FORMAT = "sha256 of each concrete-field row as canonical UTF-8 JSON, ordered by primary key, one LF after each row"


def _guard_owned_postgres() -> None:
    """Apply the shared ISS-018 ownership guard before reading or writing data."""
    _assert_synthetic_database()
    if connection.vendor != "postgresql":
        raise RuntimeError("Synthetic finance seed requires the owned PostgreSQL drill; SQLite is not accepted")


def _canonical(value):
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, (date,)):
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


def _table_digest(model) -> dict:
    hasher = hashlib.sha256()
    count = 0
    fields = model._meta.concrete_fields
    for row in model._default_manager.order_by("pk").iterator(chunk_size=1000):
        payload = {
            field.attname: _canonical(getattr(row, field.attname))
            for field in fields
        }
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        hasher.update(encoded)
        hasher.update(b"\n")
        count += 1
    return {
        "model": model._meta.label,
        "rows": count,
        "sha256": hasher.hexdigest(),
    }


def _voucher_file_digest(voucher) -> dict:
    if not voucher.file or not voucher.file.name:
        raise RuntimeError(f"FinanceVoucher {voucher.pk} has no stored file")

    media_root = Path(settings.MEDIA_ROOT).resolve(strict=True)
    try:
        path = Path(voucher.file.path).resolve(strict=True)
        path.relative_to(media_root)
    except (OSError, ValueError, NotImplementedError) as exc:
        raise RuntimeError(
            f"FinanceVoucher {voucher.pk} is not a regular file inside the owned drill MEDIA_ROOT"
        ) from exc
    if not path.is_file():
        raise RuntimeError(f"FinanceVoucher {voucher.pk} does not resolve to a regular file")

    hasher = hashlib.sha256()
    size = 0
    try:
        with voucher.file.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                hasher.update(chunk)
                size += len(chunk)
    except (OSError, ValueError) as exc:
        raise RuntimeError(f"FinanceVoucher {voucher.pk} could not be read") from exc

    actual_sha256 = hasher.hexdigest()
    if size != voucher.size or actual_sha256 != voucher.sha256:
        raise RuntimeError(f"FinanceVoucher {voucher.pk} bytes disagree with stored SHA256/size")
    return {
        "id": voucher.pk,
        "name": voucher.file.name,
        "scope": voucher.scope,
        "bank_sources": _canonical(voucher.bank_sources),
        "stored_sha256": voucher.sha256,
        "stored_size": voucher.size,
        "file_sha256": actual_sha256,
        "file_size": size,
    }


def _inventory() -> dict:
    tables = {model._meta.db_table: _table_digest(model) for model in HASHED_MODELS}
    vouchers = [
        _voucher_file_digest(voucher)
        for voucher in FinanceVoucher.objects.order_by("pk").iterator(chunk_size=500)
    ]
    return {
        "schema_version": 1,
        "kind": "iss018-synthetic-finance-backup-manifest",
        "hash_format": HASH_FORMAT,
        "tables": tables,
        "private_vouchers": vouchers,
    }


def verify(expected: dict | str | Path | None = None) -> dict:
    """Return the current inventory, optionally comparing it with source data.

    Call with no argument on the source database and preserve the returned
    dictionary as the comparison manifest. Call with that dictionary on the
    restored database. A path to its UTF-8 JSON encoding is also accepted.
    This function is read-only apart from the database identity query made by
    the required synthetic-database guard.
    """
    _guard_owned_postgres()
    if isinstance(expected, (str, Path)):
        expected = json.loads(Path(expected).read_text(encoding="utf-8"))
    actual = _inventory()
    if expected is None:
        return actual
    if not isinstance(expected, dict) or expected.get("schema_version") != 1:
        raise ValueError("Expected finance manifest must be a schema_version 1 object")
    if expected.get("kind") != actual["kind"] or expected.get("hash_format") != HASH_FORMAT:
        raise ValueError("Expected finance manifest kind or hash format does not match")

    expected_tables = expected.get("tables")
    expected_vouchers = expected.get("private_vouchers")
    if not isinstance(expected_tables, dict) or not isinstance(expected_vouchers, list):
        raise ValueError("Expected finance manifest is missing tables or private_vouchers")

    result = {"ok": True, "actual": actual, "differences": []}
    if expected_tables != actual["tables"]:
        table_names = sorted(set(expected_tables) | set(actual["tables"]))
        for table_name in table_names:
            if expected_tables.get(table_name) != actual["tables"].get(table_name):
                result["differences"].append({
                    "kind": "table",
                    "table": table_name,
                    "expected": expected_tables.get(table_name),
                    "actual": actual["tables"].get(table_name),
                })

    if expected_vouchers != actual["private_vouchers"]:
        expected_by_id = {row.get("id"): row for row in expected_vouchers if isinstance(row, dict)}
        actual_by_id = {row["id"]: row for row in actual["private_vouchers"]}
        for voucher_id in sorted(set(expected_by_id) | set(actual_by_id), key=lambda item: (item is None, item)):
            if expected_by_id.get(voucher_id) != actual_by_id.get(voucher_id):
                result["differences"].append({
                    "kind": "private_voucher_file",
                    "id": voucher_id,
                    "expected": expected_by_id.get(voucher_id),
                    "actual": actual_by_id.get(voucher_id),
                })

    result["ok"] = not result["differences"]
    return result


def _pdf(name: str, label: str) -> SimpleUploadedFile:
    data = (
        b"%PDF-1.4\n"
        + f"Synthetic ISS-018 drill voucher: {label}\n".encode("ascii")
        + b"%%EOF\n"
    )
    return SimpleUploadedFile(name, data, content_type="application/pdf")


def _remember_uploaded_voucher(voucher, created_files: list) -> None:
    storage = FinanceVoucher._meta.get_field("file").storage
    created_files.append((storage, voucher.file.name))


def _verified_bank_account(*, code: str, name: str, maker):
    account = finance_closeout.create_account({
        "code": code,
        "name": name,
        "account_type": "bank",
        "ownership": "unverified",
    }, maker)
    return finance_closeout.verify_account({
        "account": account.pk,
        "ownership": "own",
        "reason": "仅供 ISS-018 一次性隔离 PostgreSQL 备份演练的合成账户。",
    }, maker)


def _post_fact(*, maker, reviewer, account, voucher, tag: str, key: str,
               kind: str, amount: str, direction: str, nature: str,
               actual_date: date, parent: int | None = None,
               legacy_parent: int | None = None):
    payload = {
        "request_key": f"ISS018-FIN-{tag}-{key}",
        "kind": kind,
        "account": account.pk,
        "voucher": voucher.pk,
        "actual_date": actual_date.isoformat(),
        "amount": amount,
        "direction": direction,
        "nature": nature,
        "truth": "verified",
        "source_system": f"ISS018_SYNTHETIC_{tag}",
        "source_key": key,
        "reason": "合成隔离 PostgreSQL 备份演练资料；不代表真实银行资金。",
    }
    if parent is not None:
        payload["parent"] = parent
    if legacy_parent is not None:
        payload["legacy_parent"] = legacy_parent
    instruction, created = finance_closeout.submit(payload, maker)
    if not created:
        raise RuntimeError(f"Unexpected duplicate synthetic finance request: {payload['request_key']}")
    if instruction.kind in finance_closeout.APPROVAL_KINDS:
        finance_closeout.approve(instruction.pk, reviewer)
    return finance_closeout.post(instruction.pk, maker, voucher_checked=True)


def seed() -> dict:
    """Create synthetic finance records through official services and return hashes.

    Requires the core ISS-018 seed to have created its confirmed ISS018-TX
    foreign-currency source transaction first. Use a fresh owned drill database
    because this helper consumes that source's remaining cash-event allocation.
    """
    _guard_owned_postgres()

    source = Transaction.objects.filter(transaction_no="ISS018-TX").first()
    if source is None:
        raise RuntimeError("Run iss018_drill_fixture.seed() first; confirmed source ISS018-TX is required")
    if source.status != "confirmed" or source.direction != "income" or source.currency == "CNY":
        raise RuntimeError("ISS018-TX must be a confirmed foreign-currency income source")
    if source.currency not in cash_events.UNITS:
        raise RuntimeError(f"ISS018-TX currency is unsupported by cash_events: {source.currency}")

    unit = cash_events.UNITS[source.currency]
    source_amount = Decimal(source.amount)
    rounded_source_amount = source_amount.quantize(unit)
    if source_amount != rounded_source_amount or rounded_source_amount <= 0:
        raise RuntimeError("ISS018-TX amount does not fit the official cash_events currency precision")
    if cash_events.available(source) < rounded_source_amount:
        raise RuntimeError("ISS018-TX has already been allocated; use a fresh owned drill database")

    tag = uuid.uuid4().hex[:10].upper()
    username_maker = f"iss018-fin-maker-{tag.lower()}"
    username_reviewer = f"iss018-fin-reviewer-{tag.lower()}"
    source_account_code = f"SYNTH-FX-{tag}"
    legacy_account_code = f"LEGACY-CNY-{tag}"
    account_a_code = f"FIN-BANK-A-{tag}"
    account_b_code = f"FIN-BANK-B-{tag}"
    bank_net_amount = (rounded_source_amount * Decimal("7")).quantize(Decimal("0.01"))
    source_amount_text = format(rounded_source_amount, "f")
    bank_net_text = format(bank_net_amount, "f")
    bank_date = source.transaction_date
    opening_date = bank_date - timedelta(days=1)
    created_files = []

    User = get_user_model()
    try:
        # Limit the legacy bank identifiers accepted by cash_events to these
        # synthetic values for the duration of this helper call only.
        with override_settings(RMB_CASH_ACCOUNT_IDS=(source_account_code, legacy_account_code)):
            with transaction.atomic():
                maker = User.objects.create_superuser(
                    username=username_maker,
                    email=f"{username_maker}@example.invalid",
                    password=None,
                )
                reviewer = User.objects.create_superuser(
                    username=username_reviewer,
                    email=f"{username_reviewer}@example.invalid",
                    password=None,
                )

                account_a = _verified_bank_account(
                    code=account_a_code, name=f"合成银行账户A-{tag}", maker=maker,
                )
                account_b = _verified_bank_account(
                    code=account_b_code, name=f"合成银行账户B-{tag}", maker=maker,
                )

                account_voucher = finance_closeout.upload(
                    _pdf(f"iss018-account-{tag}.pdf", f"account-{tag}"), maker,
                )
                _remember_uploaded_voucher(account_voucher, created_files)
                bank_voucher = finance_closeout.upload(
                    _pdf(f"iss018-bank-{tag}.pdf", f"bank-{tag}"),
                    maker,
                    bank_sources=[source.pk],
                )
                _remember_uploaded_voucher(bank_voucher, created_files)

                bank_event_payload = {
                    "event_no": f"ISS018-FIN-EVENT-{tag}",
                    "request_key": f"ISS018-FIN-CASH-{tag}",
                    "kind": "fx_settlement",
                    "currency": source.currency,
                    "direction": "income",
                    "bank_date": bank_date.isoformat(),
                    "bank_net_amount": bank_net_text,
                    "fee_mode": "none",
                    "fee_amount": "0.00",
                    "source_account": source_account_code,
                    "rmb_account": legacy_account_code,
                    "bank_reference": f"SYNTH-REF-{tag}",
                    "bank_counterparty": "Synthetic drill counterparty",
                    "bank_summary": "Synthetic bank credit for backup verification only",
                    "bank_transaction_id": f"SYNTH-BANK-TX-{tag}",
                    "evidence_reference": f"private-voucher-{tag}",
                    "evidence_sha256": bank_voucher.sha256,
                    "evidence_note": "合成凭证，仅用于隔离 PostgreSQL 备份校验。",
                    "quoted_rate": "7.000000",
                    "sources": [{
                        "transaction_id": source.pk,
                        "amount": source_amount_text,
                        "verified": True,
                    }],
                    "private_voucher": bank_voucher.pk,
                }
                bank_event, created = cash_events.register_event(bank_event_payload, maker)
                if not created:
                    raise RuntimeError("Unexpected duplicate synthetic bank event")
                bank_event = cash_events.confirm_event(
                    bank_event.pk,
                    maker,
                    voucher_checked=True,
                )
                if bank_event.status != "confirmed":
                    raise RuntimeError("Synthetic legacy bank event did not reach confirmed state")

                mapping = finance_closeout.map_account({
                    "account": account_b.pk,
                    "legacy_code": legacy_account_code,
                    "reason": "将本次合成旧银行账户明确映射到合成账户B。",
                }, maker)

                opening = _post_fact(
                    maker=maker, reviewer=reviewer, account=account_b,
                    voucher=account_voucher, tag=tag, key="OPENING-B",
                    kind="opening", amount="1000.00", direction="income",
                    nature="unclassified", actual_date=opening_date,
                )
                if opening.kind != "opening":
                    raise RuntimeError("Synthetic opening fact was not posted")

                transfer_out = _post_fact(
                    maker=maker, reviewer=reviewer, account=account_a,
                    voucher=account_voucher, tag=tag, key="TRANSFER-OUT-A",
                    kind="cash", amount="20.00", direction="expense",
                    nature="internal_principal", actual_date=bank_date,
                )
                transfer_in = _post_fact(
                    maker=maker, reviewer=reviewer, account=account_b,
                    voucher=account_voucher, tag=tag, key="TRANSFER-IN-B",
                    kind="cash", amount="20.00", direction="income",
                    nature="internal_principal", actual_date=bank_date,
                )
                transfer_match = finance_closeout.match_transfer({
                    "outgoing": transfer_out.pk,
                    "incoming": transfer_in.pk,
                    "reason": "合成两端银行凭证的转账本金核实。",
                }, maker)

                classified_fact = _post_fact(
                    maker=maker, reviewer=reviewer, account=account_a,
                    voucher=account_voucher, tag=tag, key="CLASSIFY-ME",
                    kind="cash", amount="8.00", direction="income",
                    nature="unclassified", actual_date=bank_date,
                )
                classification = finance_closeout.classify({
                    "fact": classified_fact.pk,
                    "nature": "interest",
                    "reason": "合成利息分类记录，用于新表备份验证。",
                }, reviewer)

                historical_out = _post_fact(
                    maker=maker, reviewer=reviewer, account=account_a,
                    voucher=account_voucher, tag=tag, key="HISTORICAL-OUT-A",
                    kind="cash", amount=bank_net_text, direction="expense",
                    nature="internal_principal", actual_date=bank_date,
                )
                historical_transfer = finance_closeout.match_historical_transfer({
                    "outgoing": f"fact:{historical_out.pk}",
                    "incoming": f"legacy:{bank_event.pk}",
                    "outgoing_voucher": account_voucher.pk,
                    "incoming_voucher": account_voucher.pk,
                    "reason": "合成历史银行转出与既有银行入账的等额核实。",
                }, reviewer)

                calculated, _fingerprint = finance_closeout.balance(
                    account_b, bank_date.isoformat(), maker,
                )
                if calculated is None:
                    raise RuntimeError("Synthetic account B has no opening balance for reconciliation")
                review = finance_closeout.reconcile({
                    "account": account_b.pk,
                    "date_from": opening_date.isoformat(),
                    "date_to": bank_date.isoformat(),
                    "voucher": account_voucher.pk,
                    "statement_balance": format(calculated, "f"),
                    "completed": True,
                    "reason": "以合成资料完成的账户余额核对，仅用于备份演练。",
                }, maker)
                if not review.completed:
                    raise RuntimeError("Synthetic account reconciliation did not complete")

                manifest = _inventory()
                manifest["seed"] = {
                    "tag": tag,
                    "source_transaction_id": source.pk,
                    "maker_user_id": maker.pk,
                    "reviewer_user_id": reviewer.pk,
                    "account_ids": [account_a.pk, account_b.pk],
                    "mapping_id": mapping.pk,
                    "legacy_bank_event_id": bank_event.pk,
                    "voucher_ids": [account_voucher.pk, bank_voucher.pk],
                    "opening_fact_id": opening.pk,
                    "transfer_match_id": transfer_match.pk,
                    "classification_id": classification.pk,
                    "historical_transfer_id": historical_transfer.pk,
                    "review_id": review.pk,
                }
    except Exception as original:
        cleanup_errors = []
        for storage, name in reversed(created_files):
            try:
                path = Path(storage.path(name)).resolve(strict=True)
                media_root = Path(settings.MEDIA_ROOT).resolve(strict=True)
                path.relative_to(media_root)
                storage.delete(name)
            except FileNotFoundError:
                continue
            except Exception as cleanup_error:  # report cleanup failures without hiding the seed error
                cleanup_errors.append(f"{name}: {cleanup_error}")
        if cleanup_errors:
            raise RuntimeError(
                f"Synthetic finance seed rolled back; private file cleanup failed: {'; '.join(cleanup_errors)}"
            ) from original
        raise
    return manifest


def _cli() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("seed", "verify"))
    parser.add_argument("manifest", nargs="?", help="source manifest JSON for restore verification")
    args = parser.parse_args()
    if args.command == "seed":
        result = seed()
        exit_code = 0
    else:
        result = verify(args.manifest) if args.manifest else verify()
        exit_code = 0 if not args.manifest or result["ok"] else 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(_cli())
