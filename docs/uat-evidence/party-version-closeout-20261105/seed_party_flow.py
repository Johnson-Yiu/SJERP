"""Create two synthetic authenticated staff sessions and a synthetic quote fixture."""
import io
import json
import runpy
from contextlib import redirect_stdout
from pathlib import Path
from uuid import uuid4

output = io.StringIO()
with redirect_stdout(output):
    runpy.run_path(str(Path(__file__).with_name('seed_browser.py')), run_name='__main__')
fixture = json.loads(output.getvalue().strip().splitlines()[-1])
from django.contrib.auth import get_user_model

suffix = uuid4().hex[:10]
users = get_user_model()
first = users.objects.create_user(username=f'party-a-{suffix}', password='synthetic-only-password', is_staff=True)
second = users.objects.create_user(username=f'party-b-{suffix}', password='synthetic-only-password', is_staff=True)
fixture.update(first_username=first.username, second_username=second.username, first_id=first.pk, second_id=second.pk)
print(json.dumps(fixture))
