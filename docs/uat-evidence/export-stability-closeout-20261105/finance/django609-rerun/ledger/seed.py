import os,json
from pathlib import Path
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
import django
django.setup()
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
expected=Path(os.environ['LEDGER_TEST_DATABASE']).resolve()
assert Path(settings.DATABASES['default']['NAME']).resolve()==expected, 'Refusing non-isolated DB'
assert Path(settings.MEDIA_ROOT).resolve()==Path(os.environ['LEDGER_TEST_MEDIA']).resolve()
c=APIClient(HTTP_HOST='127.0.0.1')
def call(label, url, body, fmt='json', status=201):
 r=c.post(url,body,format=fmt)
 print(json.dumps({'action':label,'status':r.status_code,'body':getattr(r,'data',None)},ensure_ascii=False,default=str),flush=True)
 if r.status_code!=status: raise RuntimeError(f'{label}: {r.status_code}: {getattr(r,"data",None)}')
 return r.data
account=call('account','/api/finance-ledger/accounts/',{'code':'SYNTH-LEDGER-ONLY','name':'合成银行','account_type':'bank','ownership':'own','ownership_reason':'隔离数据合成凭证'})
voucher=call('voucher','/api/finance-ledger/vouchers/',{'file':SimpleUploadedFile('synthetic.pdf',b'%PDF-1.4\nSynthetic voucher\n%%EOF',content_type='application/pdf')},'multipart')
for month,base in [('09',120),('10',450)]:
 for i,prefix in enumerate(['=','+','-','@']):
  key=prefix+'SYNTH-'+month
  body={'request_key':'LEDGER-TEST-'+month+'-'+str(i),'kind':'cash','account':account['id'],'voucher':voucher['id'],'actual_date':f'2026-{month}-{20+i}','amount':str(base+i)+'.01','direction':'income','nature':'unclassified','truth':'verified','source_system':'SYNTH-LEDGER','source_key':key,'reason':'隔离合成数据，凭证核实'}
  instruction=call('instruction','/api/finance-ledger/instructions/',body)
  call('post','/api/finance-ledger/post/',{'id':instruction['id'],'voucher_checked':True},status=200)
print('PASS: eight synthetic facts posted by real API and state machine')
