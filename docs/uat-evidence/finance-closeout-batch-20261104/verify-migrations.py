"""Fresh SQLite, empty reverse/forward, and nonempty bank-proof refusal."""
import json
import os
from pathlib import Path
import sys
import tempfile

if os.environ.get("APP_STAGE", "development") != "development":
    raise SystemExit("Only isolated development verification is supported")
repo = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(repo / "backend"))
with tempfile.TemporaryDirectory(prefix="finance-migration-verification-") as owned:
    root = Path(owned).resolve()
    media = root / "media"
    media.mkdir()
    os.environ.update(DATABASE_URL="sqlite:///" + (root / "database.sqlite3").as_posix(), MEDIA_ROOT=str(media), DJANGO_SETTINGS_MODULE="config.settings")
    import django
    django.setup()
    from django.contrib.auth.models import AnonymousUser
    from django.core.files.uploadedfile import SimpleUploadedFile
    from django.db import connection
    from django.db.migrations.executor import MigrationExecutor
    from crm.models import FinanceVoucher, Transaction
    from crm.services import finance_closeout as ledger
    executor = MigrationExecutor(connection)
    latest = executor.loader.graph.leaf_nodes()
    executor.migrate(latest)
    print(json.dumps({"fresh": "PASS", "vendor": connection.vendor, "leaves": latest}))
    MigrationExecutor(connection).migrate([("crm", "0097_merge_quote_and_cash_review")])
    print(json.dumps({"empty_reverse_to_0097": "PASS"}))
    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())
    source = Transaction.objects.create(transaction_no="SYNTH-MIGRATION-BANK", transaction_date="2026-01-01", direction="income", category="合成迁移检查", amount="1.00", currency="CNY", rmb_amount="1.00", kind="other_income")
    proof = ledger.upload(SimpleUploadedFile("synthetic-migration.pdf", b"%PDF-1.4\nSynthetic migration voucher\n%%EOF"), AnonymousUser(), bank_sources=[source.pk])
    before = FinanceVoucher.objects.filter(pk=proof.pk).values().get()
    try:
        MigrationExecutor(connection).migrate([("crm", "0101_finance_historical_transfer_links")])
    except RuntimeError as error:
        if "银行私有凭证历史" not in str(error):
            raise
        print(json.dumps({"nonempty_reverse": "REFUSED_AS_REQUIRED", "reason": str(error)}, ensure_ascii=False))
    else:
        raise RuntimeError("Nonempty migration reversal was not refused")
    if before != FinanceVoucher.objects.filter(pk=proof.pk).values().get():
        raise RuntimeError("Reverse refusal modified voucher history")
    ledger.voucher(proof.pk, scope="bank")
    connection.close()
    print(json.dumps({"history_and_actual_file": "UNCHANGED", "result": "PASS"}))
