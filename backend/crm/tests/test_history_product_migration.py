from datetime import date

from django.db import connection
from django.db.migrations.exceptions import IrreversibleError
from django.db.migrations.executor import MigrationExecutor

from crm.tests.historical_database import HistoricalMigrationTestCase


class HistoricalProductMigrationTests(HistoricalMigrationTestCase):
    def test_upgrade_empty_rollback_and_protect_archive_rules_and_audit(self):
        old = [("crm", "0128_merge_release_integration")]
        h1 = [("crm", "0130_history_product_candidate_rules")]
        MigrationExecutor(connection).migrate(old)
        MigrationExecutor(connection).migrate(h1)
        MigrationExecutor(connection).migrate(old)
        self.assertNotIn("crm_archivedhistoryline", connection.introspection.table_names())

        executor = MigrationExecutor(connection)
        executor.migrate(h1)
        apps = executor.loader.project_state(h1).apps
        customer = apps.get_model("crm", "Customer").objects.create(code="H2-MC", name="合成客户")
        product = apps.get_model("crm", "Product").objects.create(code="H2-MP", name="合成商品", sales_model_prefix="H2M")
        sku = apps.get_model("crm", "SKU").objects.create(sku="H2-MS", product=product, unit="pcs")
        order = apps.get_model("crm", "Order").objects.create(
            customer=customer, order_no="H2-MO", order_date=date(2024, 1, 1), historical_only=True,
        )
        app = apps.get_model("crm", "HistoryTakeoverApplication").objects.create(source_file_name="h2-synthetic.xlsx", source_sha256="a" * 64)
        group = apps.get_model("crm", "HistoryTakeoverGroup").objects.create(application=app, source_group_id="H2-MG")
        archive = apps.get_model("crm", "ArchivedHistoryLine").objects.create(
            order=order, quantity=1, unit_price="0.335", facts={"sku_code": "H2-ORIGINAL"},
        )
        source = apps.get_model("crm", "HistoryTakeoverSourceRecord").objects.create(
            group=group, source_system="H2 Legacy", record_type="销售明细", source_record_id="H2-1",
            target_model="crm.ArchivedHistoryLine", target_id=archive.pk,
        )
        apps.get_model("crm", "HistoryProductLink").objects.create(source=source, sku=sku)
        apps.get_model("crm", "HistoryProductRule").objects.create(scope_key="a" * 64, confirmed_source=source, sku=sku)
        apps.get_model("crm", "HistoryTakeoverEvent").objects.create(
            application=app, group=group, event_type="history_product_linked", details={"source_id": source.pk},
        )
        with self.assertRaisesRegex(IrreversibleError, "不能降级"):
            MigrationExecutor(connection).migrate(old)
        self.assertIn(h1[0], MigrationExecutor(connection).loader.applied_migrations)
        for name in ("ArchivedHistoryLine", "HistoryProductLink", "HistoryProductRule", "HistoryTakeoverEvent"):
            self.assertEqual(apps.get_model("crm", name).objects.count(), 1)
        self.assertEqual(apps.get_model("crm", "HistoryTakeoverSourceRecord").objects.get().target_id, archive.pk)
