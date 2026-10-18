"""REAL_API_OBSERVATION: localhost disposable test data only; no balance edits."""
import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from pathlib import Path
from django.conf import settings
from crm.models import Customer, Transaction
assert Path(settings.DATABASES['default']['NAME']).name == 'r1a-isolated.sqlite3'
payload={'transaction_date':'2026-10-18','kind':'unallocated_advance','direction':'income','category':'未分配预收款','customer':Customer.objects.get(code='R1A-C').pk,'amount':'1.0000','currency':'USD','exchange_rate':'7.1','notes':'R1A replay synthetic only'}
results=[]
for numbered in [False,True]:
    data={**payload, **({'transaction_no':'R1A-STABLE-RETRY'} if numbered else {})}
    for attempt in [1,2]:
        before=Transaction.objects.count()
        request=Request('http://127.0.0.1:8126/api/transactions/',data=json.dumps(data).encode(),headers={'Content-Type':'application/json'})
        try:
            with urlopen(request) as response: status=response.status; body=json.load(response)
        except HTTPError as error: status=error.code; body=json.load(error)
        results.append({'type':'REAL_API_OBSERVATION','numbered':numbered,'attempt':attempt,'request':data,'http_status':status,'response':body,'count_before':before,'count_after':Transaction.objects.count()})
(settings.BASE_DIR.parent/'docs/uat-evidence/r1-a/replay-http.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
print([(r['numbered'],r['attempt'],r['http_status'],r['count_after']-r['count_before']) for r in results])
