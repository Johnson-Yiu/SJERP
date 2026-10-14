"""Local-only request gate for disposable CRM UI acceptance, not application code.

Write {"mode":"hold"}, {"mode":"success"} or {"mode":"fail"} to control.json.
Only record POST/PUT requests are gated; successful releases use the real isolated API.
"""
import argparse
import http.client
import json
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--port', type=int, default=8111)
parser.add_argument('--upstream', type=int, default=8109)
parser.add_argument('--state', type=Path, required=True)
args = parser.parse_args()
args.state.mkdir(parents=True, exist_ok=True)
lock = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def handle_request(self):
        body = self.rfile.read(int(self.headers.get('Content-Length', '0')))
        is_record_write = self.command in ('POST', 'PUT') and re.fullmatch(r'/api/(contacts|follow-ups)/(\d+/)?', self.path)
        if is_record_write:
            with lock:
                with (args.state / 'requests.jsonl').open('a', encoding='utf-8') as log:
                    log.write(json.dumps({'method': self.command, 'path': self.path, 'time': time.time()}) + '\n')
            deadline = time.monotonic() + 120
            while True:
                try:
                    mode = json.loads((args.state / 'control.json').read_text()).get('mode', 'success')
                except (FileNotFoundError, json.JSONDecodeError):
                    mode = 'success'
                if mode != 'hold' or time.monotonic() >= deadline:
                    break
                time.sleep(0.1)
            if mode != 'success':
                data = json.dumps({'detail': '验收注入的保存失败，请重试'}, ensure_ascii=False).encode('utf-8')
                self.send_response(503)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
        upstream = http.client.HTTPConnection('127.0.0.1', args.upstream, timeout=120)
        headers = {key: value for key, value in self.headers.items() if key.lower() not in ('host', 'connection')}
        upstream.request(self.command, self.path, body, headers)
        response = upstream.getresponse()
        data = response.read()
        self.send_response(response.status)
        for key, value in response.getheaders():
            if key.lower() not in ('connection', 'transfer-encoding', 'content-length'):
                self.send_header(key, value)
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)
        upstream.close()

    do_GET = handle_request
    do_POST = handle_request
    do_PUT = handle_request
    do_PATCH = handle_request
    do_DELETE = handle_request
    do_OPTIONS = handle_request


print(f'Isolated UI gate: 127.0.0.1:{args.port} -> 127.0.0.1:{args.upstream}', flush=True)
ThreadingHTTPServer(('127.0.0.1', args.port), Handler).serve_forever()
