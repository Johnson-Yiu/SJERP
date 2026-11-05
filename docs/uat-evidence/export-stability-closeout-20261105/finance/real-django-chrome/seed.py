import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
import django
django.setup()
from crm.models import Transaction, RmbCashEvent
from django.utils import timezone
for month,amount,formula in [('09','123.4500','=SUM(1,2)'),('10','456.7800','@synthetic')]:
    Transaction.objects.create(transaction_no='CSV-E2E-'+month,transaction_date='2026-'+month+'-15',direction='income',category=formula,amount=amount,currency='CNY',exchange_rate=1,rmb_amount=amount,status='confirmed')
    RmbCashEvent.objects.create(event_no='CSV-BANK-'+month,request_key='CSV-BANK-'+month,request_hash='a'*64,request_payload={},kind='cny_direct',currency='CNY',amount=amount,direction='income',bank_date='2026-'+month+'-15',bank_net_amount=amount,source_account='SYNTH',rmb_account='SYNTH',bank_reference=formula,created_actor={'kind':'synthetic'},status='confirmed',confirmed_at=timezone.now())
print('Created synthetic transactions and confirmed cash events in isolated database')
