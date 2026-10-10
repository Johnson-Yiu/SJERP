from datetime import date
from importlib import import_module
from types import SimpleNamespace

from django.apps import apps
from django.db import connection
from django.test import TestCase
from rest_framework.test import APIClient

from crm.models import Customer, FollowUp
from crm.querysets import current_due_follow_ups


class FollowUpSafetyTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = Customer.objects.create(code="SAFE-A", name="Follow-up Safety", next_follow_up=date(2026, 10, 20))

    def create(self, **changes):
        data = {"customer": self.customer.pk, "followed_at": "2026-10-10T10:00:00+08:00", "type": "call", "content": "实际沟通内容"}
        data.update(changes)
        return self.client.post('/api/follow-ups/', data, format='json')

    def schedule(self, customer=None):
        customer = customer or self.customer
        customer.refresh_from_db()
        return customer.next_follow_up

    def test_empty_communication_rejected_including_partial_edits(self):
        for content, result in [("", ""), (" \n", "\t")]:
            self.assertEqual(self.create(content=content, result=result).status_code, 400)
        saved = self.create()
        response = self.client.patch(f'/api/follow-ups/{saved.data["id"]}/', {"content": "", "result": ""}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(FollowUp.objects.get(pk=saved.data['id']).content, "实际沟通内容")

    def test_content_only_and_result_only_are_valid(self):
        self.assertEqual(self.create(result="").status_code, 201)
        self.assertEqual(self.create(content="", result="客户确认规格").status_code, 201)

    def test_default_keep_preserves_manual_customer_plan(self):
        response = self.create()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['next_follow_up_mode'], 'keep')
        self.assertEqual(self.schedule(), date(2026, 10, 20))
        self.client.delete(f'/api/follow-ups/{response.data["id"]}/')
        self.assertEqual(self.schedule(), date(2026, 10, 20))

    def test_set_and_clear_require_explicit_valid_dates(self):
        self.assertEqual(self.create(next_follow_up_mode='set').status_code, 400)
        self.assertEqual(self.create(next_follow_up_mode='clear', next_follow_up='2026-10-25').status_code, 400)
        self.assertEqual(self.create(next_follow_up_mode='set', next_follow_up='2026-10-25').status_code, 201)
        self.assertEqual(self.schedule(), date(2026, 10, 25))
        self.assertEqual(self.create(next_follow_up_mode='clear').status_code, 201)
        self.assertIsNone(self.schedule())

    def test_keep_skips_to_prior_set_or_clear_and_due_queue_uses_customer_plan(self):
        self.create(next_follow_up_mode='set', next_follow_up='2026-10-25')
        latest = self.create(next_follow_up_mode='keep', next_follow_up='2026-11-01')
        self.assertIsNone(latest.data['next_follow_up'])
        self.assertEqual(self.schedule(), date(2026, 10, 25))
        self.assertEqual(list(current_due_follow_ups(today=date(2026, 10, 25)).values_list('id', flat=True)), [latest.data['id']])
        self.create(next_follow_up_mode='clear')
        self.create(next_follow_up_mode='keep')
        self.assertIsNone(self.schedule())

    def test_delete_and_edit_restore_previous_decision(self):
        first = self.create(next_follow_up_mode='set', next_follow_up='2026-10-20')
        second = self.create(next_follow_up_mode='set', next_follow_up='2026-10-25')
        self.create(next_follow_up_mode='keep')
        self.assertEqual(self.client.delete(f'/api/follow-ups/{second.data["id"]}/').status_code, 204)
        self.assertEqual(self.schedule(), date(2026, 10, 20))
        clear = self.create(next_follow_up_mode='clear')
        self.assertIsNone(self.schedule())
        self.client.patch(f'/api/follow-ups/{clear.data["id"]}/', {'next_follow_up_mode': 'keep'}, format='json')
        self.assertEqual(self.schedule(), date(2026, 10, 20))
        self.client.patch(f'/api/follow-ups/{first.data["id"]}/', {'next_follow_up': '2026-10-23'}, format='json')
        self.assertEqual(self.schedule(), date(2026, 10, 23))

    def test_moving_follow_up_recomputes_both_customers(self):
        self.create(next_follow_up_mode='set', next_follow_up='2026-10-20')
        moving = self.create(next_follow_up_mode='set', next_follow_up='2026-10-25')
        other = Customer.objects.create(code='SAFE-B', name='Other customer', next_follow_up=date(2026, 11, 1))
        response = self.client.patch(f'/api/follow-ups/{moving.data["id"]}/', {'customer': other.pk}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.schedule(), date(2026, 10, 20))
        self.assertEqual(self.schedule(other), date(2026, 10, 25))
        self.client.patch(f'/api/follow-ups/{moving.data["id"]}/', {'next_follow_up_mode': 'keep'}, format='json')
        self.assertIsNone(self.schedule(other))

    def test_legacy_data_migration_does_not_change_customers(self):
        dated = FollowUp.objects.create(customer=self.customer, followed_at='2026-10-01T10:00:00Z', next_follow_up=date(2026, 10, 25))
        empty = FollowUp.objects.create(customer=self.customer, followed_at='2026-10-02T10:00:00Z')
        migrate = import_module('crm.migrations.0073_followup_next_follow_up_mode').mark_legacy_follow_up_modes
        migrate(apps, SimpleNamespace(connection=connection))
        dated.refresh_from_db(); empty.refresh_from_db()
        self.assertEqual(dated.next_follow_up_mode, 'set')
        self.assertEqual(empty.next_follow_up_mode, 'keep')
        self.assertEqual(self.schedule(), date(2026, 10, 20))
