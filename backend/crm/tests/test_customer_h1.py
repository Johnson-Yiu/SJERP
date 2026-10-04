from datetime import date, datetime, timezone as datetime_timezone
from decimal import Decimal
from pathlib import Path
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from crm.models import (
    Contact,
    ContractChangeRequest,
    Customer,
    FollowUp,
    FollowUpAttachment,
    InventoryReservation,
    Order,
    OrderItem,
    OperationLog,
    PaymentPlan,
    Product,
    Quote,
    SKU,
    Transaction,
)


class CustomerSalesMetricsTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = Customer.objects.create(code="H1-SALES-C", name="H1 Sales Buyer")
        self.product = Product.objects.create(code="H1-SALES-P", name="H1 Sales Product")
        self.sku = SKU.objects.create(product=self.product, sku="H1-SALES-SKU")

    def create_order(self, order_no, order_date, status, amount):
        order = Order.objects.create(
            order_no=order_no,
            customer=self.customer,
            order_date=order_date,
            status=status,
            exchange_rate="2",
            shipping_fee="12",
            discount="4",
        )
        OrderItem.objects.create(order=order, sku=self.sku, quantity="1", unit_price=amount, cost_price="0")
        return order

    def test_customer_sales_metrics_use_formal_order_total_and_approved_adjustments(self):
        year = timezone.localdate().year
        draft = self.create_order("H1-SALES-DRAFT", date(year, 9, 20), "draft", "100")
        latest_draft = self.create_order("H1-SALES-DRAFT-LATEST", date(year, 9, 20), "draft", "50")
        formal = self.create_order("H1-SALES-CONFIRMED", date(year, 9, 15), "confirmed", "200")
        ContractChangeRequest.objects.create(order=formal, amount_delta="20", status="approved", notes="Approved sales adjustment")
        cancelled = self.create_order("H1-SALES-CANCELLED", date(year, 9, 29), "cancelled", "300")

        detail = self.client.get(f"/api/customers/{self.customer.id}/")

        self.assertEqual(detail.status_code, status.HTTP_200_OK, detail.data)
        self.assertEqual(detail.data["order_count"], 1)
        self.assertEqual(Decimal(detail.data["sales_amount"]), Decimal("456"))

        insights = self.client.get(f"/api/customers/{self.customer.id}/insights/")
        self.assertEqual(insights.status_code, status.HTTP_200_OK, insights.data)
        current_year = next(row for row in insights.data["yearly"] if row["year"] == year)
        self.assertEqual(current_year["orders"], 1)
        self.assertEqual(Decimal(current_year["sales"]), Decimal("456"))
        self.assertEqual(Decimal(insights.data["top_products"][0]["sales"]), Decimal("400"))
        recent_ids = [row["id"] for row in insights.data["recent_orders"]]
        self.assertNotIn(cancelled.id, recent_ids)
        self.assertEqual(recent_ids[:3], [latest_draft.id, draft.id, formal.id])

        context = self.client.get(f"/api/context/customers/{self.customer.id}/")
        metrics = {row[0]: row[1] for row in context.data["metrics"]}
        self.assertEqual(Decimal(metrics["累计销售额"]), Decimal("456"))
        self.assertEqual(metrics["订单"], 1)


class CustomerFollowUpProjectionTests(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create(code="H1-FOLLOW-C", name="H1 Follow-up Buyer")

    @staticmethod
    def at(day):
        return datetime(2026, 9, day, 9, 0, tzinfo=datetime_timezone.utc)

    def test_customer_next_follow_up_tracks_latest_record_updates_deletes_and_null(self):
        first = FollowUp.objects.create(
            customer=self.customer,
            followed_at=self.at(1),
            type="email",
            next_follow_up=date(2026, 9, 10),
        )
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.next_follow_up, date(2026, 9, 10))

        second = FollowUp.objects.create(
            customer=self.customer,
            followed_at=self.at(5),
            type="call",
            next_follow_up=date(2026, 9, 20),
        )
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.next_follow_up, date(2026, 9, 20))

        second.next_follow_up = date(2026, 9, 25)
        second.save(update_fields=["next_follow_up"])
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.next_follow_up, date(2026, 9, 25))

        second.delete()
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.next_follow_up, date(2026, 9, 10))

        first.next_follow_up = None
        first.save(update_fields=["next_follow_up"])
        self.customer.refresh_from_db()
        self.assertIsNone(self.customer.next_follow_up)

    def test_moving_follow_up_recomputes_both_customers(self):
        other = Customer.objects.create(code="H1-FOLLOW-OTHER", name="H1 Other Buyer")
        moving = FollowUp.objects.create(
            customer=self.customer,
            followed_at=self.at(1),
            type="email",
            next_follow_up=date(2026, 9, 10),
        )
        FollowUp.objects.create(
            customer=other,
            followed_at=self.at(5),
            type="call",
            next_follow_up=date(2026, 9, 20),
        )

        moving.customer = other
        moving.followed_at = self.at(10)
        moving.save(update_fields=["customer", "followed_at"])

        self.customer.refresh_from_db()
        other.refresh_from_db()
        self.assertIsNone(self.customer.next_follow_up)
        self.assertEqual(other.next_follow_up, date(2026, 9, 10))


class FollowUpOwnershipAndAttachmentTests(TestCase):
    def setUp(self):
        self.media_dir = tempfile.TemporaryDirectory()
        self.media_settings = override_settings(MEDIA_ROOT=self.media_dir.name)
        self.media_settings.enable()
        self.client = APIClient()
        self.customer_a = Customer.objects.create(code="H1-FU-A", name="H1 Follow-up A")
        self.customer_b = Customer.objects.create(code="H1-FU-B", name="H1 Follow-up B")
        self.contact_a = Contact.objects.create(customer=self.customer_a, name="A Contact")
        self.contact_b = Contact.objects.create(customer=self.customer_b, name="B Contact")

    def tearDown(self):
        self.media_settings.disable()
        self.media_dir.cleanup()

    def test_contact_must_belong_to_selected_customer(self):
        response = self.client.post("/api/follow-ups/", {
            "customer": self.customer_a.id,
            "contact": self.contact_b.id,
            "followed_at": "2026-09-01T09:00:00Z",
            "type": "email",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("contact", response.data)

    def test_invalid_relation_updates_preserve_follow_up_and_its_attachment(self):
        follow_up = FollowUp.objects.create(
            customer=self.customer_a,
            contact=self.contact_a,
            followed_at="2026-09-01T09:00:00Z",
            type="email",
            subject="Original subject",
            content="Original content",
        )
        attachment = FollowUpAttachment.objects.create(
            follow_up=follow_up,
            file=SimpleUploadedFile("record.txt", b"original", content_type="text/plain"),
            name="record.txt",
            content_type="text/plain",
            size=8,
        )

        wrong_contact = self.client.patch(
            f"/api/follow-ups/{follow_up.id}/",
            {"contact": self.contact_b.id},
            format="json",
        )
        wrong_customer = self.client.patch(
            f"/api/follow-ups/{follow_up.id}/",
            {"customer": self.customer_b.id},
            format="json",
        )

        self.assertEqual(wrong_contact.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(wrong_customer.status_code, status.HTTP_400_BAD_REQUEST)
        follow_up.refresh_from_db()
        self.assertEqual(follow_up.customer_id, self.customer_a.id)
        self.assertEqual(follow_up.contact_id, self.contact_a.id)
        self.assertEqual(follow_up.subject, "Original subject")
        self.assertTrue(FollowUpAttachment.objects.filter(pk=attachment.pk, follow_up=follow_up).exists())

        updated = self.client.patch(f"/api/follow-ups/{follow_up.id}/", {
            "subject": "Updated subject",
            "content": "Updated content",
            "result": "Confirmed details",
            "next_action": "Send documents",
            "next_follow_up": "2026-09-25",
        }, format="json")
        self.assertEqual(updated.status_code, status.HTTP_200_OK, updated.data)
        self.assertEqual(updated.data["subject"], "Updated subject")
        self.assertEqual(updated.data["content"], "Updated content")
        self.assertEqual(updated.data["result"], "Confirmed details")
        self.assertEqual(updated.data["next_action"], "Send documents")
        self.assertEqual(updated.data["next_follow_up"], "2026-09-25")
        self.assertEqual(len(updated.data["attachments"]), 1)
        self.assertEqual(updated.data["attachments"][0]["id"], attachment.id)

    def test_delete_follow_up_attachment_removes_record_and_stored_file(self):
        follow_up = FollowUp.objects.create(
            customer=self.customer_a,
            contact=self.contact_a,
            followed_at=timezone.now(),
            type="email",
            subject="Attachment delete test",
        )
        attachment = FollowUpAttachment.objects.create(
            follow_up=follow_up,
            file=SimpleUploadedFile("delete-this.txt", b"stored contents", content_type="text/plain"),
            name="delete-this.txt",
            content_type="text/plain",
            size=15,
        )
        stored_path = attachment.file.path
        self.assertTrue(Path(stored_path).exists())

        response = self.client.delete(f"/api/follow-ups/{follow_up.id}/attachments/{attachment.id}/")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(FollowUpAttachment.objects.filter(pk=attachment.pk).exists())
        self.assertFalse(Path(stored_path).exists())

    def test_follow_up_attachment_cannot_be_deleted_through_another_follow_up(self):
        follow_up_a = FollowUp.objects.create(
            customer=self.customer_a,
            contact=self.contact_a,
            followed_at=timezone.now(),
            type="email",
            subject="Owner follow-up",
        )
        follow_up_b = FollowUp.objects.create(
            customer=self.customer_b,
            contact=self.contact_b,
            followed_at=timezone.now(),
            type="email",
            subject="Other follow-up",
        )
        attachment = FollowUpAttachment.objects.create(
            follow_up=follow_up_a,
            file=SimpleUploadedFile("owned-by-a.txt", b"keep me", content_type="text/plain"),
            name="owned-by-a.txt",
            content_type="text/plain",
            size=7,
        )
        stored_path = attachment.file.path

        response = self.client.delete(f"/api/follow-ups/{follow_up_b.id}/attachments/{attachment.id}/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(FollowUpAttachment.objects.filter(pk=attachment.pk, follow_up=follow_up_a).exists())
        self.assertTrue(Path(stored_path).exists())

    @override_settings(AUDIT_LOG_ENABLED=True)
    def test_delete_follow_up_attachment_logs_filename_when_audit_is_enabled(self):
        follow_up = FollowUp.objects.create(
            customer=self.customer_a,
            contact=self.contact_a,
            followed_at=timezone.now(),
            type="email",
            subject="Attachment audit test",
        )
        attachment = FollowUpAttachment.objects.create(
            follow_up=follow_up,
            file=SimpleUploadedFile("audit-target.md", b"notes", content_type="text/markdown"),
            name="audit-target.md",
            content_type="text/markdown",
            size=5,
        )
        self.client.force_authenticate(get_user_model().objects.create_user(username="attachment-auditor"))

        response = self.client.delete(f"/api/follow-ups/{follow_up.id}/attachments/{attachment.id}/")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        log = OperationLog.objects.get(object_id=str(follow_up.id), action_label="删除跟进附件")
        self.assertEqual(log.metadata["file_name"], "audit-target.md")


class CustomerAndContactDeleteGuardTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def customer(self, suffix):
        return Customer.objects.create(code=f"H1-DELETE-{suffix}", name=f"H1 Delete {suffix}")

    def test_customer_delete_is_blocked_for_each_historical_relation(self):
        follow_up_customer = self.customer("FU")
        FollowUp.objects.create(customer=follow_up_customer, followed_at="2026-09-01T09:00:00Z", type="email")

        quote_customer = self.customer("Q")
        Quote.objects.create(quote_no="H1-DELETE-Q", customer=quote_customer, quote_date=date(2026, 9, 1))

        order_customer = self.customer("O")
        Order.objects.create(order_no="H1-DELETE-O", customer=order_customer, order_date=date(2026, 9, 1))

        transaction_customer = self.customer("T")
        Transaction.objects.create(
            transaction_no="H1-DELETE-TX",
            transaction_date=date(2026, 9, 1),
            direction="income",
            category="预收款",
            amount="10",
            currency="USD",
            kind="unallocated_advance",
            customer=transaction_customer,
        )

        for customer in (follow_up_customer, quote_customer, order_customer, transaction_customer):
            with self.subTest(customer=customer.name):
                response = self.client.delete(f"/api/customers/{customer.id}/")
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertTrue(Customer.objects.filter(pk=customer.pk).exists())

    def test_customer_without_history_and_contact_without_follow_up_can_be_deleted(self):
        customer = self.customer("EMPTY")
        response = self.client.delete(f"/api/customers/{customer.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Customer.objects.filter(pk=customer.pk).exists())

        another = self.customer("CONTACT")
        contact = Contact.objects.create(customer=another, name="No history")
        response = self.client.delete(f"/api/contacts/{contact.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Contact.objects.filter(pk=contact.pk).exists())

    def test_contact_with_follow_up_cannot_be_deleted(self):
        customer = self.customer("CONTACT-FU")
        contact = Contact.objects.create(customer=customer, name="History contact")
        FollowUp.objects.create(customer=customer, contact=contact, followed_at="2026-09-01T09:00:00Z", type="email")

        response = self.client.delete(f"/api/contacts/{contact.id}/")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(Contact.objects.filter(pk=contact.pk).exists())


class QuoteLifecycleActionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = Customer.objects.create(code="H1-QUOTE-C", name="H1 Quote Buyer", country="Germany")
        product = Product.objects.create(code="H1-QUOTE-P", name="H1 Quote Product")
        self.sku = SKU.objects.create(product=product, sku="H1-QUOTE-SKU")

    def create_quote(self, **overrides):
        payload = {
            "customer": self.customer.id,
            "quote_date": "2026-09-01",
            "items": [{"sku": self.sku.id, "quantity": "1", "unit_price": "10"}],
        }
        payload.update(overrides)
        response = self.client.post("/api/quotes/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        return Quote.objects.get(pk=response.data["id"])

    def test_status_payload_is_forced_to_draft_and_actions_do_not_create_quotes(self):
        quote = self.create_quote(status="accepted")
        self.assertEqual(quote.status, "draft")
        original_count = Quote.objects.count()

        sent = self.client.post(f"/api/quotes/{quote.id}/mark-sent/", {}, format="json")
        self.assertEqual(sent.status_code, status.HTTP_200_OK, sent.data)
        quote.refresh_from_db()
        self.assertEqual(quote.status, "sent")
        self.assertEqual(Quote.objects.count(), original_count)

        accepted = self.client.post(f"/api/quotes/{quote.id}/accept/", {}, format="json")
        self.assertEqual(accepted.status_code, status.HTTP_200_OK, accepted.data)
        quote.refresh_from_db()
        self.assertEqual(quote.status, "accepted")
        self.assertEqual(Quote.objects.count(), original_count)

        for action in ("mark-sent", "reject", "expire"):
            with self.subTest(action=action):
                response = self.client.post(f"/api/quotes/{quote.id}/{action}/", {}, format="json")
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Quote.objects.count(), original_count)

    def test_sent_quote_can_be_rejected_or_expired_without_creating_quote(self):
        for terminal_action, expected_status in (("reject", "rejected"), ("expire", "expired")):
            with self.subTest(action=terminal_action):
                quote = self.create_quote()
                sent = self.client.post(f"/api/quotes/{quote.id}/mark-sent/", {}, format="json")
                self.assertEqual(sent.status_code, status.HTTP_200_OK, sent.data)
                before = Quote.objects.count()

                response = self.client.post(f"/api/quotes/{quote.id}/{terminal_action}/", {}, format="json")

                self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
                quote.refresh_from_db()
                self.assertEqual(quote.status, expected_status)
                self.assertEqual(Quote.objects.count(), before)

    def test_draft_quote_can_be_accepted_or_rejected_without_creating_quote(self):
        for action, expected_status in (("accept", "accepted"), ("reject", "rejected")):
            with self.subTest(action=action):
                quote = self.create_quote()
                before = Quote.objects.count()

                response = self.client.post(f"/api/quotes/{quote.id}/{action}/", {}, format="json")

                self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
                quote.refresh_from_db()
                self.assertEqual(quote.status, expected_status)
                self.assertEqual(Quote.objects.count(), before)

    def test_revision_from_accepted_quote_preserves_source_and_starts_as_draft(self):
        source = self.create_quote()
        self.client.post(f"/api/quotes/{source.id}/mark-sent/", {}, format="json")
        self.client.post(f"/api/quotes/{source.id}/accept/", {}, format="json")
        before = Quote.objects.count()

        response = self.client.post(f"/api/quotes/{source.id}/revise/", {"revision_summary": "Accepted revision"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        source.refresh_from_db()
        revision = Quote.objects.get(pk=response.data["id"])
        self.assertEqual(source.status, "accepted")
        self.assertEqual(revision.status, "draft")
        self.assertEqual(Quote.objects.count(), before + 1)


class CustomerStageWriteGuardTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = Customer.objects.create(code="H2-STAGE-C", name="H2 Stage Buyer", country="Germany")
        self.product = Product.objects.create(code="H2-STAGE-P", name="H2 Stage Product")
        self.sku = SKU.objects.create(product=self.product, sku="H2-STAGE-SKU")

    def test_customer_status_is_read_only_and_derived_from_business_facts(self):
        self.assertEqual(self.customer.status, "lead")

        response = self.client.patch(
            f"/api/customers/{self.customer.id}/",
            {"status": "company"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.status, "lead")

        FollowUp.objects.create(
            customer=self.customer,
            followed_at="2026-09-30T09:00:00Z",
            type="email",
        )
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.status, "contact")

        response = self.client.patch(
            f"/api/customers/{self.customer.id}/",
            {"status": "lead"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.status, "contact")

        quote_response = self.client.post("/api/quotes/", {
            "customer": self.customer.id,
            "quote_date": "2026-09-30",
            "items": [{"sku": self.sku.id, "quantity": "1", "unit_price": "10"}],
        }, format="json")
        self.assertEqual(quote_response.status_code, status.HTTP_201_CREATED, quote_response.data)
        sent = self.client.post(f"/api/quotes/{quote_response.data['id']}/mark-sent/", {}, format="json")
        self.assertEqual(sent.status_code, status.HTTP_200_OK, sent.data)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.status, "opportunity")

        first_order = Order.objects.create(
            order_no="H2-STAGE-SO-1",
            customer=self.customer,
            order_date=date(2026, 9, 30),
            status="confirmed",
        )
        OrderItem.objects.create(order=first_order, sku=self.sku, quantity=1, unit_price=10)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.status, "customer")

        second_order = Order.objects.create(
            order_no="H2-STAGE-SO-2",
            customer=self.customer,
            order_date=date(2026, 9, 30),
            status="confirmed",
        )
        OrderItem.objects.create(order=second_order, sku=self.sku, quantity=1, unit_price=10)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.status, "company")


class QuoteOrderConversionGuardTests(TestCase):
    terminal_message = "该报价已拒绝或过期，请先创建新的修订版后再转为订单。"
    confirm_message = "来源报价已拒绝或过期，请先基于新的报价修订版更新订单来源。"

    def setUp(self):
        self.client = APIClient()
        self.customer = Customer.objects.create(code="H2-QUOTE-C", name="H2 Quote Buyer", country="Germany")
        self.product = Product.objects.create(code="H2-QUOTE-P", name="H2 Quote Product")
        self.sku = SKU.objects.create(product=self.product, sku="H2-QUOTE-SKU", cost_price="4")

    def create_quote(self, quote_status="draft"):
        response = self.client.post("/api/quotes/", {
            "customer": self.customer.id,
            "quote_date": "2026-09-30",
            "items": [{"sku": self.sku.id, "quantity": "1", "unit_price": "10"}],
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        quote = Quote.objects.get(pk=response.data["id"])
        if quote_status == "sent":
            transition = self.client.post(f"/api/quotes/{quote.id}/mark-sent/", {}, format="json")
        elif quote_status == "accepted":
            transition = self.client.post(f"/api/quotes/{quote.id}/accept/", {}, format="json")
        elif quote_status == "rejected":
            transition = self.client.post(f"/api/quotes/{quote.id}/reject/", {}, format="json")
        elif quote_status == "expired":
            sent = self.client.post(f"/api/quotes/{quote.id}/mark-sent/", {}, format="json")
            self.assertEqual(sent.status_code, status.HTTP_200_OK, sent.data)
            transition = self.client.post(f"/api/quotes/{quote.id}/expire/", {}, format="json")
        else:
            return quote
        self.assertEqual(transition.status_code, status.HTTP_200_OK, transition.data)
        quote.refresh_from_db()
        return quote

    def order_draft(self, quote):
        return self.client.get(f"/api/quotes/{quote.id}/order-draft/")

    def test_only_draft_sent_and_accepted_quotes_can_create_and_confirm_orders(self):
        for quote_status in ("draft", "sent", "accepted"):
            with self.subTest(quote_status=quote_status):
                quote = self.create_quote(quote_status)
                draft_response = self.order_draft(quote)
                self.assertEqual(draft_response.status_code, status.HTTP_200_OK, draft_response.data)
                created = self.client.post("/api/orders/", draft_response.data, format="json")
                self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.data)
                confirmed = self.client.post(f"/api/orders/{created.data['id']}/confirm/", {}, format="json")
                self.assertEqual(confirmed.status_code, status.HTTP_200_OK, confirmed.data)
                quote.refresh_from_db()
                self.assertEqual(quote.status, "accepted")

    def test_rejected_and_expired_quotes_cannot_supply_order_draft_or_direct_order(self):
        for quote_status in ("rejected", "expired"):
            with self.subTest(quote_status=quote_status):
                quote = self.create_quote(quote_status)
                draft_response = self.order_draft(quote)
                self.assertEqual(draft_response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertEqual(draft_response.data["detail"], self.terminal_message)

                direct = self.client.post("/api/orders/", {
                    "customer": self.customer.id,
                    "quote": quote.id,
                    "order_date": "2026-09-30",
                    "items": [{"sku": self.sku.id, "quantity": "1", "unit_price": "10"}],
                }, format="json")
                self.assertEqual(direct.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertEqual(direct.data["quote"][0], self.terminal_message)

    def test_draft_order_cannot_be_rebound_to_a_rejected_or_expired_quote(self):
        source = self.create_quote()
        draft = self.order_draft(source)
        created = self.client.post("/api/orders/", draft.data, format="json")
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.data)
        for quote_status in ("rejected", "expired"):
            with self.subTest(quote_status=quote_status):
                terminal = self.create_quote(quote_status)
                updated = self.client.patch(
                    f"/api/orders/{created.data['id']}/",
                    {"quote": terminal.id},
                    format="json",
                )
                self.assertEqual(updated.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertEqual(updated.data["quote"][0], self.terminal_message)

    def test_confirming_after_source_quote_becomes_terminal_has_no_side_effects(self):
        for terminal_action, expected_status in (("reject", "rejected"), ("expire", "expired")):
            with self.subTest(terminal_action=terminal_action):
                quote = self.create_quote()
                draft = self.order_draft(quote)
                created = self.client.post("/api/orders/", draft.data, format="json")
                self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.data)
                order_id = created.data["id"]
                if terminal_action == "expire":
                    sent = self.client.post(f"/api/quotes/{quote.id}/mark-sent/", {}, format="json")
                    self.assertEqual(sent.status_code, status.HTTP_200_OK, sent.data)
                terminal = self.client.post(f"/api/quotes/{quote.id}/{terminal_action}/", {}, format="json")
                self.assertEqual(terminal.status_code, status.HTTP_200_OK, terminal.data)
                quote_count = Quote.objects.count()
                accepted_count = Quote.objects.filter(status="accepted").count()

                confirmed = self.client.post(f"/api/orders/{order_id}/confirm/", {}, format="json")

                self.assertEqual(confirmed.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertEqual(confirmed.data["detail"], self.confirm_message)
                order = Order.objects.get(pk=order_id)
                quote.refresh_from_db()
                self.assertEqual(order.status, "draft")
                self.assertEqual(quote.status, expected_status)
                self.assertFalse(InventoryReservation.objects.filter(order_item__order=order).exists())
                self.assertFalse(PaymentPlan.objects.filter(order=order).exists())
                self.assertEqual(Quote.objects.count(), quote_count)
                self.assertEqual(Quote.objects.filter(status="accepted").count(), accepted_count)
