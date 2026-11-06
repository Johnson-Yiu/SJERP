"""Versioned quote-party fingerprint primitives; not a storage or authorization API.

V1 delegates to the existing quote fingerprint unchanged. V2 binds that exact
digest to separately supplied structured facts. Callers must persist and lock
the same facts atomically and integrate the descriptor into every approval,
application and formalization check before treating V2 as an enforced boundary.
Legacy records need an explicit V1 descriptor derived from their stored hash;
do not rewrite those records or attach newly inferred details to them. V2
descriptors and facts must be stored together on newly opted-in documents.
No migration, API, consumer or persistence integration is provided here.
"""

from copy import deepcopy
import hashlib
import hmac
import json
import re

from django.core.exceptions import ValidationError


LEGACY_VERSION = 1
STRUCTURED_VERSION = 2
_DOMAIN = "crm.quote-party-fingerprint.v2"
_ROLES = ("buyer", "seller")
_ADDRESS_FIELDS = ("address", "recipient", "phone", "email")
_COMMON_FIELDS = ("registration_id", "registered_address", "billing", "shipping")
_SELLER_FIELDS = ("country", "tax_id")
_HEX_DIGEST = re.compile(r"^[0-9a-f]{64}$")


def validate_party_details(details):
    """Return a validated copy; no field is inferred from a master or template.

    Every leaf must explicitly be a string or None. None means unknown and
    remains distinct from the explicitly recorded empty string.
    """
    if isinstance(details, dict) and details.get('schema') == 'party-document-details-v1':
        from .party_document_details import validate_details
        return validate_details(details)
    if not isinstance(details, dict) or set(details) != set(_ROLES):
        raise ValidationError("必须提供买卖双方的结构化资料。")
    for role in _ROLES:
        party = details[role]
        fields = set(_COMMON_FIELDS + (_SELLER_FIELDS if role == "seller" else ()))
        if not isinstance(party, dict) or set(party) != fields:
            raise ValidationError(f"{role} 主体资料字段不完整。")
        for field, value in party.items():
            if field in {"billing", "shipping"}:
                if not isinstance(value, dict) or set(value) != set(_ADDRESS_FIELDS):
                    raise ValidationError(f"{role}.{field} 地址资料字段不完整。")
                leaves = value.values()
            else:
                leaves = (value,)
            if any(item is not None and not isinstance(item, str) for item in leaves):
                raise ValidationError(f"{role}.{field} 只能为文本或未知。")
    return deepcopy(details)


def quote_party_fingerprint(quote, items, *, version, details=None):
    """Return an explicit version descriptor without changing V1 inputs."""
    if type(version) is not int or version not in (LEGACY_VERSION, STRUCTURED_VERSION):
        raise ValidationError("不支持的报价主体指纹版本。")
    if version == LEGACY_VERSION and details is not None:
        raise ValidationError("旧版指纹不能用于带扩展主体资料的报价。")
    validated = validate_party_details(details) if version == STRUCTURED_VERSION else None
    from .party_version import _quote_fingerprint

    legacy_digest = _quote_fingerprint(quote, items)
    if version == LEGACY_VERSION:
        return {"version": LEGACY_VERSION, "sha256": legacy_digest}
    payload = {"domain": _DOMAIN, "quote_v1_sha256": legacy_digest, "party_details": validated}
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return {"version": STRUCTURED_VERSION, "sha256": hashlib.sha256(encoded).hexdigest()}


def verify_quote_party_fingerprint(quote, items, descriptor, *, details=None):
    """Verify exactly the recorded version; never fall back across versions."""
    if not isinstance(descriptor, dict) or set(descriptor) != {"version", "sha256"}:
        raise ValidationError("报价主体指纹描述无效。")
    digest = descriptor["sha256"]
    if not isinstance(digest, str) or not _HEX_DIGEST.fullmatch(digest):
        raise ValidationError("报价主体指纹格式无效。")
    expected = quote_party_fingerprint(quote, items, version=descriptor["version"], details=details)
    if not hmac.compare_digest(expected["sha256"], digest):
        raise ValidationError("报价或主体资料已变更。")
    return True
