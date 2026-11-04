"""Real loopback HTTP, session authentication, CSRF and downloadable files."""
import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from django.contrib.auth import get_user_model
from django.contrib.sessions.backends.db import SessionStore
from django.test import LiveServerTestCase, override_settings

from crm.tests.test_finance_adversarial_review import AdversarialFixture, BASE
from crm.tests.test_finance_data_scope import RBAC_SETTINGS


class FinanceAdversarialLiveHTTPTests(AdversarialFixture, LiveServerTestCase):
    def setUp(self):
        self.setup_adversarial()

    def session(self, user):
        s = SessionStore()
        s["_auth_user_id"] = str(user.pk)
        s["_auth_user_backend"] = "django.contrib.auth.backends.ModelBackend"
        s["_auth_user_hash"] = user.get_session_auth_hash()
        s.save()
        return s.session_key

    def http(self, path, data=None, user=None, authenticated=True):
        headers = {}
        if authenticated:
            headers = {"Cookie": "sessionid=" + self.session(user or self.maker) + "; csrftoken=" + "a" * 32, "X-CSRFToken": "a" * 32}
        if data is not None:
            headers["Content-Type"] = "application/json"
        request = Request(self.live_server_url + path, data=json.dumps(data).encode() if data is not None else None, headers=headers)
        try:
            with urlopen(request, timeout=15) as response:
                status, body, response_headers = response.status, response.read(), dict(response.headers)
        except HTTPError as response:
            status, body, response_headers = response.code, response.read(), dict(response.headers)
        self.records.append({"transport": "real_tcp_http", "path": path, "request": data, "status": status,
                             "headers": {k: v for k, v in response_headers.items() if k.lower() != "set-cookie"},
                             "body": body.decode("utf-8", errors="replace")})
        return status, body, response_headers

    def test_real_session_csrf_two_person_approval_post_retry_and_csv(self):
        data = self.data(kind="opening", amount="37.91", actual_date="2026-04-01")
        status, body, _ = self.http(BASE + "instructions/", data)
        self.assertEqual(status, 201, body)
        ident = json.loads(body)["id"]
        self.assertEqual(self.http(BASE + "approve/", {"id": ident})[0], 400)
        self.assertEqual(self.http(BASE + "approve/", {"id": ident}, user=self.reviewer)[0], 200)
        first = self.http(BASE + "post/", {"id": ident, "voucher_checked": True})
        second = self.http(BASE + "post/", {"id": ident, "voucher_checked": True})
        self.assertEqual(first[0], 200, first[1])
        self.assertEqual(json.loads(first[1])["id"], json.loads(second[1])["id"])
        status, body, _ = self.http(BASE + "facts/?date_from=2026-04-01&date_to=2026-04-30&export=csv")
        self.assertEqual(status, 200, body)
        self.assertIn(b"37.91", body)

    def test_real_private_file_and_anonymous_role_denials(self):
        with override_settings(**RBAC_SETTINGS):
            status, body, headers = self.http(BASE + f"voucher-download/?id={self.proof}")
            self.assertEqual(status, 200, body)
            self.assertEqual(body, self.proof_bytes)
            self.assertEqual(headers["Cache-Control"], "private, no-store")
            no_role = get_user_model().objects.create_user("adversarial-http-no-role")
            for path in (BASE, BASE + f"voucher-download/?id={self.proof}", BASE + "facts/?export=csv"):
                self.assertEqual(self.http(path, authenticated=False)[0], 403)
                self.assertEqual(self.http(path, user=no_role)[0], 403)
