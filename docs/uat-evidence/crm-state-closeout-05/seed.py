"""Seed only a runner-owned C5 SQLite database."""
import json
import os
import sys
from pathlib import Path

import django

django.setup()
from django.conf import settings
from django.utils import timezone
from crm.models import Contact, Customer, FollowUp, NewProductReminder

database = Path(settings.DATABASES["default"]["NAME"]).resolve()
root = Path(os.environ["ISOLATED_TEST_ROOT"]).resolve()
assert database == Path(os.environ["ISOLATED_TEST_DATABASE"]).resolve()
assert root in database.parents and root in Path(settings.MEDIA_ROOT).resolve().parents
namespace = sys.argv[1]
assert namespace.startswith("C5-")

buyers = [
    Customer.objects.create(code=f"{namespace}-{suffix}", name=f"{namespace} 合成客户{suffix}", region="原业务区域")
    for suffix in ("A", "B")
]
contacts = [
    Contact.objects.create(customer=buyer, name=f"{namespace} {suffix} 长名称国际照明采购与项目协调联系人", phone="010-5550100")
    for buyer, suffix in zip(buyers, ("A", "B"))
]
followups = [
    FollowUp.objects.create(customer=buyer, contact=contact, subject=f"{namespace} 跟进{suffix}", content="原合成正文", followed_at=timezone.now())
    for buyer, contact, suffix in zip(buyers, contacts, ("A", "B"))
]
reminder = NewProductReminder.objects.create(customer=buyers[0], requirement=f"{namespace} 现有合成需求", created_by="C5 synthetic fixture")
print(json.dumps(dict(
    buyers=[{"id": row.pk, "name": row.name} for row in buyers],
    contacts=[{"id": row.pk, "name": row.name} for row in contacts],
    followups=[row.pk for row in followups],
    reminder=reminder.pk,
), ensure_ascii=False))
