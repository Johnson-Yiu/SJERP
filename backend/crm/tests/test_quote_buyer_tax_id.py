from datetime import date
from io import BytesIO
from pathlib import Path
from shutil import copy2
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase, override_settings
from openpyxl import load_workbook
from rest_framework.test import APIClient

from crm.models import Customer, Product, Quote, SKU
from crm.serializers import QuoteSerializer


class QuoteBuyerTaxTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        from crm.quote_template_snapshot import PROJECT_ROOT
        from crm.quotation_template_config import quotation_templates
        directory = TemporaryDirectory(prefix="quote-tax-templates-")
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        for config in quotation_templates.values():
            target = root / config.file
            target.parent.mkdir(parents=True, exist_ok=True)
            copy2(PROJECT_ROOT / config.file, target)
            book = load_workbook(target)
            book.properties.creator = "Synthetic test"
            book.properties.lastModifiedBy = "Synthetic test"
            book.properties.title = "Synthetic test"
            book.properties.subject = None
            book.properties.description = None
            book.properties.keywords = None
            book.properties.category = None
            sheet = book[config.sheet]
            for row, value in enumerate(("Synthetic Seller", "Synthetic Contact", "Synthetic Address", "synthetic@example.invalid", "+00 000000"), start=3):
                sheet[f"I{row}"] = value
            start = config.lower_block.rows["bank_header"] + 1
            for row in range(start, start + 9):
                sheet[f"C{row}"] = f"SYNTHETIC-{row}"
            sheet[f"A{start + 9}"] = "Synthetic notice"
            book.save(target)
            book.close()
        patcher = patch("crm.quote_template_snapshot.PROJECT_ROOT", root)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.customer = Customer.objects.create(code="TAX-C", name="Synthetic Buyer", country="Germany")
        product = Product.objects.create(code="TAX-P", name="Synthetic Product")
        self.sku = SKU.objects.create(product=product, sku="TAX-S")

    def create_quote(self, **extra):
        data = {"customer": self.customer.pk, "quote_date": "2026-11-05", "currency": "USD", "items": [{"sku": self.sku.pk, "quantity": "1", "unit_price": "10"}], **extra}
        result = self.client.post("/api/quotes/", data, format="json")
        self.assertEqual(result.status_code, 201, result.data)
        return Quote.objects.get(pk=result.data["id"])

    def test_new_optional_tax_id_api_and_xlsx(self):
        empty = self.create_quote()
        self.assertEqual(empty.buyer_tax_id, "")
        quote = self.create_quote(buyer_tax_id="000123-A")
        api = self.client.get(f"/api/quotes/{quote.pk}/pi-data/")
        self.assertEqual(api.status_code, 200, api.data)
        self.assertEqual(api.data["buyer"]["tax_id"], "000123-A")
        self.assertIn("000123-A", api.data["print_html"])
        for template in ("standard_en_no_discount", "standard_en_with_discount"):
            response = self.client.get(f"/api/quotes/{quote.pk}/export/", {"template_id": template})
            self.assertEqual(response.status_code, 200, response.data if hasattr(response, "data") else "")
            book = load_workbook(BytesIO(response.content))
            try:
                self.assertEqual(book["PI"]["B6"].value, "000123-A")
                self.assertEqual(book["PI"]["B6"].data_type, "s")
            finally:
                book.close()

    def test_rejects_nontext_null_and_excel_formula_for_new_quote(self):
        base = {"customer": self.customer.pk, "quote_date": "2026-11-05", "items": [{"sku": self.sku.pk, "quantity": "1", "unit_price": "10"}]}
        for value in (123, None, "=1+1"):
            with self.subTest(value=value):
                result = self.client.post("/api/quotes/", {**base, "buyer_tax_id": value}, format="json")
                self.assertEqual(result.status_code, 400)
                self.assertIn("buyer_tax_id", result.data)

    def test_legacy_unknown_and_revision_cannot_change_tax(self):
        for value in (None, "", "000123"):
            with self.subTest(value=value):
                quote = self.create_quote()
                Quote.objects.filter(pk=quote.pk).update(buyer_tax_id=value)
                for changed in ("NEW",):
                    rejected = self.client.post(f"/api/quotes/{quote.pk}/revise/", {"revision_summary": "No overwrite", "buyer_tax_id": changed}, format="json")
                    if value is None:
                        self.assertEqual(rejected.status_code, 400)
                    else:
                        self.assertEqual(rejected.status_code, 201, rejected.data)
                        self.assertEqual(rejected.data["buyer_tax_id"], changed)
                revised = self.client.post(f"/api/quotes/{quote.pk}/revise/", {"revision_summary": "Inherit"}, format="json")
                self.assertEqual(revised.status_code, 201, revised.data)
                self.assertEqual(revised.data["buyer_tax_id"], value)
                quote.refresh_from_db()
                self.assertEqual(quote.buyer_tax_id, value)
                quote.buyer_tax_id = "changed"
                with self.assertRaises(ValidationError):
                    quote.save()

    def test_order_confirmation_revision_inherits_tax(self):
        for value in (None, "", "000456"):
            with self.subTest(value=value):
                quote = self.create_quote()
                Quote.objects.filter(pk=quote.pk).update(buyer_tax_id=value)
                draft = self.client.get(f"/api/quotes/{quote.pk}/order-draft/")
                self.assertEqual(draft.status_code, 200, draft.data)
                saved = self.client.post("/api/orders/", dict(draft.data, shipping_fee="1.00"), format="json")
                self.assertEqual(saved.status_code, 201, saved.data)
                confirmed = self.client.post(f"/api/orders/{saved.data['id']}/confirm/", {}, format="json")
                self.assertEqual(confirmed.status_code, 200, confirmed.data)
                from crm.models import Order
                revised = Order.objects.get(pk=saved.data["id"]).quote
                self.assertNotEqual(revised.pk, quote.pk)
                self.assertEqual(revised.buyer_tax_id, value)

    @override_settings(APP_STAGE="production", DEBUG=False, DEVELOPMENT_SUPERADMIN=False, RBAC_ENFORCEMENT=True)
    def test_tax_redacted_without_customer_permission(self):
        quote = Quote.objects.create(quote_no="TAX-REDACT", customer=self.customer, quote_date=date(2026, 11, 5), buyer_tax_id="PRIVATE")
        self.assertIsNone(QuoteSerializer(quote, context={"user": AnonymousUser()}).data["buyer_tax_id"])

    def test_legacy_template_is_not_rewritten(self):
        from crm.quote_template_snapshot import PRINT_TEMPLATE_PATH
        original = PRINT_TEMPLATE_PATH.read_text(encoding="utf-8")
        old = original.replace('{{ buyer.tax_id|default_if_none:"" }}', '')
        with patch("crm.quote_template_snapshot.PRINT_TEMPLATE_PATH") as template:
            template.read_text.return_value = old
            quote = self.create_quote(buyer_tax_id="000987")
        api = self.client.get(f"/api/quotes/{quote.pk}/pi-data/")
        self.assertEqual(api.status_code, 200)
        self.assertEqual(api.data["buyer"]["tax_id"], "000987")
        self.assertNotIn("000987", api.data["print_html"])
        revision = self.client.post(f"/api/quotes/{quote.pk}/revise/", {"revision_summary": "Inherit"}, format="json")
        self.assertEqual(revision.status_code, 201, revision.data)
        child = Quote.objects.get(pk=revision.data["id"])
        self.assertEqual(child.pi_template_snapshots, quote.pi_template_snapshots)
        self.assertEqual(child.buyer_tax_id, "000987")


class QuoteBuyerTaxMigrationTests(TransactionTestCase):
    def test_cross_migration_rollback_is_rejected_before_schema_changes(self):
        from django.db.migrations.recorder import MigrationRecorder

        executor = MigrationExecutor(connection)
        leaves = executor.loader.graph.leaf_nodes()
        self.addCleanup(lambda: MigrationExecutor(connection).migrate(leaves))
        # Empty later migrations can reverse before 0115 rejects protected facts.
        # Start at that guard so schema/state comparisons cover the refusal.
        start = [("crm", "0115_party_replacement")]
        executor.migrate(start)
        apps = executor.loader.project_state(start).apps
        customer_model = apps.get_model("crm", "Customer")
        quote_model = apps.get_model("crm", "Quote")
        request_model = apps.get_model("crm", "PartyVersionRequest")
        approval_model = apps.get_model("crm", "PartyVersionApproval")
        user_model = apps.get_model("auth", "User")
        customer = customer_model.objects.create(code="TAX-CROSS-C", name="Synthetic buyer", country="Germany")
        quote = quote_model.objects.create(quote_no="TAX-CROSS-Q", customer_id=customer.pk,
            quote_date=date(2025, 1, 1), buyer_country_snapshot=None, buyer_tax_id=None)

        def schema_and_migrations():
            names = (quote_model._meta.db_table, request_model._meta.db_table, approval_model._meta.db_table)
            with connection.cursor() as cursor:
                tables = set(connection.introspection.table_names(cursor))
                columns = {name: tuple(col.name for col in connection.introspection.get_table_description(cursor, name))
                           for name in names if name in tables}
            return tables, columns, set(MigrationRecorder(connection).applied_migrations())

        expected = schema_and_migrations()
        def assert_rejected(message):
            with self.assertRaisesMessage(RuntimeError, message):
                MigrationExecutor(connection).migrate([("crm", "0108_history_append_only_truncate")])
            self.assertEqual(schema_and_migrations(), expected)

        for value in ("000123", ""):
            with self.subTest(tax=value):
                quote_model.objects.filter(pk=quote.pk).update(buyer_tax_id=value)
                assert_rejected("报价主体快照已存在，拒绝回退")
                self.assertEqual(quote_model.objects.get(pk=quote.pk).buyer_tax_id, value)
        quote_model.objects.filter(pk=quote.pk).update(buyer_tax_id=None)
        for value in ("Germany", ""):
            with self.subTest(country=value):
                quote_model.objects.filter(pk=quote.pk).update(buyer_country_snapshot=value)
                assert_rejected("报价主体快照已存在，拒绝回退")
                self.assertEqual(quote_model.objects.get(pk=quote.pk).buyer_country_snapshot, value)
        quote_model.objects.filter(pk=quote.pk).update(buyer_country_snapshot=None)
        initiator = user_model.objects.create(username="tax-cross-initiator")
        approver = user_model.objects.create(username="tax-cross-approver")
        request = request_model.objects.create(quote_id=quote.pk, initiator_id=initiator.pk,
            base_snapshot={}, proposed_snapshot={}, base_fingerprint="base", content_fingerprint="content",
            change_type="correction", reason="Synthetic", evidence="Synthetic", source_trust="unknown")
        assert_rejected("主体记录已存在，拒绝回退")
        self.assertTrue(request_model.objects.filter(pk=request.pk).exists())
        approval = approval_model.objects.create(request_id=request.pk, approver_id=approver.pk,
            approved_fingerprint="content", note="Synthetic")
        assert_rejected("主体记录已存在，拒绝回退")
        self.assertTrue(approval_model.objects.filter(pk=approval.pk).exists())

    def test_legacy_null_and_loss_guard(self):
        old = [("crm", "0110_party_version")]
        new = [("crm", "0111_quote_buyer_tax_id")]
        executor = MigrationExecutor(connection)
        executor.migrate(old)
        apps = executor.loader.project_state(old).apps
        customer = apps.get_model("crm", "Customer").objects.create(code="TAX-MIG-C", name="Legacy", country="Germany")
        quote = apps.get_model("crm", "Quote").objects.create(quote_no="TAX-MIG-Q", customer_id=customer.pk, quote_date=date(2025, 1, 1))
        try:
            executor = MigrationExecutor(connection)
            executor.migrate(new)
            model = executor.loader.project_state(new).apps.get_model("crm", "Quote")
            self.assertIsNone(model.objects.get(pk=quote.pk).buyer_tax_id)
            for value in ("000123", ""):
                with self.subTest(value=value):
                    model.objects.filter(pk=quote.pk).update(buyer_tax_id=value)
                    with self.assertRaisesMessage(RuntimeError, "已有买方税号快照"):
                        MigrationExecutor(connection).migrate(old)
                    self.assertEqual(model.objects.get(pk=quote.pk).buyer_tax_id, value)
            # Fault setup in the isolated DB only: restore unknown before rollback.
            model.objects.filter(pk=quote.pk).update(buyer_tax_id=None)
            MigrationExecutor(connection).migrate(old)
            old_model = MigrationExecutor(connection).loader.project_state(old).apps.get_model("crm", "Quote")
            self.assertTrue(old_model.objects.filter(pk=quote.pk).exists())
        finally:
            executor = MigrationExecutor(connection)
            executor.migrate(executor.loader.graph.leaf_nodes())
