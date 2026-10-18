"""FIXTURE_SETUP: append synthetic data to copied disposable DB; never migrate/clear."""
import os,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
import django
django.setup()
from django.conf import settings
from decimal import Decimal as D
from django.utils import timezone
from crm.models import Customer,Transaction
from crm.services.finance import record_transaction,void_transaction
assert Path(settings.DATABASES['default']['NAME']).name=='r1-fin-p1-isolated.sqlite3'
assert set(Customer.objects.values_list('code',flat=True))=={'FUP02-C'}
assert not Transaction.objects.filter(transaction_no__startswith='FINP1-').exists()
for no,kind,direction,currency,amount,rate in [('CNY-IN','other_income','income','CNY','100','1'),('USD-OUT','period_expense','expense','USD','12.34','7.123456'),('EUR-IN','other_income','income','EUR','10','7.8'),('CNY-OUT','period_expense','expense','CNY','20','1'),('VOID','period_expense','expense','USD','2.34','7.123456')]:
 row=record_transaction(dict(transaction_no='FINP1-'+no,kind=kind,direction=direction,currency=currency,amount=D(amount),exchange_rate=D(rate),category='P1 合成口径验收',transaction_date=timezone.localdate()))
 if no=='VOID':void_transaction(row,'合成已作废不计统计')
print('FIXTURE_SETUP: CNY/USD/EUR/void added through unchanged service; no bank facts')
