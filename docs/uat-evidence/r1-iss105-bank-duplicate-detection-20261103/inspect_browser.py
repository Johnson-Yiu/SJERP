"""Inspect only the identity-verified synthetic browser database."""
import json
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "test_support.isolated_settings")
import django
django.setup()
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from crm.models import CashDuplicateReview, RmbCashEvent
from test_support.isolated_runtime import verify_isolated_runtime

verify_isolated_runtime(settings=settings, database_must_exist=True)
events = RmbCashEvent.objects.filter(event_no__startswith="SYNTH-DUP-").order_by("pk")
reviews = CashDuplicateReview.objects.filter(event__event_no__startswith="P2B-").order_by("pk")
print(json.dumps({"database": str(settings.DATABASES["default"]["NAME"]), "seed_events": list(events.values()), "reviews": list(reviews.values())}, cls=DjangoJSONEncoder))
