"""Populate and compare synthetic finance history around a migration upgrade.

Run only against a disposable database, with DATABASE_URL set explicitly.
"""
import json
import os
import sys
from datetime import date
from decimal import Decimal

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

MODE, PHASE = sys.argv[1:3]
if connection.vendor != "postgresql" or connection.settings_dict["HOST"] != "127.0.0.1" or not connection.settings_dict["NAME"].startswith("fic_"):
    raise RuntimeError("Probe requires a dedicated local PostgreSQL database named fic_*.")
TARGET = {
    "c978": ("crm", "0120_advanceallocation_cash_amount_and_more"),
    "c90": ("crm", "0122_merge_sales_and_finance_review"),
}[MODE]
apps = MigrationExecutor(connection).loader.project_state([TARGET]).apps if PHASE == "seed" else django.apps.apps


def model(name):
    return apps.get_model("crm", name)


def seed():
    customer = model("Customer").objects.create(code="SYNTH-MIGRATION", name="Synthetic migration buyer")
    order = model("Order").objects.create(order_no="SYNTH-MIGRATION", customer=customer, order_date=date(2026, 11, 1), currency="USD", exchange_rate=7, status="confirmed")
    plan = model("PaymentPlan").objects.create(order=order, direction="receivable", currency="USD", planned_amount=100, settled_amount=80, status="open")
    values = dict(transaction_no="SYNTH-MIGRATION", transaction_date=date(2026, 11, 1), kind="unallocated_advance", direction="income", category="synthetic", amount=80, currency="USD", exchange_rate=7, customer=customer, status="confirmed", allocated_amount=80)
    if MODE == "c978":
        values.update(exchange_rate=None, reference_rate_missing=True)
    receipt = model("Transaction").objects.create(**values)
    allocation = model("AdvanceAllocation").objects.create(advance=receipt, plan=plan, amount=80, cash_amount=80, fee_credit_amount=0)
    writeoff = model("FinancePlanWriteoff").objects.create(plan=plan, source_transaction=receipt, amount=10, reason="synthetic basis", request_key="migration-writeoff", request_hash="synthetic", confirmed_actor={})
    if MODE == "c978":
        proof = model("FinanceVoucher").objects.create(original_name="synthetic.pdf", file="synthetic.pdf", sha256="a" * 64, size=1, scope="transaction", actor={})
        model("FinanceReceiptAdjustment").objects.create(transaction=receipt, plan=plan, order=order, nature="discount", handling="applied", amount=10, currency="USD", reason="synthetic basis", evidence=proof, writeoff=writeoff, actor={})
    else:
        model("FinancePlanWriteoffCorrection").objects.create(writeoff=writeoff, amount=4, reason="synthetic correction", request_key="migration-correction", request_hash="synthetic", actor={})
    print("seeded", receipt.pk, allocation.pk, writeoff.pk)


def verify():
    receipt = model("Transaction").objects.get(transaction_no="SYNTH-MIGRATION")
    allocation = model("AdvanceAllocation").objects.get(advance=receipt)
    writeoff = model("FinancePlanWriteoff").objects.get(source_transaction=receipt)
    assert (allocation.amount, allocation.cash_amount, allocation.fee_credit_amount) == (Decimal("80"), Decimal("80"), Decimal("0"))
    assert writeoff.amount == Decimal("10")
    with connection.cursor() as cursor:
        constraints = connection.introspection.get_constraints(cursor, model("AdvanceAllocation")._meta.db_table)
    assert {"advance_allocation_cash_nonnegative", "advance_allocation_fee_nonnegative", "advance_allocation_split_matches"} <= constraints.keys()
    if MODE == "c978":
        assert receipt.exchange_rate is None and receipt.reference_rate_missing
        adjustment = model("FinanceReceiptAdjustment").objects.get(transaction=receipt)
        assert adjustment.evidence_id and adjustment.writeoff_id == writeoff.pk and adjustment.amount == Decimal("10")
        from crm.serializers import TransactionSerializer
        assert TransactionSerializer(receipt).data["rmb_amount"] is None
    else:
        correction = model("FinancePlanWriteoffCorrection").objects.get(writeoff=writeoff)
        assert correction.amount == Decimal("4")
    print(json.dumps({"mode": MODE, "receipt": receipt.pk, "allocation": allocation.pk, "writeoff": writeoff.pk, "verified": True}))


seed() if PHASE == "seed" else verify()
