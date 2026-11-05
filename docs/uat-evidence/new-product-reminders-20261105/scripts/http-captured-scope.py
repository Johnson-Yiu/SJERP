import json,uuid
from pathlib import Path
from urllib.request import Request,build_opener,ProxyHandler
from urllib.error import HTTPError
from urllib.parse import quote
opener=build_opener(ProxyHandler({}));proof=[]
session=json.loads(Path('.tmp-reminder-session.json').read_text())['session']
def call(method,path,data=None,status=200,authenticated=True):
 headers={'Content-Type':'application/json'}
 if authenticated:headers.update(Cookie='sessionid='+session+'; csrftoken='+'a'*32,**{'X-CSRFToken':'a'*32})
 req=Request('http://127.0.0.1:8177/api/'+path,method=method,headers=headers,data=json.dumps(data).encode() if data is not None else None)
 try:r=opener.open(req,timeout=30)
 except HTTPError as e:r=e
 with r:
  raw=r.read(); body=json.loads(raw) if raw else None
  proof.append(dict(method=method,path=path,status=r.status,body=body,identity='synthetic-restricted' if authenticated else 'anonymous'))
  assert r.status==status,(path,r.status,body)
  return body
try:
 operator=call('GET','session/current-operator/');assert not operator['development_superadmin'] and operator['authenticated']
 call('GET','new-product-reminders/',status=403,authenticated=False)
 data=call('GET','new-product-reminders/?tag='+quote('新品提醒')+'&search='+quote('合成分页壁灯')+'&state=all')
 assert data['count']==51 and all(x['customer']==1 for x in data['results'])
 foreign=call('GET','new-product-reminders/?customer=2&search='+quote('合成分页壁灯')+'&state=all');assert foreign['count']==0
 call('GET','new-product-reminders/55/',status=404)
 call('GET','new-product-reminders/55/history/',status=404)
 call('PATCH','new-product-reminders/55/',{'version':1,'requirement':'unauthorized'},404)
 call('POST','new-product-reminders/55/void/',{'version':1,'reason':'unauthorized'},404)
 call('POST','new-product-reminders/',{'customer':2,'requirement':'unauthorized','request_key':str(uuid.uuid4())},403)
 call('GET','customers/2/',status=404)
 call('GET','customers/1/')
 call('GET','follow-ups/1/')
 call('GET','new-product-reminders/56/')
 print('REAL_HTTP_SCOPE_PASS',len(proof),'requests; isolated synthetic scope process only')
finally:
 Path('docs/uat-evidence/new-product-reminders-20261105/http-scope-real.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2),encoding='utf-8')
