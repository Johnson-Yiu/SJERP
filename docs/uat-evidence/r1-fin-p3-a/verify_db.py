import os, sys, json, hashlib
from decimal import Decimal
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
os.environ.setdefault('DATABASE_URL','sqlite:///D:/Codex项目/森爵照明管理系统/.r1-fin-p3-a-isolated.sqlite3')
sys.path.insert(0,os.getcwd())
import django
django.setup()
from django.apps import apps
from crm.models import RmbCashEvent, CashSourceAllocation, Transaction
from django.core.serializers.json import DjangoJSONEncoder

def legacy():
    return {m.__name__: list(m.objects.order_by('pk').values()) for m in apps.get_app_config('crm').get_models() if m not in {RmbCashEvent, CashSourceAllocation}}
def digest(value):
    return hashlib.sha256(json.dumps(value, cls=DjangoJSONEncoder, sort_keys=True, separators=(',',':')).encode()).hexdigest()
before=json.load(open('../docs/uat-evidence/r1-fin-p3-a/legacy-before.json',encoding='utf-8'))
events=list(RmbCashEvent.objects.order_by('pk').values('id','event_no','status','direction','bank_date','bank_net_amount','fee_amount','currency','amount'))
confirmed=[e for e in events if e['status']=='confirmed']
actual=sum((Decimal(e['bank_net_amount']) if e['direction']=='income' else -Decimal(e['bank_net_amount']) for e in confirmed), Decimal('0'))
out={'DATABASE_VERIFICATION':'isolated_only','legacy_before_sha256':digest(before),'legacy_after_sha256':digest(legacy()),'legacy_unchanged':digest(before)==digest(legacy()),'transaction_count':Transaction.objects.count(),'cash_event_count':len(events),'cash_event_status_counts':{s:sum(e['status']==s for e in events) for s in ['confirmed','pending','cancelled']},'confirmed_bank_net_signed':str(actual),'confirmed_events':events,'allocation_count':CashSourceAllocation.objects.count()}
open('../docs/uat-evidence/r1-fin-p3-a/DATABASE_VERIFICATION-after.json','w',encoding='utf-8').write(json.dumps(out,cls=DjangoJSONEncoder,ensure_ascii=False,indent=2))
print(json.dumps(out,cls=DjangoJSONEncoder,ensure_ascii=False))



