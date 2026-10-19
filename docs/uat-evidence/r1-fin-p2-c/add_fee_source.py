"""FIXTURE_SETUP only: add one isolated CNY bank-fee source before UI capture."""
import os
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()
from django.conf import settings
from crm.models import Customer, Transaction, RmbCashEvent
assert Path(settings.DATABASES["default"]["NAME"]).name == "r1-fin-p2-c-isolated.sqlite3"
assert RmbCashEvent.objects.count() == 0
assert not Transaction.objects.filter(transaction_no="P2C-CNY-BANK-FEE").exists()
row = Transaction.objects.create(
    transaction_no="P2C-CNY-BANK-FEE", transaction_date=date(2026, 10, 19),
    direction="expense", category="银行手续费", amount=Decimal("5.00"), currency="CNY",
    exchange_rate=Decimal("1"), rmb_amount=Decimal("5.0000"), kind="bank_fee",
    status="confirmed", notes="合成银行扣费来源，非真实银行流水",
)
print({"FIXTURE_SETUP": {"bank_fee_source": row.pk, "amount": "5.00", "currency": "CNY"}})
