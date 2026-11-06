"""Schema validation for explicitly entered SO/PO party details.

This module does not persist or authorize changes. Persistence must lock the
document and share the existing PartyDocumentVersion approval and chain.
"""
import hashlib
import hmac
import json
import re

from django.core.exceptions import ValidationError


SCHEMA = 'party-document-details-v1'
PARTIES = ('buyer', 'seller')
FIELDS = ('name', 'country', 'address', 'tax_id', 'contact', 'phone', 'email',
          'billing_address', 'shipping_address', 'recipient')
LIMITS = {'name': 200, 'country': 100, 'tax_id': 200, 'contact': 200,
          'phone': 100, 'email': 254, 'recipient': 200}


def unknown_details():
    """Represent a historical document with no recorded details."""
    return {'schema': SCHEMA, **{side: {field: None for field in FIELDS} for side in PARTIES}}


def validate_details(value):
    """Validate a full, explicitly supplied schema; preserve NULL versus empty."""
    if not isinstance(value, dict) or set(value) != {'schema', *PARTIES} or value['schema'] != SCHEMA:
        raise ValidationError('主体资料格式或版本无效。')
    result = {'schema': SCHEMA}
    for side in PARTIES:
        fields = value[side]
        if not isinstance(fields, dict) or set(fields) != set(FIELDS):
            raise ValidationError('主体资料字段不完整。')
        result[side] = {}
        for field, item in fields.items():
            if item is not None and (not isinstance(item, str) or len(item) > LIMITS.get(field, 10000)):
                raise ValidationError('主体资料字段类型或长度无效。')
            result[side][field] = item
    return result


def validate_initial_details(*, persisted_status, details):
    """Validate initial entry against the status read under a document lock."""
    if persisted_status != 'draft':
        raise ValidationError('仅草稿单据可以录入初始主体资料。')
    return validate_details(details)


def document_party_fingerprint(snapshot, *, version, target_type=None, target_id=None, details=None):
    """Build a versioned digest, without changing the historical snapshot hash.

    V2 binds the exact legacy snapshot, document identity and explicit details.
    This primitive neither persists facts nor establishes authorization.
    """
    if not isinstance(snapshot, dict) or type(version) is not int or version not in (1, 2):
        raise ValidationError('主体快照或指纹版本无效。')
    if version == 1:
        if details is not None or target_type is not None or target_id is not None:
            raise ValidationError('旧版指纹不能附加主体资料。')
        payload = snapshot
    else:
        if target_type not in ('order', 'purchase_order') or type(target_id) is not int or target_id < 1:
            raise ValidationError('单据身份无效。')
        payload = {'domain': 'crm.party-document-fingerprint.v2', 'target_type': target_type,
                   'target_id': target_id, 'snapshot': snapshot, 'details': validate_details(details)}
    try:
        encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')
    except (TypeError, ValueError):
        raise ValidationError('主体快照不能计算指纹。')
    return {'version': version, 'sha256': hashlib.sha256(encoded).hexdigest()}


def verify_document_party_fingerprint(snapshot, descriptor, *, target_type=None, target_id=None, details=None):
    if (not isinstance(descriptor, dict) or set(descriptor) != {'version', 'sha256'}
            or not isinstance(descriptor['sha256'], str)
            or not re.fullmatch(r'[0-9a-f]{64}', descriptor['sha256'])):
        raise ValidationError('主体指纹描述无效。')
    expected = document_party_fingerprint(snapshot, version=descriptor['version'],
        target_type=target_type, target_id=target_id, details=details)
    if not hmac.compare_digest(expected['sha256'], descriptor['sha256']):
        raise ValidationError('单据或主体资料已变更。')
    return True


def effective_quote_details(quote):
    """Validate inherited details back to a root or independently approved boundary.

    Caller holds the quote lock in an atomic transaction; ancestors are locked
    in descendant-to-ancestor order, matching quotation approval validation.
    """
    from .models import Quote, PartyQuoteApplication
    from .party_document_details_models import PartyDocumentDetailsStorage
    from .party_version import TARGETS, _snapshot, verify_quote_details_application
    current = quote
    seen = set()
    expected = None
    first = True
    while current is not None:
        if current.pk in seen:
            raise ValidationError('报价修订链无效。')
        seen.add(current.pk)
        row = PartyDocumentDetailsStorage.objects.filter(quote_id=current.pk).first()
        details = validate_details(row.details) if row and row.details is not None else None
        if first:
            expected, first = details, False
        elif details != expected:
            raise ValidationError('报价修订主体资料与来源不一致。')
        if not current.parent_quote_id:
            return expected
        parent = Quote.objects.select_for_update().get(pk=current.parent_quote_id)
        if current.customer_id != parent.customer_id:
            raise ValidationError('报价修订主体身份不一致。')
        application = PartyQuoteApplication.objects.filter(result_quote_id=current.pk).select_related('approval__request').first()
        if application and 'party_details' in application.approval.request.base_snapshot:
            if verify_quote_details_application(parent, current) != expected:
                raise ValidationError('报价修订主体资料与批准内容不一致。')
            return expected
        if expected is not None and _snapshot(current, TARGETS['quote'][1]) != _snapshot(parent, TARGETS['quote'][1]):
            raise ValidationError('报价修订主体与来源不一致。')
        current = parent
    return expected


def inherit_quote_details(source, revision):
    """Copy only validated facts into a newly created draft revision."""
    from .party_document_details_models import PartyDocumentDetailsStorage
    if revision.status != 'draft' or revision.parent_quote_id != source.pk:
        raise ValidationError('报价资料只能继承至来源修订草稿。')
    details = effective_quote_details(source)
    if details is not None:
        PartyDocumentDetailsStorage.objects.create(quote=revision, details=details)


def read_document_details(*, request, target_type, target_id):
    """Authorized read of recorded facts; no master-data fallback or inference."""
    from django.db import transaction
    from .party_version import TARGETS, _authorize
    from .party_document_details_models import PartyDocumentDetailsStorage

    if target_type not in TARGETS:
        raise ValidationError('不支持的单据类型。')
    with transaction.atomic():
        actor = _draft_actor(request)
        target = TARGETS[target_type][0].objects.select_for_update().get(pk=target_id)
        _authorize(actor, target_type, target, write=False)
        if target_type == 'quote' and target.parent_quote_id:
            return effective_quote_details(target)
        row = PartyDocumentDetailsStorage.objects.filter(**{target_type: target}).first()
        if row is None or row.details is None:
            return None
        if target.status == 'draft':
            return validate_details(row.details)
        if target_type in ('order', 'purchase_order'):
            from .party_document_version import effective_snapshot
            return effective_snapshot(target).get('party_details')
        if target_type == 'quote':
            return validate_details(row.details)
        # Enabling storage requires approval-bound effective-version validation.
        raise ValidationError('主体资料尚未接入有效版本验证。')


def save_draft_details(*, request, target_type, target_id, details):
    """Save explicit details while holding the same lock as formalization."""
    from django.db import transaction
    from .party_version import TARGETS, _authorize
    from .party_document_details_models import PartyDocumentDetailsStorage

    if target_type not in TARGETS:
        raise ValidationError('不支持的单据类型。')
    details = validate_details(details)
    with transaction.atomic():
        actor = _draft_actor(request)
        target = TARGETS[target_type][0].objects.select_for_update().get(pk=target_id)
        _authorize(actor, target_type, target, write=True)
        if getattr(target, 'historical_only', False):
            raise ValidationError('历史单据不能录入主体资料。')
        if target_type == 'quote' and target.parent_quote_id:
            raise ValidationError('报价修订主体资料须通过独立审批更正。')
        validate_initial_details(persisted_status=target.status, details=details)
        PartyDocumentDetailsStorage.objects.update_or_create(**{target_type: target}, defaults={'details': details})
        return details


def _draft_actor(request):
    from .permissions import development_superadmin_enabled
    from .party_version import _actor
    if development_superadmin_enabled():
        return getattr(request, 'user', None)
    return _actor(request)
