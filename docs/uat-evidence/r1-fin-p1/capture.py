"""REAL_API_OBSERVATION + DATABASE_VERIFICATION: read-only same disposable DB."""
import os,sys,json,csv,io,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
import django
django.setup()
from django.conf import settings
from django.apps import apps
from django.core.serializers.json import DjangoJSONEncoder
from django.utils import timezone
from rest_framework.test import APIClient
assert Path(settings.DATABASES['default']['NAME']).name=='r1-fin-p1-isolated.sqlite3'
name=sys.argv[1];assert name in ['before','after']
p=Path(__file__).resolve().parent;c=APIClient();day=timezone.localdate();dates={'date_from':str(day.replace(day=1)),'date_to':str(day)}
result={}
for key,url,params in [('finance','/api/finance-dashboard/',dates),('finance_csv','/api/finance-dashboard/',dict(dates,export='csv')),('cash','/api/reports/data/',dict(dates,source='cash',group_by='direction')),('cash_csv','/api/reports/data/',dict(dates,source='cash',group_by='direction',export='csv')),('sales','/api/reports/data/',dict(dates,source='sales')),('profit','/api/reports/data/',dict(dates,source='profit')),('transactions','/api/transactions/',{})]:
 r=c.get(url,params);assert r.status_code==200,(key,r.status_code)
 result[key]={'status':r.status_code,'body':r.content.decode('utf-8-sig') if key.endswith('_csv') else json.loads(r.content)}
 if key.endswith('_csv'):(p/(name+'-'+key+'.csv')).write_bytes(r.content)
models={m.__name__:list(m.objects.order_by('pk').values()) for m in apps.get_app_config('crm').get_models()}
result['database_sha256']=hashlib.sha256(json.dumps(models,cls=DjangoJSONEncoder,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
(p/(name+'.json')).write_text(json.dumps(result,cls=DjangoJSONEncoder,ensure_ascii=False,indent=2),encoding='utf8')
print(name,result['database_sha256'],result['finance']['body']['metrics'])
