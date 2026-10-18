"""Isolated UAT transport proxy. Forwards to REAL Django, drops one committed response."""
import http.client, json, socket, threading
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
log = Path(__file__).with_name('transport-events.jsonl')
lock=threading.Lock()
dropped=False
class Proxy(BaseHTTPRequestHandler):
 def handle_request(self):
  global dropped
  body=self.rfile.read(int(self.headers.get('Content-Length','0')))
  conn=http.client.HTTPConnection('127.0.0.1',8129,timeout=90)
  headers={k:v for k,v in self.headers.items() if k.lower() not in ['host','connection','content-length']}
  conn.request(self.command,self.path,body,headers)
  response=conn.getresponse(); data=response.read()
  drop=False
  with lock:
   if self.command=='POST' and self.path.startswith('/api/transactions/') and b'FUP01-LOST-RESPONSE' in body and response.status==201 and not dropped:
    dropped=True; drop=True
   with log.open('a',encoding='utf8') as f:
    f.write(json.dumps(dict(method=self.command,path=self.path,request=body.decode('utf8','replace'),upstream_status=response.status,response=data.decode('utf8','replace'),response_dropped=drop),ensure_ascii=False)+'\n')
  if drop:
   self.close_connection=True
   self.connection.shutdown(socket.SHUT_RDWR);self.connection.close();return
  self.send_response(response.status)
  for k,v in response.getheaders():
   if k.lower() not in ['connection','transfer-encoding','content-length']:self.send_header(k,v)
  self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
 do_GET=handle_request
 do_POST=handle_request
 do_OPTIONS=handle_request
 do_PATCH=handle_request
ThreadingHTTPServer(('127.0.0.1',8128),Proxy).serve_forever()
