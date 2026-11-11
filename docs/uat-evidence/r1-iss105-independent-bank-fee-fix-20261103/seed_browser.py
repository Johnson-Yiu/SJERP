"""Synthetic fixtures only after the owned runtime/database/migration checks."""
import os
import json
import sys
from uuid import uuid4
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "test_support.isolated_settings")
django.setup()
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from test_support.isolated_runtime import verify_isolated_runtime
from crm.models import Transaction, RmbCashEvent, CashSourceAllocation, FinanceAccount
from crm.services.finance import record_transaction

verify_isolated_runtime(settings=settings, database_must_exist=True)
assert {"SYNTH_FX", "SYNTH_CNY"}.issubset(settings.RMB_CASH_ACCOUNT_IDS), "Configure synthetic controlled accounts in the isolated API process"
if len(sys.argv) > 1:
    ids = json.loads(sys.argv[1])
    assert all(isinstance(pk, int) and pk > 0 for pk in ids)
    source_rows = list(Transaction.objects.filter(pk__in=ids).order_by("pk").values())
    event_ids = list(CashSourceAllocation.objects.filter(source_id__in=ids).values_list("event_id", flat=True))
    print(json.dumps({"source_rows": source_rows, "events": list(RmbCashEvent.objects.filter(pk__in=event_ids).order_by("pk").values()), "allocations": list(CashSourceAllocation.objects.filter(source_id__in=ids).order_by("pk").values())}, cls=DjangoJSONEncoder))
    sys.exit(0)
for code, currency in (("SYNTH_FX", "USD"), ("SYNTH_CNY", "CNY")):
    FinanceAccount.objects.get_or_create(code=code, defaults={
        "name": f"合成 {currency} 银行账户", "currency": currency, "account_type": "bank",
        "ownership": "own", "ownership_reason": "隔离验收合成账户",
    })

prefix = "SYNTH-FEE-" + uuid4().hex[:8].upper()
rows = []
names = []
for n in range(4):
    name = f"{prefix}-{n}"
    row = record_transaction(dict(transaction_no=name, kind="bank_fee", direction="expense", category="合成银行手续费", amount="5", currency="CNY", exchange_rate="1"))
    rows.append(row.pk)
    names.append(name)
fx = record_transaction(dict(transaction_no=f"{prefix}-FX", kind="other_income", direction="income", category="合成外币收入", amount="200", currency="USD", exchange_rate="7"))
print(json.dumps({"fee_ids": rows, "fee_names": names, "fx_id": fx.pk, "prefix": prefix, "source_rows": list(Transaction.objects.filter(pk__in=rows + [fx.pk]).order_by("pk").values()), "database": str(settings.DATABASES["default"]["NAME"]), "media": str(settings.MEDIA_ROOT)}, cls=DjangoJSONEncoder))
