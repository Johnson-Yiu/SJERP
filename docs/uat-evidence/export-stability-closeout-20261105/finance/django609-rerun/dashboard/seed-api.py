import os, json
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
import django
django.setup()
from rest_framework.test import APIClient
from django.core.files.uploadedfile import SimpleUploadedFile
c=APIClient()
for month,amount in [('09','123.45'),('10','456.78')]:
 for i,prefix in enumerate(['=','+','-','@']):
  key=f'CSV2-{month}-{i}'
  amount=str((120 if month=='09' else 450)+i)+'.01'
  def check(response,expected):
   print(key,response.status_code,flush=True)
   if response.status_code != expected: raise RuntimeError(str(getattr(response,'data',response.content)))
   return response.data
  t=check(c.post('/api/transactions/',{'transaction_no':key,'transaction_date':f'2026-{month}-{20+i}','direction':'income','kind':'other_income','category':prefix+'synthetic','amount':amount,'currency':'CNY','exchange_rate':'1'},format='json'),201)
  v=check(c.post('/api/rmb-cash-events/voucher-upload/',{'sources':json.dumps([t['id']]),'file':SimpleUploadedFile(key+'.pdf',b'%PDF-1.4\nsynthetic\n%%EOF',content_type='application/pdf')},format='multipart'),201)
  p={'event_no':key,'request_key':key,'kind':'cny_direct','currency':'CNY','direction':'income','bank_date':f'2026-{month}-{20+i}','bank_net_amount':amount,'fee_mode':'none','fee_amount':'0','source_account':'SYNTH_CNY','rmb_account':'SYNTH_CNY','bank_reference':prefix+'synthetic','evidence_reference':'test','evidence_sha256':'a'*64,'evidence_note':'synthetic','sources':[{'transaction_id':t['id'],'amount':amount,'verified':True}],'private_voucher':v['id']}
  event=check(c.post('/api/rmb-cash-events/',p,format='json'),201)
  check(c.post('/api/rmb-cash-events/'+str(event['id'])+'/confirm/',{'voucher_checked':True},format='json'),200)
print('All records created and confirmed through API')

