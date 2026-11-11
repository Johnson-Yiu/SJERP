from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

from django.test import SimpleTestCase

from operations_runtime_http import ready


class RuntimeHttpTests(SimpleTestCase):
    def test_requires_django_session_response_on_the_expected_host(self):
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path != "/api/session/csrf/" or self.headers.get("X-Forwarded-Proto") != "https":
                    self.send_error(404)
                    return
                host = self.headers["Host"]
                self.send_response(302 if host == "redirect.invalid" else 200)
                self.send_header("Content-Type", "application/json")
                if host == "erp-a.invalid":
                    self.send_header("Set-Cookie", "csrftoken=synthetic; Path=/; Secure")
                self.end_headers()

            def log_message(self, *args):
                pass

        with HTTPServer(("127.0.0.1", 0), Handler) as server:
            worker = threading.Thread(target=server.serve_forever)
            worker.start()
            try:
                self.assertTrue(ready("erp-a.invalid", server.server_port))
                self.assertFalse(ready("erp-b.invalid", server.server_port))
                self.assertFalse(ready("redirect.invalid", server.server_port))
            finally:
                server.shutdown()
                worker.join()

    def test_refuses_unreachable_listener(self):
        with HTTPServer(("127.0.0.1", 0), BaseHTTPRequestHandler) as server:
            # Reserve the address without accepting HTTP, then probe after shutdown.
            port = server.server_port
        self.assertFalse(ready("erp-a.invalid", port))
