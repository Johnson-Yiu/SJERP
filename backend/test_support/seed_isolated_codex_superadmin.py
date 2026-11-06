"""Create the named test superuser only inside the isolated browser database."""

import os

import django

django.setup()

from django.contrib.auth import get_user_model
from django.conf import settings

from test_support.isolated_runtime import verify_isolated_runtime


verify_isolated_runtime(settings=settings, database_must_exist=True)
username = os.environ.get("CODEX_TEST_USERNAME", "")
password = os.environ.get("CODEX_TEST_PASSWORD", "")
if username != "codex" or not password:
    raise SystemExit("The isolated browser profile needs the configured codex test credentials.")

user, _created = get_user_model().objects.get_or_create(
    username=username,
    defaults={"email": "codex@example.test"},
)
user.email = "codex@example.test"
user.first_name = "codex"
user.last_name = ""
user.is_active = True
user.is_staff = True
user.is_superuser = True
user.set_password(password)
user.save()
print("Isolated codex superuser seeded; credentials omitted.")
