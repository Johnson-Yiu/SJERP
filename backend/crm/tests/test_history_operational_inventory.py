from datetime import date
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import tempfile
import unittest
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import DatabaseError, close_old_connections, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase, override_settings
from rest_framework.exceptions import APIException

from crm import history_operational_inventory as opening
from crm.models import (HistoryInventoryBaseline, HistoryInventoryBaselineReversal, InventoryMovement,
    HistoryTakeoverGroup, HistoryTakeoverHandoff, HistoryTakeoverSourceRecord)
from crm.services.fulfillment import bulk_sku_metrics, sku_metrics
from crm.tests.test_history_takeover import HistoryTakeoverFixtureMixin


@override_settings(AUDIT_LOG_ENABLED=True)
class HistoricalInventoryBaselineTests(HistoryTakeoverFixtureMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.application, self.group, _ = self.application_and_group()
        base = f"/api/import/history-takeovers/{self.application.pk}/groups/{self.group.pk}/"
        reviewed = self.client.post(base + "review/", {"decision": "approve", "note": "已核对合成盘点", "confirm_manual": True}, format="json")
        self.assertEqual(reviewed.status_code, 200, reviewed.data)
        executed = self.client.post(base + "execute/", {}, format="json")
        self.assertEqual(executed.status_code, 200, executed.data)
        self.source = HistoryTakeoverSourceRecord.objects.get(group=self.group, record_type="库存盘点")
        self.maker = get_user_model().objects.create_superuser(username="historical-inventory-maker", password="test-only")
        self.reviewer = get_user_model().objects.create_superuser(username="historical-inventory-reviewer", password="test-only")
        self.row = {"source_id": self.source.pk, "goods_ownership": "own", "unit_cost": "3.25", "cost_currency": "USD", "no_lot": False}

    def submit_and_approve(self):
        proposal, replay = opening.propose(self.group.pk, [self.row], "合成盘点与成本已核实", True, self.maker)
        self.assertFalse(replay)
        self.assertEqual(proposal.status, "pending_review")
        with self.assertRaises(APIException):
            opening.approve(self.group.pk, "本人不可复核", self.maker)
        opening.approve(self.group.pk, "已核对合成原始盘点", self.reviewer)

    def test_baseline_is_not_movement_and_reversal_preserves_evidence(self):
        self.submit_and_approve()
        self.assertEqual(sku_metrics(self.sku)["actual_quantity"], 0)
        ids, replay = opening.execute(self.group.pk, self.maker)
        self.assertFalse(replay)
        self.assertEqual(opening.execute(self.group.pk, self.maker), (ids, True))
        self.assertEqual(sku_metrics(self.sku)["actual_quantity"], Decimal("18"))
        self.assertEqual(bulk_sku_metrics([self.sku.pk])[self.sku.pk]["actual_quantity"], Decimal("18"))
        sku_response = self.client.get(f"/api/skus/{self.sku.pk}/")
        self.assertEqual(sku_response.status_code, 200, sku_response.data)
        self.assertEqual(Decimal(sku_response.data["stock_quantity"]), Decimal("18"))
        context_response = self.client.get(f"/api/context/skus/{self.sku.pk}/")
        self.assertEqual(context_response.status_code, 200, context_response.data)
        self.assertEqual(Decimal(str(context_response.data["metrics"][0][1])), Decimal("18"))
        self.assertFalse(InventoryMovement.objects.exists())
        baseline = HistoryInventoryBaseline.objects.get(pk=ids[0])
        self.assertEqual((baseline.lot_reference, baseline.unit_cost, baseline.cost_currency), ("LOT-HT-01", Decimal("3.25"), "USD"))
        with self.assertRaises(DjangoValidationError):
            HistoryInventoryBaseline.objects.filter(pk=baseline.pk).update(quantity=0)
        with self.assertRaises(DatabaseError), transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("UPDATE crm_historyinventorybaseline SET quantity = 0 WHERE id = %s", [baseline.pk])
        self.assertFalse(opening.reverse(self.group.pk, "合成盘点撤销", self.reviewer))
        self.assertTrue(opening.reverse(self.group.pk, "重复请求", self.reviewer))
        self.assertEqual(sku_metrics(self.sku)["actual_quantity"], 0)
        self.assertEqual(HistoryInventoryBaselineReversal.objects.count(), 1)
        self.assertTrue(HistoryInventoryBaseline.objects.filter(pk=baseline.pk).exists())

    def test_third_party_owned_goods_do_not_increase_available_stock(self):
        self.row["goods_ownership"] = "third_party"
        self.submit_and_approve()
        opening.execute(self.group.pk, self.maker)
        self.assertEqual(sku_metrics(self.sku)["actual_quantity"], 0)
        self.assertEqual(HistoryInventoryBaseline.objects.get().goods_ownership, "third_party")

    def test_existing_or_later_movements_prevent_unsafe_baseline_and_reversal(self):
        self.submit_and_approve()
        InventoryMovement.objects.create(movement_no="SYNTH-EXISTING-MOVEMENT", movement_date=date(2025, 1, 2), type="other_in", sku=self.sku, quantity=1)
        with self.assertRaises(APIException):
            opening.execute(self.group.pk, self.maker)
        self.assertFalse(HistoryInventoryBaseline.objects.exists())

    def test_later_movement_blocks_reversal(self):
        self.submit_and_approve()
        opening.execute(self.group.pk, self.maker)
        InventoryMovement.objects.create(movement_no="SYNTH-LATER-MOVEMENT", movement_date=date(2025, 1, 2), type="other_in", sku=self.sku, quantity=1)
        with self.assertRaises(APIException):
            opening.reverse(self.group.pk, "不能删除后续业务", self.reviewer)
        self.assertFalse(HistoryInventoryBaselineReversal.objects.exists())
        self.assertEqual(sku_metrics(self.sku)["actual_quantity"], Decimal("19"))

    def test_audit_failure_rolls_back_entire_group(self):
        self.submit_and_approve()
        with patch("crm.history_operational_inventory._event", side_effect=RuntimeError("audit failed")):
            with self.assertRaisesRegex(RuntimeError, "audit failed"):
                opening.execute(self.group.pk, self.maker)
        self.assertFalse(HistoryInventoryBaseline.objects.exists())
        self.assertEqual(sku_metrics(self.sku)["actual_quantity"], 0)
        self.group.refresh_from_db()
        self.assertEqual(self.group.inventory_handoff_status, "approved")

    def test_source_change_after_approval_is_rejected(self):
        self.submit_and_approve()
        snapshot = dict(self.source.source_snapshot)
        snapshot["resolved"] = {**snapshot["resolved"], "counted_quantity": "19"}
        HistoryTakeoverSourceRecord.objects.filter(pk=self.source.pk).update(source_snapshot=snapshot)
        with self.assertRaises(APIException):
            opening.execute(self.group.pk, self.maker)
        self.assertFalse(HistoryInventoryBaseline.objects.exists())


@unittest.skipUnless(connection.vendor == "postgresql", "requires real PostgreSQL row locks")
@override_settings(FILE_UPLOAD_TEMP_DIR=tempfile.gettempdir())
class HistoricalInventoryPostgresTests(HistoryTakeoverFixtureMixin, TransactionTestCase):
    def setUp(self):
        super().setUp()
        self.application, self.group, _ = self.application_and_group()
        base = f"/api/import/history-takeovers/{self.application.pk}/groups/{self.group.pk}/"
        review = self.client.post(base + "review/", {"decision": "approve", "note": "合成盘点", "confirm_manual": True}, format="json")
        self.assertEqual(review.status_code, 200, review.data)
        result = self.client.post(base + "execute/", {}, format="json")
        self.assertEqual(result.status_code, 200, result.data)
        self.source = HistoryTakeoverSourceRecord.objects.get(group=self.group, record_type="库存盘点")
        self.maker = get_user_model().objects.create_superuser(username="history-stock-pg-maker", password="test-only")
        self.reviewer = get_user_model().objects.create_superuser(username="history-stock-pg-reviewer", password="test-only")
        self._prepare(self.group, self.source)

    def _prepare(self, group, source):
        row = {"source_id": source.pk, "goods_ownership": "own", "unit_cost": "3.25", "cost_currency": "USD", "no_lot": False}
        opening.propose(group.pk, [row], "合成盘点", True, self.maker)
        opening.approve(group.pk, "已复核合成盘点", self.reviewer)

    def _race(self, group_ids):
        gate = Barrier(2)
        def run(group_id):
            close_old_connections()
            try:
                user = get_user_model().objects.get(pk=self.maker.pk)
                gate.wait(timeout=20)
                try:
                    return opening.execute(group_id, user)
                except APIException:
                    return "conflict"
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:
            return list(pool.map(run, group_ids))

    def test_same_group_concurrent_replay_creates_one_baseline(self):
        results = self._race([self.group.pk, self.group.pk])
        self.assertCountEqual([item[1] for item in results], [True, False])
        self.assertEqual(HistoryInventoryBaseline.objects.count(), 1)
        self.assertEqual(sku_metrics(self.sku)["actual_quantity"], Decimal("18"))
        self.assertFalse(InventoryMovement.objects.exists())

    def test_different_groups_same_sku_cannot_double_the_stock(self):
        original = {**self.source.source_snapshot["source"], "group_id": "PG-OTHER", "source_record_id": "OTHER-COUNT"}
        resolved = {**self.source.source_snapshot["resolved"], "group_id": "PG-OTHER", "source_record_id": "OTHER-COUNT"}
        other = HistoryTakeoverGroup.objects.create(application=self.application, source_group_id="PG-OTHER", source_system="PG-OTHER", truth_status="真实", coverage_status="complete", status="executed", source_rows={"库存盘点": [{"row": 2, "data": original}]})
        HistoryTakeoverHandoff.objects.create(group=other, kind="inventory", payload={"count_baselines": [resolved]})
        source = HistoryTakeoverSourceRecord.objects.create(group=other, source_system="PG-OTHER", record_type="库存盘点", source_record_id="OTHER-COUNT", source_snapshot={"source": original, "resolved": resolved})
        self._prepare(other, source)
        results = self._race([self.group.pk, other.pk])
        self.assertEqual(results.count("conflict"), 1)
        self.assertEqual(HistoryInventoryBaseline.objects.count(), 1)
        self.assertEqual(sku_metrics(self.sku)["actual_quantity"], Decimal("18"))

    def test_migration_refuses_to_remove_existing_baseline(self):
        opening.execute(self.group.pk, self.maker)
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        try:
            with self.assertRaisesRegex(RuntimeError, "Refusing to remove recorded historical inventory baselines"):
                executor.migrate([("crm", "0103_merge_finance_and_history")])
            self.assertEqual(HistoryInventoryBaseline.objects.count(), 1)
        finally:
            MigrationExecutor(connection).migrate(latest)
