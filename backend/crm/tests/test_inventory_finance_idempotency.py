from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless
from unittest.mock import patch

from django.db import close_old_connections, connection, connections
from django.test import TestCase, TransactionTestCase, override_settings
from rest_framework.test import APIClient

from crm.models import FulfillmentIdempotency, InventoryMovement, OperationLog, Product, SKU


@override_settings(APP_STAGE="development", DEBUG=True, DEVELOPMENT_SUPERADMIN=True, RBAC_ENFORCEMENT=False, AUDIT_LOG_ENABLED=True)
class InventoryRequestTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.sku = SKU.objects.create(product=Product.objects.create(code="INV-ID-P", name="合成产品"), sku="INV-ID-SKU")
        self.single = {"movement_date": "2026-11-06", "type": "adjust_in", "sku": self.sku.pk, "quantity": "5"}
        self.batch = {"movement_date": "2026-11-06", "type": "adjust_in", "items": [{"sku": self.sku.pk, "quantity": "5"}, {"sku": self.sku.pk, "quantity": "3"}]}

    def test_single_replay_and_conflicting_content(self):
        url = "/api/inventory-movements/"
        self.assertEqual(self.client.post(url, self.single, format="json").status_code, 400)
        first = self.client.post(url, self.single, format="json", HTTP_IDEMPOTENCY_KEY="INV-SINGLE")
        self.assertEqual(first.status_code, 201, first.data)
        replay = self.client.post(url, self.single, format="json", HTTP_IDEMPOTENCY_KEY="INV-SINGLE")
        self.assertEqual(replay.status_code, 201, replay.data)
        self.assertEqual(replay.data["id"], first.data["id"])
        self.assertEqual(replay.headers.get("Idempotent-Replay"), "true")
        conflict = self.client.post(url, {**self.single, "quantity": "6"}, format="json", HTTP_IDEMPOTENCY_KEY="INV-SINGLE")
        self.assertEqual(conflict.status_code, 409, conflict.data)
        self.assertEqual(InventoryMovement.objects.count(), 1)

    def test_batch_audit_failure_rolls_back_all_and_same_key_can_retry(self):
        url = "/api/inventory-movements/batch/"
        from crm import views
        original = views.record_operation
        calls = []
        def fail_second(*args, **kwargs):
            calls.append(1)
            if len(calls) == 2:
                raise RuntimeError("synthetic audit failure")
            return original(*args, **kwargs)
        with patch("crm.views.record_operation", side_effect=fail_second):
            with self.assertRaises(RuntimeError):
                self.client.post(url, self.batch, format="json", HTTP_IDEMPOTENCY_KEY="INV-BATCH")
        self.assertFalse(InventoryMovement.objects.exists())
        self.assertFalse(OperationLog.objects.exists())
        self.assertFalse(FulfillmentIdempotency.objects.filter(key="INV-BATCH").exists())
        response = self.client.post(url, self.batch, format="json", HTTP_IDEMPOTENCY_KEY="INV-BATCH")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(InventoryMovement.objects.count(), 2)
        replay = self.client.post(url, self.batch, format="json", HTTP_IDEMPOTENCY_KEY="INV-BATCH")
        self.assertEqual(replay.status_code, 201, replay.data)
        self.assertEqual([row["id"] for row in replay.data], [row["id"] for row in response.data])
        self.assertEqual(InventoryMovement.objects.count(), 2)

    def test_single_audit_failure_rolls_back_and_same_key_can_retry(self):
        url = "/api/inventory-movements/"
        with patch("crm.audit.record_operation", side_effect=RuntimeError("synthetic audit failure")):
            with self.assertRaises(RuntimeError):
                self.client.post(url, self.single, format="json", HTTP_IDEMPOTENCY_KEY="INV-SINGLE-AUDIT")
        self.assertFalse(InventoryMovement.objects.exists())
        self.assertFalse(FulfillmentIdempotency.objects.filter(key="INV-SINGLE-AUDIT").exists())
        response = self.client.post(url, self.single, format="json", HTTP_IDEMPOTENCY_KEY="INV-SINGLE-AUDIT")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(InventoryMovement.objects.count(), 1)

    def test_replay_succeeds_after_the_original_stock_was_consumed(self):
        InventoryMovement.objects.create(movement_no="INV-OPEN", movement_date="2026-11-06", type="adjust_in", sku=self.sku, quantity=5)
        payload = {**self.single, "type": "sample_out"}
        first = self.client.post("/api/inventory-movements/", payload, format="json", HTTP_IDEMPOTENCY_KEY="INV-OUT")
        self.assertEqual(first.status_code, 201, first.data)
        replay = self.client.post("/api/inventory-movements/", payload, format="json", HTTP_IDEMPOTENCY_KEY="INV-OUT")
        self.assertEqual(replay.status_code, 201, replay.data)
        self.assertEqual(replay.data["id"], first.data["id"])
        self.assertEqual(InventoryMovement.objects.filter(type="sample_out").count(), 1)


@override_settings(APP_STAGE="development", DEBUG=True, DEVELOPMENT_SUPERADMIN=True, RBAC_ENFORCEMENT=False, AUDIT_LOG_ENABLED=True)
@skipUnless(connection.vendor == "postgresql", "并发测试需要 PostgreSQL")
class InventoryRequestConcurrencyTests(TransactionTestCase):
    def test_same_batch_concurrently_records_each_movement_once(self):
        sku = SKU.objects.create(product=Product.objects.create(code="INV-RACE-P", name="合成产品"), sku="INV-RACE-SKU")
        payload = {"movement_date": "2026-11-06", "type": "adjust_in", "items": [{"sku": sku.pk, "quantity": "5"}, {"sku": sku.pk, "quantity": "3"}]}
        barrier = Barrier(2)

        def submit():
            close_old_connections()
            try:
                barrier.wait(timeout=15)
                response = APIClient().post("/api/inventory-movements/batch/", payload, format="json", HTTP_IDEMPOTENCY_KEY="INV-RACE")
                return response.status_code, [row["id"] for row in response.data], response.headers.get("Idempotent-Replay")
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: submit(), range(2)))
        self.assertEqual([item[0] for item in results], [201, 201])
        self.assertEqual(results[0][1], results[1][1])
        self.assertEqual(sum(item[2] == "true" for item in results), 1)
        self.assertEqual(InventoryMovement.objects.count(), 2)
