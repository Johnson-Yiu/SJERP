import http.client
import json
import os
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpRequest
from django.middleware.csrf import get_token
from django.test import Client, LiveServerTestCase, override_settings

from crm.models import CSVImportBatch, CSVImportRowAudit, Customer


class CsvUploadHttp413Tests(LiveServerTestCase):
    """Exercise oversized multipart bodies through Django's real HTTP server."""

    limit_bytes = 64 * 1024
    oversized_file = b"code,name\nHTTP-413," + b"x" * (limit_bytes + 256 * 1024)

    @classmethod
    def setUpClass(cls):
        cls.upload_temp_directory = tempfile.TemporaryDirectory(prefix="iss052-http-413-")
        cls.settings_override = override_settings(
            AUDIT_LOG_ENABLED=True,
            CSV_IMPORT_MAX_BYTES=cls.limit_bytes,
            FILE_UPLOAD_MAX_MEMORY_SIZE=1024,
            FILE_UPLOAD_TEMP_DIR=cls.upload_temp_directory.name,
        )
        cls.settings_override.enable()
        try:
            super().setUpClass()
        except Exception:
            cls.settings_override.disable()
            cls.upload_temp_directory.cleanup()
            raise

    @classmethod
    def tearDownClass(cls):
        try:
            super().tearDownClass()
        finally:
            cls.settings_override.disable()
            cls.upload_temp_directory.cleanup()

    def setUp(self):
        operator = get_user_model().objects.create_user(
            username="csv-http-413-operator",
            password="isolated-test-only",
        )
        session_client = Client()
        session_client.force_login(operator)
        session_key = session_client.cookies[settings.SESSION_COOKIE_NAME].value
        csrf_token = get_token(HttpRequest())
        self.cookie_header = (
            f"{settings.SESSION_COOKIE_NAME}={session_key}; "
            f"{settings.CSRF_COOKIE_NAME}={csrf_token}"
        )
        self.csrf_token = csrf_token
        self.assertEqual(list(Path(self.upload_temp_directory.name).iterdir()), [])

    def _multipart_body(self, *, entity="customers", include_preview_token=False):
        boundary = "----iss052-http-413-boundary"
        parts = [
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"entity\"\r\n\r\n{entity}\r\n".encode()
        ]
        if include_preview_token:
            parts.append(
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"preview_token\"\r\n\r\nnot-used\r\n".encode()
            )
        parts.extend(
            [
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"oversized.csv\"\r\nContent-Type: text/csv\r\n\r\n".encode(),
                self.oversized_file,
                f"\r\n--{boundary}--\r\n".encode(),
            ]
        )
        return boundary, b"".join(parts)

    def _post_real_http(self, path, *, include_preview_token=False):
        boundary, body = self._multipart_body(include_preview_token=include_preview_token)
        server = urlsplit(self.live_server_url)
        connection = http.client.HTTPConnection(server.hostname, server.port, timeout=30)
        try:
            connection.request(
                "POST",
                path,
                body=body,
                headers={
                    "Content-Type": f"multipart/form-data; boundary={boundary}",
                    "Cookie": self.cookie_header,
                    "X-CSRFToken": self.csrf_token,
                },
            )
            response = connection.getresponse()
            payload = response.read()
            return response.status, json.loads(payload.decode("utf-8")), response.getheaders(), len(body)
        except (ConnectionError, OSError) as exc:
            self.fail(f"HTTP upload connection closed instead of returning a response: {exc}")
        finally:
            connection.close()

    def test_all_csv_upload_routes_return_http_413_and_release_temp_files(self):
        routes = (
            ("/api/import/csv/preview/", False),
            ("/api/import/csv/execute/", True),
            ("/api/import/csv/", False),
        )
        results = []
        for path, include_preview_token in routes:
            with self.subTest(path=path):
                status_code, payload, headers, request_bytes = self._post_real_http(
                    path,
                    include_preview_token=include_preview_token,
                )
                self.assertEqual(status_code, 413, payload)
                self.assertIn("CSV 文件超过大小限制", payload["detail"])
                self.assertNotIn("connection reset", str(headers).lower())
                temporary_files = [item.name for item in Path(self.upload_temp_directory.name).iterdir()]
                self.assertEqual(temporary_files, [])
                self.assertFalse(Customer.objects.exists())
                self.assertFalse(CSVImportRowAudit.objects.exists())
                results.append({
                    "endpoint": path,
                    "status": status_code,
                    "detail": payload["detail"],
                    "uploaded_file_bytes": len(self.oversized_file),
                    "multipart_request_bytes": request_bytes,
                    "connection_header": next(
                        (value for key, value in headers if key.lower() == "connection"),
                        "",
                    ),
                    "temporary_files_after_response": temporary_files,
                    "customer_rows_after_response": Customer.objects.count(),
                    "row_audits_after_response": CSVImportRowAudit.objects.count(),
                })

        failed_batch = CSVImportBatch.objects.get()
        self.assertEqual(failed_batch.status, "failed")
        self.assertEqual(failed_batch.file_sha256, "")
        self.assertEqual((failed_batch.total_rows, failed_batch.failed_rows), (0, 0))
        evidence_root = os.environ.get("ISS052_HTTP_413_EVIDENCE_ROOT")
        if evidence_root:
            log_dir = Path(evidence_root) / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            (log_dir / "http-413-all-upload-routes.json").write_text(
                json.dumps({
                    "limit_bytes": self.limit_bytes,
                    "django_version": __import__("django").get_version(),
                    "results": results,
                    "execute_failed_batch": {
                        "status": failed_batch.status,
                        "file_sha256": failed_batch.file_sha256,
                        "total_rows": failed_batch.total_rows,
                        "failed_rows": failed_batch.failed_rows,
                    },
                }, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
