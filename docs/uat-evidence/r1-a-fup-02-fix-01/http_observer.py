"""REAL_API_OBSERVATION only: forwards all requests to isolated Django unchanged."""
import http.client,json,threading
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from pathlib import Path
from datetime import datetime,timezone
lock=threading.Lock()
class Proxy(BaseHTTPRequestHandler):
 def forward(self):
  body=self.rfile.read(int(self.headers.get('Content-Length','0')))
  conn=http.client.HTTPConnection('127.0.0.1',8134,timeout=90)
  headers={k:v for k,v in self.headers.items() if k.lower() not in ['host','connection','content-length']}
  conn.request(self.command,self.path,body,headers);res=conn.getresponse();data=res.read()
  if any(key in self.path for key in ['/api/orders','/api/transactions','/api/payment-plans','/api/finance']):
   with lock,Path(__file__).with_name('http-events.jsonl').open('a',encoding='utf8') as f:
    f.write(json.dumps({'at':datetime.now(timezone.utc).isoformat(),'method':self.command,'path':self.path,'request':body.decode('utf8','replace'),'status':res.status,'response':data.decode('utf8','replace')},ensure_ascii=False)+'\n')
  self.send_response(res.status)
  for k,v in res.getheaders():
   if k.lower() not in ['connection','transfer-encoding','content-length']:self.send_header(k,v)
  self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
 do_GET=forward
 do_POST=forward
 do_PATCH=forward
 do_PUT=forward
 do_OPTIONS=forward
ThreadingHTTPServer(('127.0.0.1',8133),Proxy).serve_forever()
