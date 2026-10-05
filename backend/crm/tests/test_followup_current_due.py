from datetime import date, datetime, timezone as datetime_timezone
from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from crm.models import Customer, FollowUp


TODAY = date(2026, 10, 5)


class CurrentDueFollowUpApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.sequence = 0

    def customer(self, name):
        self.sequence += 1
        return Customer.objects.create(code=f"P2C4-{self.sequence:03}", name=name)

    def follow_up(self, customer, *, day, due, subject="Next action", hour=9):
        return FollowUp.objects.create(
            customer=customer,
            followed_at=datetime(2026, 9, day, hour, tzinfo=datetime_timezone.utc),
            type="call",
            subject=subject,
            next_follow_up=due,
        )

    def follow_up_rows(self, **params):
        response = self.client.get("/api/follow-ups/", params)
        self.assertEqual(response.status_code, 200, response.data)
        return response.data.get("results", response.data)

    @patch("crm.views.timezone.localdate", return_value=TODAY)
    def test_due_endpoint_returns_only_latest_current_follow_up_per_customer(self, _localdate):
        due_today_customer = self.customer("Due Today")
        superseded_customer = self.customer("Superseded by Future")
        latest_overdue_customer = self.customer("Latest Overdue")
        latest_without_date_customer = self.customer("Latest Has No Date")
        multiple_due_customer = self.customer("Several Historical Due")

        old_due_today = self.follow_up(due_today_customer, day=1, due=date(2026, 9, 30), subject="Old due")
        latest_due_today = self.follow_up(due_today_customer, day=20, due=TODAY, subject="Due today")
        superseded_old = self.follow_up(superseded_customer, day=1, due=date(2026, 9, 20), subject="Superseded overdue")
        superseded_latest = self.follow_up(superseded_customer, day=20, due=date(2026, 10, 20), subject="Future next action")
        latest_overdue_old_future = self.follow_up(latest_overdue_customer, day=1, due=date(2026, 10, 30), subject="Old future")
        latest_overdue = self.follow_up(latest_overdue_customer, day=20, due=date(2026, 10, 1), subject="Latest overdue")
        no_date_old = self.follow_up(latest_without_date_customer, day=1, due=date(2026, 9, 25), subject="Old before null")
        latest_no_date = self.follow_up(latest_without_date_customer, day=20, due=None, subject="No next date")
        multiple_due_old = self.follow_up(multiple_due_customer, day=1, due=date(2026, 9, 1), subject="Earlier overdue")
        multiple_due_latest = self.follow_up(multiple_due_customer, day=20, due=date(2026, 9, 30), subject="Latest overdue")

        rows = self.follow_up_rows(due="true")
        ids = [row["id"] for row in rows]

        self.assertEqual(set(ids), {latest_due_today.id, latest_overdue.id, multiple_due_latest.id})
        self.assertEqual(len(ids), len(set(ids)))
        self.assertNotIn(old_due_today.id, ids)
        self.assertNotIn(superseded_old.id, ids)
        self.assertNotIn(superseded_latest.id, ids)
        self.assertNotIn(latest_overdue_old_future.id, ids)
        self.assertNotIn(no_date_old.id, ids)
        self.assertNotIn(latest_no_date.id, ids)
        self.assertNotIn(multiple_due_old.id, ids)
        historical_ids = [row["id"] for row in self.follow_up_rows()]
        self.assertIn(old_due_today.id, historical_ids)
        self.assertIn(superseded_old.id, historical_ids)

    @patch("crm.views.timezone.localdate", return_value=TODAY)
    def test_same_followed_at_uses_higher_id_as_latest_and_includes_due_today(self, _localdate):
        customer = self.customer("Timestamp tie")
        timestamp = datetime(2026, 10, 1, 9, tzinfo=datetime_timezone.utc)
        older_id = FollowUp.objects.create(
            customer=customer, followed_at=timestamp, type="call", subject="Lower ID", next_follow_up=TODAY,
        )
        latest_id = FollowUp.objects.create(
            customer=customer, followed_at=timestamp, type="call", subject="Higher ID", next_follow_up=TODAY,
        )

        rows = self.follow_up_rows(due="true")

        self.assertEqual([row["id"] for row in rows], [latest_id.id])
        self.assertGreater(latest_id.id, older_id.id)

    @patch("crm.views.timezone.localdate", return_value=TODAY)
    def test_due_combines_with_customer_search_and_ordering(self, _localdate):
        alpha = self.customer("Alpha Lighting")
        alpha_earlier_customer = self.customer("Alpha Lighting East")
        beta = self.customer("Beta Lighting")
        alpha_later_due = self.follow_up(alpha, day=2, due=date(2026, 10, 3), subject="Alpha later")
        alpha_earlier_due = self.follow_up(alpha_earlier_customer, day=3, due=date(2026, 9, 20), subject="Alpha earlier")
        beta_due = self.follow_up(beta, day=4, due=TODAY, subject="Beta today")
        future_customer = self.customer("Alpha future customer")
        self.follow_up(future_customer, day=5, due=date(2026, 10, 20), subject="Alpha future")

        by_customer = self.follow_up_rows(due="true", customer=alpha.id)
        by_search = self.follow_up_rows(due="true", search="Alpha")
        combined = self.follow_up_rows(due="true", customer=alpha_earlier_customer.id, search="earlier")
        ordered = self.follow_up_rows(due="true", ordering="next_follow_up")

        self.assertEqual({row["id"] for row in by_customer}, {alpha_later_due.id})
        self.assertEqual({row["id"] for row in by_search}, {alpha_later_due.id, alpha_earlier_due.id})
        self.assertEqual([row["id"] for row in combined], [alpha_earlier_due.id])
        self.assertEqual([row["id"] for row in ordered], [alpha_earlier_due.id, alpha_later_due.id, beta_due.id])
        self.assertNotIn(beta_due.id, [row["id"] for row in by_customer])

    @patch("crm.views.timezone.localdate", return_value=TODAY)
    def test_dashboard_count_and_five_display_rows_share_the_complete_due_queryset(self, _localdate):
        latest_due = []
        for index in range(7):
            customer = self.customer(f"Due customer {index}")
            self.follow_up(customer, day=1, due=date(2026, 9, 1), subject="Superseded history")
            latest_due.append(self.follow_up(
                customer,
                day=20,
                due=date(2026, 9, 20 + index),
                subject=f"Current due {index}",
            ))

        future_customer = self.customer("Not due now")
        self.follow_up(future_customer, day=1, due=date(2026, 9, 2), subject="Historical due")
        self.follow_up(future_customer, day=20, due=date(2026, 10, 20), subject="Current future")

        due_response = self.client.get("/api/follow-ups/", {"due": "true"})
        dashboard_response = self.client.get("/api/dashboard/")
        self.assertEqual(due_response.status_code, 200, due_response.data)
        self.assertEqual(dashboard_response.status_code, 200, dashboard_response.data)
        complete_due_ids = [row["id"] for row in due_response.data["results"]]
        dashboard_ids = [row["id"] for row in dashboard_response.data["due_follow_ups"]]

        self.assertEqual(due_response.data["count"], 7)
        self.assertEqual(dashboard_response.data["summary"]["follow_ups_due"], due_response.data["count"])
        self.assertEqual(len(dashboard_ids), 5)
        self.assertEqual(dashboard_ids, complete_due_ids[:5])
        self.assertEqual(dashboard_ids, [row.id for row in latest_due[:5]])
