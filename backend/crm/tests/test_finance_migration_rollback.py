from datetime import date
from decimal import Decimal
from uuid import uuid4

from crm.tests.historical_database import HistoricalMigrationTestCase
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.recorder import MigrationRecorder


class FinanceMigrationRollbackMatrixTests(HistoricalMigrationTestCase):
    """Exercise finance rollback guards through Django's migration executor."""

    merge_migration = ("crm", "0097_merge_quote_and_cash_review")
    account_migration = ("crm", "0098_finance_accounts")
    workflow_migration = ("crm", "0099_finance_closeout_workflows")
    legacy_link_migration = ("crm", "0100_finance_legacy_fact_links")
    transfer_migration = ("crm", "0101_finance_historical_transfer_links")
    bank_voucher_migration = ("crm", "0102_bank_private_voucher_binding")

    def _latest_targets(self):
        return tuple(MigrationExecutor(connection).loader.graph.leaf_nodes())

    def _migrate_to(self, target):
        executor = MigrationExecutor(connection)
        executor.migrate([("crm", target)])
        return executor.loader.project_state([("crm", target)]).apps

    def _restore_latest(self, targets):
        MigrationExecutor(connection).migrate(targets)
        applied = set(MigrationRecorder(connection).applied_migrations())
        self.assertTrue(set(targets).issubset(applied))

    def _new_voucher(self, apps, *, scope=None, bank_sources=None, suffix=None):
        model = apps.get_model("crm", "FinanceVoucher")
        suffix = suffix or uuid4().hex
        values = {
            "file": f"finance-vouchers/test/{suffix}.pdf",
            "original_name": f"{suffix}.pdf",
            "sha256": "a" * 64,
            "size": 1,
            "actor": {"kind": "synthetic_migration_test"},
        }
        model_fields = {field.name for field in model._meta.get_fields()}
        if scope is not None and "scope" in model_fields:
            values["scope"] = scope
        if bank_sources is not None and "bank_sources" in model_fields:
            values["bank_sources"] = bank_sources
        return model.objects.create(**values)

    def _new_account(self, apps, *, suffix=None):
        suffix = suffix or uuid4().hex[:12]
        return apps.get_model("crm", "FinanceAccount").objects.create(
            code=f"MT-{suffix}",
            name="迁移矩阵合成账户",
            account_type="bank",
        )

    def _new_instruction(self, apps, *, suffix=None):
        suffix = suffix or uuid4().hex
        return apps.get_model("crm", "FinanceInstruction").objects.create(
            request_key=f"migration-test-{suffix}",
            request_hash="b" * 64,
            payload={"fixture": "finance-migration-rollback"},
            kind="receipt",
            reason="隔离迁移回退矩阵",
            created_actor={"kind": "synthetic_migration_test"},
        )

    def _new_fact(self, apps, *, legacy_parent=None, suffix=None):
        suffix = suffix or uuid4().hex
        account = self._new_account(apps, suffix=suffix[:12])
        voucher = self._new_voucher(apps, suffix=suffix)
        instruction = self._new_instruction(apps, suffix=suffix)
        values = {
            "instruction": instruction,
            "account": account,
            "voucher": voucher,
            "actual_date": date(2026, 11, 4),
            "amount": Decimal("1.00"),
            "direction": "income",
            "kind": "receipt",
            "source_system": "migration-test",
            "source_key": suffix,
            "actor": {"kind": "synthetic_migration_test"},
        }
        model = apps.get_model("crm", "FinanceFact")
        if legacy_parent is not None and "legacy_parent" in {field.name for field in model._meta.get_fields()}:
            values["legacy_parent"] = legacy_parent
        return model.objects.create(**values)

    def _new_cash_event(self, apps, *, suffix=None):
        suffix = suffix or uuid4().hex
        return apps.get_model("crm", "RmbCashEvent").objects.create(
            event_no=f"MIG-{suffix[:20]}",
            request_key=f"migration-test-event-{suffix}",
            request_hash="c" * 64,
            request_payload={"fixture": "finance-migration-rollback"},
            kind="cny_direct",
            currency="CNY",
            amount=Decimal("1.0000"),
            direction="income",
            bank_date=date(2026, 11, 4),
            bank_net_amount=Decimal("1.00"),
            source_account="SYNTH-FX",
            rmb_account="SYNTH-CNY",
            bank_reference=f"MIG-REF-{suffix[:20]}",
            created_actor={"kind": "synthetic_migration_test"},
        )

    def test_empty_0098_through_0102_can_reverse_and_remigrate(self):
        latest = self._latest_targets()
        guarded_migrations = {
            self.account_migration,
            self.workflow_migration,
            self.legacy_link_migration,
            self.transfer_migration,
            self.bank_voucher_migration,
        }
        try:
            self._migrate_to(self.bank_voucher_migration[1])
            self._migrate_to(self.merge_migration[1])
            applied = set(MigrationRecorder(connection).applied_migrations())
            self.assertTrue(guarded_migrations.isdisjoint(applied))

            self._restore_latest(latest)
            applied = set(MigrationRecorder(connection).applied_migrations())
            self.assertTrue(guarded_migrations.issubset(applied))
            tables = set(connection.introspection.table_names())
            for table in (
                "crm_financeaccount",
                "crm_financevoucher",
                "crm_financeaccountmapping",
                "crm_financefact",
                "crm_financeclassification",
                "crm_financeinstruction",
                "crm_financetransfermatch",
                "crm_financereview",
                "crm_financehistoricaltransfer",
                "crm_financebankvoucherbinding",
            ):
                self.assertIn(table, tables)
        finally:
            self._restore_latest(latest)

    def test_0098_refuses_reverse_when_account_history_exists(self):
        latest = self._latest_targets()
        try:
            apps = self._migrate_to(self.account_migration[1])
            account = self._new_account(apps)

            with self.assertRaisesRegex(RuntimeError, "已有资金账户历史"):
                MigrationExecutor(connection).migrate([self.merge_migration])

            account_model = apps.get_model("crm", "FinanceAccount")
            self.assertTrue(account_model.objects.filter(pk=account.pk).exists())
            self.assertIn(self.account_migration, MigrationRecorder(connection).applied_migrations())
        finally:
            self._restore_latest(latest)

    def test_0099_refuses_reverse_when_voucher_history_exists(self):
        latest = self._latest_targets()
        try:
            apps = self._migrate_to(self.workflow_migration[1])
            voucher = self._new_voucher(apps)

            with self.assertRaisesRegex(RuntimeError, "已有资金或凭证历史"):
                MigrationExecutor(connection).migrate([self.account_migration])

            voucher_model = apps.get_model("crm", "FinanceVoucher")
            self.assertTrue(voucher_model.objects.filter(pk=voucher.pk).exists())
            self.assertIn(self.workflow_migration, MigrationRecorder(connection).applied_migrations())
        finally:
            self._restore_latest(latest)

    def test_0100_refuses_reverse_when_fact_links_to_legacy_cash_event(self):
        latest = self._latest_targets()
        try:
            apps = self._migrate_to(self.legacy_link_migration[1])
            event = self._new_cash_event(apps)
            fact = self._new_fact(apps, legacy_parent=event)

            with self.assertRaisesRegex(RuntimeError, "已有旧资金关联事实"):
                MigrationExecutor(connection).migrate([self.workflow_migration])

            fact_model = apps.get_model("crm", "FinanceFact")
            self.assertEqual(fact_model.objects.get(pk=fact.pk).legacy_parent_id, event.pk)
            self.assertIn(self.legacy_link_migration, MigrationRecorder(connection).applied_migrations())
        finally:
            self._restore_latest(latest)

    def test_0101_refuses_reverse_when_historical_transfer_exists(self):
        latest = self._latest_targets()
        try:
            apps = self._migrate_to(self.transfer_migration[1])
            outgoing = self._new_cash_event(apps)
            incoming = self._new_cash_event(apps)
            outgoing_voucher = self._new_voucher(apps)
            incoming_voucher = self._new_voucher(apps)
            transfer = apps.get_model("crm", "FinanceHistoricalTransfer").objects.create(
                outgoing_legacy=outgoing,
                incoming_legacy=incoming,
                outgoing_voucher=outgoing_voucher,
                incoming_voucher=incoming_voucher,
                reason="隔离历史转账回退测试",
                actor={"kind": "synthetic_migration_test"},
            )

            with self.assertRaisesRegex(RuntimeError, "已有历史转账核实记录"):
                MigrationExecutor(connection).migrate([self.legacy_link_migration])

            transfer_model = apps.get_model("crm", "FinanceHistoricalTransfer")
            self.assertTrue(transfer_model.objects.filter(pk=transfer.pk).exists())
            self.assertIn(self.transfer_migration, MigrationRecorder(connection).applied_migrations())
        finally:
            self._restore_latest(latest)

    def test_0102_refuses_reverse_when_bank_voucher_binding_exists(self):
        latest = self._latest_targets()
        try:
            apps = self._migrate_to(self.bank_voucher_migration[1])
            event = self._new_cash_event(apps)
            voucher = self._new_voucher(apps, scope="account", bank_sources=[])
            binding = apps.get_model("crm", "FinanceBankVoucherBinding").objects.create(
                event=event,
                voucher=voucher,
                actor={"kind": "synthetic_migration_test"},
            )

            with self.assertRaisesRegex(RuntimeError, "银行私有凭证历史"):
                MigrationExecutor(connection).migrate([self.transfer_migration])

            binding_model = apps.get_model("crm", "FinanceBankVoucherBinding")
            self.assertTrue(binding_model.objects.filter(pk=binding.pk).exists())
            self.assertIn(self.bank_voucher_migration, MigrationRecorder(connection).applied_migrations())
        finally:
            self._restore_latest(latest)

    def test_0102_refuses_reverse_when_bank_scope_voucher_has_no_binding(self):
        latest = self._latest_targets()
        try:
            apps = self._migrate_to(self.bank_voucher_migration[1])
            voucher = self._new_voucher(apps, scope="bank", bank_sources=[])

            with self.assertRaisesRegex(RuntimeError, "银行私有凭证历史"):
                MigrationExecutor(connection).migrate([self.transfer_migration])

            voucher_model = apps.get_model("crm", "FinanceVoucher")
            self.assertTrue(voucher_model.objects.filter(pk=voucher.pk, scope="bank").exists())
            self.assertIn(self.bank_voucher_migration, MigrationRecorder(connection).applied_migrations())
        finally:
            self._restore_latest(latest)

    def test_0102_refuses_reverse_when_account_scope_voucher_has_bank_sources(self):
        latest = self._latest_targets()
        try:
            apps = self._migrate_to(self.bank_voucher_migration[1])
            sources = [17]
            voucher = self._new_voucher(apps, scope="account", bank_sources=sources)

            try:
                MigrationExecutor(connection).migrate([self.transfer_migration])
            except RuntimeError as exc:
                self.assertRegex(str(exc), "银行私有凭证历史")
                voucher_model = apps.get_model("crm", "FinanceVoucher")
                restored = voucher_model.objects.get(pk=voucher.pk)
                self.assertEqual(restored.scope, "account")
                self.assertEqual(restored.bank_sources, sources)
                self.assertIn(self.bank_voucher_migration, MigrationRecorder(connection).applied_migrations())
                return

            # Prove the consequence before failing: reverse drops bank_sources;
            # reapplying 0102 supplies [], so the persisted association is gone.
            self.assertNotIn(self.bank_voucher_migration, MigrationRecorder(connection).applied_migrations())
            self._restore_latest(latest)
            from crm.models import FinanceVoucher as CurrentFinanceVoucher

            restored = CurrentFinanceVoucher.objects.get(pk=voucher.pk)
            self.assertEqual(restored.scope, "account")
            self.assertEqual(restored.bank_sources, [])
            self.fail("0102 rollback silently discarded the nonempty bank_sources association")
        finally:
            self._restore_latest(latest)

    def test_0102_account_scope_voucher_without_bank_sources_can_reverse(self):
        latest = self._latest_targets()
        try:
            apps = self._migrate_to(self.bank_voucher_migration[1])
            voucher = self._new_voucher(apps, scope="account", bank_sources=[])

            MigrationExecutor(connection).migrate([self.transfer_migration])
            self.assertNotIn(self.bank_voucher_migration, MigrationRecorder(connection).applied_migrations())
            self._restore_latest(latest)

            from crm.models import FinanceVoucher

            restored = FinanceVoucher.objects.get(pk=voucher.pk)
            self.assertEqual(restored.scope, "account")
            self.assertEqual(restored.bank_sources, [])
        finally:
            self._restore_latest(latest)
