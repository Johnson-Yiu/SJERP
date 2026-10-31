"""Loopback-only receiver for original Chrome screenshots from the CUA session."""
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import re
import sys


OUTPUT_DIR = Path(__file__).parent.resolve()
PORT = int(sys.argv[1])
NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,80}\.jpg$")


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        name = self.headers.get("X-Filename", "")
        if self.path != "/screenshot" or not NAME_PATTERN.fullmatch(name):
            self.send_error(400, "invalid destination")
            return
        length = int(self.headers.get("Content-Length", "0"))
        if length < 4 or length > 10_000_000:
            self.send_error(413, "invalid screenshot size")
            return
        payload = self.rfile.read(length)
        if not payload.startswith(b"\xff\xd8\xff"):
            self.send_error(415, "expected JPEG bytes")
            return
        target = (OUTPUT_DIR / name).resolve()
        if OUTPUT_DIR not in target.parents:
            self.send_error(400, "invalid destination")
            return
        target.write_bytes(payload)
        self.send_response(201)
        self.end_headers()
        self.wfile.write(f"saved {name} {len(payload)} bytes".encode())

    def log_message(self, fmt, *args):
        print("SCREENSHOT_RECEIVER", fmt % args, flush=True)


print(f"Screenshot receiver listening on 127.0.0.1:{PORT}; output={OUTPUT_DIR}", flush=True)
HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
