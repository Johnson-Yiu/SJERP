import json, uuid
from urllib.request import Request, build_opener, ProxyHandler
from urllib.error import HTTPError
from pathlib import Path
out=Path('docs/uat-evidence/new-product-reminders-20261105')
http=build_opener(ProxyHandler({})); proof=[]
def call(method,path,data=None,expected=200):
 req=Request('http://127.0.0.1:8176/api/'+path,method=method,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json'})
 try:r=http.open(req,timeout=30)
 except HTTPError as e:r=e
 with r:
  raw=r.read(); body=json.loads(raw) if raw else None
  proof.append(dict(method=method,path=path,status=r.status,body=body))
  assert r.status==expected,(path,r.status,body)
  return body
try:
 for state,count in [('active',0),('void',1),('all',1)]:
  data=call('GET',f'new-product-reminders/?state={state}&search='+__import__('urllib.parse',fromlist=['quote']).quote('内置浏览器合成新品壁灯'))
  assert data['count']==count
 detail=call('GET','new-product-reminders/56/');assert detail['version']==3 and detail['void_reason']=='内置浏览器验收：需求用途调整'
 history=call('GET','new-product-reminders/56/history/');assert len(history)==3 and [r['after_data']['version'] for r in history]==[1,2,3]
 call('DELETE','new-product-reminders/56/',expected=405)
 call('DELETE','new-product-reminders/',{'ids':[56]},405)
 call('POST','new-product-reminders/bulk-delete/',{'ids':[56]},405)
 payload={'customer':1,'follow_up':1,'requirement':'真实HTTP合成新品需求','specification':'IP65','request_key':str(uuid.uuid4())}
 row=call('POST','new-product-reminders/',payload,201);rid=row['id']
 assert call('POST','new-product-reminders/',payload,200)['id']==rid
 call('PATCH',f'new-product-reminders/{rid}/',{'version':1,'void_reason':'绕过'},400)
 call('PATCH',f'new-product-reminders/{rid}/',{'version':1,'specification':'IP68'},200)
 call('PATCH',f'new-product-reminders/{rid}/',{'version':1,'specification':'stale'},409)
 call('POST',f'new-product-reminders/{rid}/void/',{'version':2,'reason':' '},400)
 call('POST',f'new-product-reminders/{rid}/void/',{'version':2,'reason':'真实HTTP合成验收'},200)
 call('PATCH',f'new-product-reminders/{rid}/',{'version':3,'requirement':'不能改历史'},409)
 print('REAL_HTTP_PASS',len(proof),'requests', 'created_record',rid)
finally:
 (out/'http-real.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2),encoding='utf-8')
