"""Only synthesize authenticated identities in the runner-owned SQLite DB."""
import hashlib
import json
import os
from pathlib import Path
import sys
import uuid

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "test_support.isolated_settings")
import django
django.setup()
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sessions.backends.db import SessionStore
from django.core.serializers.json import DjangoJSONEncoder
from test_support.isolated_runtime import verify_isolated_runtime
from crm.models import Order, PurchaseOrder, InventoryMovement, PaymentPlan, Transaction

verify_isolated_runtime(settings=settings, database_must_exist=True)


def snapshot():
    values = {model.__name__: list(model.objects.order_by("pk").values()) for model in (Order, PurchaseOrder, InventoryMovement, PaymentPlan, Transaction)}
    return {"sha256": hashlib.sha256(json.dumps(values, cls=DjangoJSONEncoder, sort_keys=True).encode()).hexdigest(), "counts": {key: len(rows) for key, rows in values.items()}}


if "--snapshot" in sys.argv:
    print(json.dumps(snapshot()))
else:
    users = []
    prefix = "synthetic_finance_" + uuid.uuid4().hex[:10]
    for label in ("maker", "reviewer"):
        user = get_user_model().objects.create_superuser(prefix + "_" + label, "", None)
        session = SessionStore()
        session["_auth_user_id"] = str(user.pk)
        session["_auth_user_backend"] = "django.contrib.auth.backends.ModelBackend"
        session["_auth_user_hash"] = user.get_session_auth_hash()
        session.save()
        users.append({"id": user.pk, "session": session.session_key})
    destination = Path(os.environ["FINANCE_AUTH_EVIDENCE_DIR"])
    destination.mkdir(parents=True, exist_ok=True)
    # Ephemeral credentials stay only in the owned runner directory, not Git.
    (destination / "fixture.json").write_text(json.dumps({"maker": users[0], "reviewer": users[1], "before": snapshot()}), encoding="utf-8")
    print(json.dumps({"synthetic_users": [u["id"] for u in users], "core_tables": snapshot(), "rbac_changed": False}))
