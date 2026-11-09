"""Stable request identity shared by finance entry points."""
from django.core.exceptions import ValidationError
from django.db.models import Model


def require_finance_request_key(request):
    key = str(request.headers.get("Idempotency-Key") or "").strip()
    if not key or len(key) > 128 or any(ord(char) < 32 or ord(char) == 127 for char in key):
        raise ValidationError("本次操作缺少有效的请求标识，请重新打开登记窗口。")
    return key


def finance_request_value(value):
    """Replace model instances with stable identities before canonical hashing."""
    if isinstance(value, Model):
        return {"model": value._meta.label_lower, "id": value.pk}
    if isinstance(value, dict):
        return {key: finance_request_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [finance_request_value(item) for item in value]
    return value
