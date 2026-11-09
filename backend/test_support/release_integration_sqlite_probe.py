"""Check the three integration migration entry points using disposable SQLite databases."""
import os
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory


def run():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"
    with TemporaryDirectory(prefix="sunjack-release-migrations-") as directory:
        root = Path(directory)
        os.environ["DATABASE_URL"] = f"sqlite:///{(root / 'fresh.sqlite3').as_posix()}"
        import django

        django.setup()
        from django.db import connection
        from django.db.migrations.executor import MigrationExecutor

        assert connection.vendor == "sqlite"
        for name, entry in [
            ("fresh", None),
            ("c978", "0120_advanceallocation_cash_amount_and_more"),
            ("c90", "0122_merge_sales_and_finance_review"),
        ]:
            connection.settings_dict["NAME"] = str(root / f"{name}.sqlite3")
            try:
                executor = MigrationExecutor(connection)
                sample = None
                if entry:
                    target = ("crm", entry)
                    executor.migrate([target])
                    sample = seed(executor.loader.project_state([target]).apps, name)
                executor = MigrationExecutor(connection)
                executor.migrate(executor.loader.graph.leaf_nodes())
                applied = MigrationExecutor(connection).loader.applied_migrations
                assert ("crm", "0128_merge_release_integration") in applied
                if entry:
                    assert ("crm", entry) in applied
                    verify(connection, name, sample)
                print(f"{name} => 0128 PASS", flush=True)
            finally:
                connection.close()


def seed(apps, name):
    def m(model):
        return apps.get_model("crm", model)

    when = date(2026, 11, 1)
    customer = m("Customer").objects.create(code="SYNTH-RELEASE", name="Synthetic", country="US")
    order = m("Order").objects.create(
        order_no="SYNTH-RELEASE", customer=customer, order_date=when, currency="USD", exchange_rate=7,
        status="historical", historical_only=True, customer_country_snapshot="CA",
    )
    product = m("Product").objects.create(code="SYNTH-P", name="Synthetic product")
    sku = m("SKU").objects.create(sku="SYNTH-SKU", product=product, currency="USD", cost_price=12)
    item = m("OrderItem").objects.create(order=order, sku=sku, quantity=1, unit_price=100, cost_price=9)
    plan = m("PaymentPlan").objects.create(
        order=order, direction="receivable", currency="USD", planned_amount=100, settled_amount=80, status="open",
    )
    rate = {"exchange_rate": None, "reference_rate_missing": True} if name == "c978" else {"exchange_rate": 7}
    receipt = m("Transaction").objects.create(
        transaction_no="SYNTH-RELEASE", transaction_date=when, kind="unallocated_advance", direction="income",
        category="synthetic", amount=80, currency="USD", customer=customer, status="confirmed", allocated_amount=80,
        **rate,
    )
    allocation = m("AdvanceAllocation").objects.create(
        advance=receipt, plan=plan, amount=80, cash_amount=75, fee_credit_amount=5,
    )
    writeoff = m("FinancePlanWriteoff").objects.create(
        plan=plan, source_transaction=receipt, amount=10, reason="synthetic",
        request_key="release-writeoff", request_hash="synthetic", confirmed_actor={},
    )
    if name == "c978":
        proof = m("FinanceVoucher").objects.create(
            original_name="synthetic.pdf", file="synthetic.pdf", sha256="a" * 64, size=1, scope="transaction", actor={},
        )
        m("FinanceReceiptAdjustment").objects.create(
            transaction=receipt, plan=plan, order=order, nature="discount", handling="applied", amount=10,
            currency="USD", reason="synthetic", evidence=proof, writeoff=writeoff, actor={},
        )
        related = proof.pk
    else:
        related = m("FinancePlanWriteoffCorrection").objects.create(
            writeoff=writeoff, amount=4, reason="synthetic", request_key="release-correction",
            request_hash="synthetic", actor={},
        ).pk
    content_type = apps.get_model("contenttypes", "ContentType").objects.create(app_label="crm", model="transaction")
    audit = m("OperationLog").objects.create(
        content_type=content_type, object_id=str(receipt.pk), entity="transaction", action="create",
        after_data={"amount": "80"},
    )
    return order.pk, item.pk, receipt.pk, allocation.pk, writeoff.pk, related, audit.pk


def verify(connection, name, sample):
    from crm.models import (
        AdvanceAllocation, FinancePlanWriteoffCorrection, FinanceReceiptAdjustment,
        OperationLog, Order, OrderItem, Transaction,
    )

    order, item, receipt, allocation, writeoff, related, audit = sample
    split = AdvanceAllocation.objects.get(pk=allocation)
    assert (split.amount, split.cash_amount, split.fee_credit_amount) == (Decimal(80), Decimal(75), Decimal(5))
    with connection.cursor() as cursor:
        constraints = connection.introspection.get_constraints(cursor, AdvanceAllocation._meta.db_table)
    assert {"advance_allocation_cash_nonnegative", "advance_allocation_fee_nonnegative",
            "advance_allocation_split_matches"} <= constraints.keys()
    assert Order.objects.get(pk=order).customer_country_snapshot == "CA"
    line = OrderItem.objects.get(pk=item)
    assert (line.cost_price, line.cost_currency_snapshot, line.product_category_name_snapshot) == (Decimal(9), "", "")
    assert OperationLog.objects.get(pk=audit).after_data == {"amount": "80"}
    if name == "c978":
        row = Transaction.objects.get(pk=receipt)
        assert row.exchange_rate is None and row.reference_rate_missing
        assert FinanceReceiptAdjustment.objects.filter(
            transaction_id=receipt, evidence_id=related, writeoff_id=writeoff, amount=10,
        ).exists()
    else:
        assert FinancePlanWriteoffCorrection.objects.filter(pk=related, writeoff_id=writeoff, amount=4).exists()


if __name__ == "__main__":
    run()
