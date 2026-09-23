import json

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.serializers.json import DjangoJSONEncoder
from django.forms.models import model_to_dict

from .models import OperationLog


def audit_is_enabled(request=None):
    """Only authenticated operators can create audit rows when explicitly enabled."""
    if not getattr(settings, "AUDIT_LOG_ENABLED", False):
        return False
    user = getattr(request, "user", None)
    return bool(user and user.is_authenticated)


def snapshot(instance):
    """Return a JSON-safe snapshot of concrete model fields."""
    if instance is None:
        return {}
    values = model_to_dict(instance)
    values["id"] = instance.pk
    return json.loads(json.dumps(values, cls=DjangoJSONEncoder, default=str))


def _changed_fields(before, after):
    keys = set(before or {}) | set(after or {})
    return sorted(key for key in keys if (before or {}).get(key) != (after or {}).get(key))


def _object_label(instance):
    try:
        label = str(instance)
    except Exception:  # pragma: no cover - defensive for unusual __str__ methods
        label = ""
    return label[:300]


def record_operation(*, request, instance, action="custom", action_label="", before=None, after=None, metadata=None):
    """Persist one audit row, or do nothing while audit logging is disabled."""
    if not audit_is_enabled(request):
        return None
    content_type = ContentType.objects.get_for_model(instance, for_concrete_model=False)
    before_data = before or {}
    after_data = after if after is not None else snapshot(instance)
    return OperationLog.objects.create(
        content_type=content_type,
        object_id=str(instance.pk),
        entity=instance._meta.label_lower,
        entity_label=str(instance._meta.verbose_name),
        object_label=_object_label(instance),
        action=action,
        action_label=action_label or dict(OperationLog.ACTION_CHOICES).get(action, action),
        operator=request.user,
        changed_fields=_changed_fields(before_data, after_data),
        before_data=before_data,
        after_data=after_data,
        metadata=metadata or {},
        request_method=getattr(request, "method", "")[:10],
        request_path=getattr(request, "path", "")[:500],
    )


class AuditTrailMixin:
    """Add audit hooks to ordinary DRF create/update/delete operations."""

    def perform_create(self, serializer):
        instance = serializer.save()
        record_operation(request=self.request, instance=instance, action="create")

    def perform_update(self, serializer):
        before = snapshot(serializer.instance)
        instance = serializer.save()
        record_operation(request=self.request, instance=instance, action="update", before=before)

    def perform_destroy(self, instance):
        before = snapshot(instance)
        instance.delete()
        record_operation(request=self.request, instance=instance, action="delete", before=before, after={})
