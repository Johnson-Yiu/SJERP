"""Extend the isolated ISS-055 fixture with a synthetic hidden attachment."""
import json
import os
from pathlib import Path
import runpy

runpy.run_path('browser-run/iss055/seed.py', run_name='__main__')
from django.core.files.base import ContentFile
from django.utils import timezone
from crm.models import FollowUp, FollowUpAttachment

target = Path(os.environ['ISS055_EVIDENCE_DIR']) / 'fixture.json'
fixture = json.loads(target.read_text(encoding='utf8'))
followup = FollowUp.objects.create(customer_id=fixture['hidden_id'], followed_at=timezone.now(), content='Synthetic private attachment')
attachment = FollowUpAttachment(follow_up=followup, name='synthetic.txt', content_type='text/plain', size=9)
attachment.file.save('synthetic.txt', ContentFile(b'synthetic'), save=True)
fixture['hidden_attachment'] = attachment.file.name
target.write_text(json.dumps(fixture, ensure_ascii=False, indent=2), encoding='utf8')
