import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TransactionTestCase, override_settings
from rest_framework.test import APIClient

from crm.models import Customer, FollowUp, FollowUpAttachment


@override_settings(DEVELOPMENT_SUPERADMIN=False, RBAC_ENFORCEMENT=True, AUDIT_LOG_ENABLED=True)
class ReviewAttachmentDownloadTests(TransactionTestCase):
    def test_opaque_storage_key_preserves_original_download_name_and_bytes(self):
        with tempfile.TemporaryDirectory(prefix="review-attachment-download-") as media:
            with override_settings(MEDIA_ROOT=media):
                operator = get_user_model().objects.create_superuser(
                    username="synthetic-download", password="test-only-password",
                )
                client = APIClient()
                client.force_authenticate(operator)
                customer = Customer.objects.create(code="REVIEW-DOWNLOAD", name="Synthetic download customer")
                follow_up = FollowUp.objects.create(
                    customer=customer, followed_at="2026-11-04T09:00:00Z",
                    type="email", subject="Synthetic attachment download",
                )
                body = b"Synthetic attachment bytes; no business data."
                response = client.post(
                    f"/api/follow-ups/{follow_up.pk}/attachments/",
                    {"files": [SimpleUploadedFile("office-evidence.txt", body, content_type="text/plain")]},
                    format="multipart",
                )
                self.assertEqual(response.status_code, 201, response.data)
                attachment = FollowUpAttachment.objects.get(follow_up=follow_up)
                self.assertNotEqual(attachment.file.name.rsplit("/", 1)[-1], attachment.name)
                downloaded = client.get(f"/api/media/{attachment.file.name}")
                try:
                    self.assertEqual(downloaded.status_code, 200)
                    self.assertEqual(b"".join(downloaded.streaming_content), body)
                    self.assertIn('filename="office-evidence.txt"', downloaded["Content-Disposition"])
                    self.assertEqual(downloaded["Content-Type"], "text/plain; charset=utf-8")
                    self.assertEqual(downloaded["Cache-Control"], "private, no-store")
                    self.assertEqual(downloaded["X-Content-Type-Options"], "nosniff")
                finally:
                    downloaded.close()
