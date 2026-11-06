"""Persist party proposals and approvals and apply approved quote corrections.

Callers must supply a Django HttpRequest with a verified login session. This
module checks target access and preserves the existing quote revision tree.
"""
import hashlib
import json

from copy import deepcopy

from django.contrib.auth import get_user
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models.fields.files import FieldFile
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction

from .models import (Order, PartyQuoteApplication, PartyVersionApproval, PartyVersionRequest,
                     PurchaseOrder, Quote, QuoteItem)
from .party_version_models import PartyVersionTerminalEvent
from .permissions import user_can
from .sales_scope import customer_in_scope


TARGETS = {
    'quote': (Quote, {'name': 'buyer_company_name', 'country': 'buyer_country_snapshot', 'address': 'buyer_address', 'contact': 'recipient_name', 'phone': 'buyer_phone', 'email': 'buyer_email', 'tax_id': 'buyer_tax_id'}),
    'order': (Order, {'name': 'customer_name_snapshot', 'country': 'customer_country_snapshot', 'address': 'customer_address_snapshot', 'contact': 'customer_contact_name_snapshot', 'phone': 'customer_phone_snapshot', 'email': 'customer_email_snapshot'}),
    'purchase_order': (PurchaseOrder, {'name': 'supplier_name_snapshot', 'address': 'supplier_address_snapshot', 'contact': 'supplier_contact_name_snapshot', 'phone': 'supplier_phone_snapshot', 'email': 'supplier_email_snapshot'}),
}


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()


def _actor(request):
    try:
        user = get_user(request)
    except (AttributeError, KeyError, TypeError):
        raise ValidationError('必须使用真实认证会话。')
    if not user.is_authenticated or not user.is_active or user.pk is None:
        raise ValidationError('必须使用真实认证会话。')
    return user


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError({field: '此项不能为空。'})
    return value.strip()


def _authorize(user, target_type, target, *, write):
    module = {'quote': 'quotes', 'order': 'orders', 'purchase_order': 'purchases'}[target_type]
    related_module = 'suppliers' if target_type == 'purchase_order' else 'customers'
    if not user_can(user, module, 'view') or not user_can(user, related_module, 'view'):
        raise PermissionDenied('无权访问该单据的主体信息。')
    if write and not user_can(user, module, 'update'):
        raise PermissionDenied('无权更正该单据的主体信息。')
    if target_type != 'purchase_order' and not customer_in_scope(target.customer_id, user):
        raise PermissionDenied('无权访问该单据的主体信息。')


def _locked_request(request_id):
    """Lock target first, then request; the initial identifier read takes no lock."""
    ref = PartyVersionRequest.objects.values('quote_id', 'order_id', 'purchase_order_id').get(pk=request_id)
    kinds = [name for name in TARGETS if ref[name + '_id'] is not None]
    if len(kinds) != 1:
        raise ValidationError('申请必须关联且仅关联一个单据。')
    kind = kinds[0]
    model, fields = TARGETS[kind]
    target = model.objects.select_for_update().get(pk=ref[kind + '_id'])
    obj = PartyVersionRequest.objects.select_for_update().get(pk=request_id)
    if _target_type(obj) != kind or getattr(obj, kind + '_id') != target.pk:
        raise ValidationError('申请关联已变更。')
    return obj, kind, target, fields


def _terminal(obj):
    return PartyVersionTerminalEvent.objects.filter(request_id=obj.pk).first()


def _require_active(obj):
    if not obj.is_active or _terminal(obj) is not None:
        raise ValidationError('申请已结束，不能继续此操作。')


def _snapshot(target, fields):
    return {key: getattr(target, field) for key, field in fields.items()}


def _effective_basis(kind, target, fields):
    if kind in {'order', 'purchase_order'}:
        from .party_document_version import effective_snapshot
        return effective_snapshot(target)
    result = _snapshot(target, fields)
    from .party_document_details_models import PartyDocumentDetailsStorage
    from django.db import connections
    alias = target._state.db or 'default'
    if PartyDocumentDetailsStorage._meta.db_table not in connections[alias].introspection.table_names():
        return result
    row = PartyDocumentDetailsStorage.objects.filter(quote_id=target.pk).first()
    if row and row.details is not None:
        from .party_document_details import validate_details
        result['party_details'] = validate_details(row.details)
    return result


def _validate_saved_basis(obj, target_type, target, fields):
    # Validate precisely the schema saved with this request; never fill missing
    # historical fields or alter either stored fingerprint.
    if not isinstance(obj.base_snapshot, dict):
        raise ValidationError('基准快照字段无效。')
    allowed_fields = [set(fields)]
    if target_type in {'order', 'purchase_order'}:
        allowed_fields.append(set(fields) | {'party_details'})
    if target_type == 'quote':
        allowed_fields.append(set(fields) - {'tax_id'})
        allowed_fields.append(set(fields) | {'party_details'})
    if set(obj.base_snapshot) not in allowed_fields:
        raise ValidationError('基准快照字段无效。')
    if target_type == 'quote' and 'tax_id' not in obj.base_snapshot and target.buyer_tax_id is not None:
        raise ValidationError('基准快照已变更，请重新申请。')
    basis_fields = {key: fields[key] for key in obj.base_snapshot if key in fields}
    if target_type in {'order', 'purchase_order'}:
        from .party_document_version import identity_fingerprint
        if obj.source_document_fingerprint is not None and obj.source_document_fingerprint != identity_fingerprint(target):
            raise ValidationError('单据主体身份已变更，请重新申请。')
        # Pre-versioning requests retain their original validation semantics.
        current = (_snapshot(target, basis_fields) if obj.source_document_fingerprint is None
                   else _effective_basis(target_type, target, basis_fields))
        if 'party_details' not in obj.base_snapshot:
            current = {key: current[key] for key in basis_fields}
    else:
        current = (_effective_basis('quote', target, basis_fields)
                   if 'party_details' in obj.base_snapshot else _snapshot(target, basis_fields))
    if _digest(obj.base_snapshot) != obj.base_fingerprint or _digest(current) != obj.base_fingerprint:
        raise ValidationError('基准快照已变更，请重新申请。')


def _content(obj):
    content = {'target_type': _target_type(obj), 'target_id': getattr(obj, _target_type(obj) + '_id'),
            'initiator_id': obj.initiator_id, 'base_snapshot': obj.base_snapshot,
            'proposed_snapshot': obj.proposed_snapshot, 'base_fingerprint': obj.base_fingerprint,
            'change_type': obj.change_type, 'reason': obj.reason, 'evidence': obj.evidence,
            'source_trust': obj.source_trust}
    # Pre-0112 applications remain byte-for-byte verifiable, but cannot be
    # applied without an originally signed customer identity.
    if obj.quote_customer_id is not None:
        content['quote_customer_id'] = obj.quote_customer_id
    if obj.source_document_fingerprint is not None:
        content['source_document_fingerprint'] = obj.source_document_fingerprint
    descriptor = getattr(obj, '_replacement_descriptor', None)
    if descriptor is None and obj.pk and obj.change_type == 'replacement':
        from .party_replacement_models import PartyReplacementTarget
        from django.db import connections
        alias = obj._state.db or 'default'
        connection = connections[alias]
        # Historical migration tests can exercise the original fingerprint
        # before 0115 creates this table. Such requests remain verifiable but
        # cannot be applied by the replacement service without a binding.
        binding = (PartyReplacementTarget.objects.using(alias).filter(request_id=obj.pk).first()
                   if PartyReplacementTarget._meta.db_table in connection.introspection.table_names() else None)
        if binding:
            descriptor = {'type': 'customer' if binding.customer_id else 'supplier',
                          'id': binding.customer_id or binding.supplier_id, 'name': binding.target_name}
    if descriptor is not None:
        content['replacement_target'] = descriptor
    return content


def _target_type(obj):
    targets = [name for name in TARGETS if getattr(obj, name + '_id') is not None]
    if len(targets) != 1:
        raise ValidationError('申请必须关联且仅关联一个单据。')
    return targets[0]


@transaction.atomic
def propose(*, request, target_type, target_id, expected_base_fingerprint, proposed_snapshot, change_type, reason, evidence, source_trust, replacement_target_id=None):
    actor = _actor(request)
    if target_type not in TARGETS:
        raise ValidationError('不支持的单据类型。')
    model, fields = TARGETS[target_type]
    target = model.objects.select_for_update().get(pk=target_id)
    _authorize(actor, target_type, target, write=True)
    if target_type == 'quote' and target.status not in {'sent', 'accepted'}:
        raise ValidationError('只有已发送或已接受的正式报价可以申请主体更正。')
    if PartyVersionRequest.objects.filter(**{target_type: target}, is_active=True).exists():
        raise ValidationError('该单据已有活跃的主体申请。')
    base = _effective_basis(target_type, target, fields)
    base_hash = _digest(base)
    if not isinstance(expected_base_fingerprint, str) or expected_base_fingerprint != base_hash:
        raise ValidationError('基准快照已变更，请重新核对。')
    if not isinstance(proposed_snapshot, dict) or set(proposed_snapshot) != set(base):
        raise ValidationError('必须提供完整的主体快照字段。')
    if any(not isinstance(value, str) and not (key in {'tax_id', 'country'} and value is None) for key, value in proposed_snapshot.items() if key != 'party_details'):
        raise ValidationError('主体快照字段必须为字符串。')
    if 'party_details' in proposed_snapshot:
        from .party_document_details import validate_details
        validate_details(proposed_snapshot['party_details'])
    _text(proposed_snapshot['name'], 'name')
    if proposed_snapshot == base:
        raise ValidationError('主体快照没有变化。')
    if change_type not in {'correction', 'replacement'}:
        raise ValidationError('必须明确更正或法律主体替换。')
    if source_trust not in {'unknown', 'unverified'}:
        raise ValidationError('来源可信度必须为未知或未核验。')
    replacement_target = None
    if change_type == 'replacement':
        from .party_replacement import lock_target
        replacement_target = lock_target(actor, target_type, target, replacement_target_id)
        if proposed_snapshot['name'] != replacement_target.name:
            raise ValidationError('拟议名称必须与替换目标一致。')
    elif replacement_target_id is not None:
        raise ValidationError('同主体更正不能指定替换目标。')
    obj = PartyVersionRequest(**{target_type: target}, initiator=actor, base_snapshot=base,
        proposed_snapshot=proposed_snapshot, base_fingerprint=base_hash, change_type=change_type,
        reason=_text(reason, 'reason'), evidence=_text(evidence, 'evidence'), source_trust=source_trust)
    if target_type == 'quote':
        obj.quote_customer_id = target.customer_id
        obj.source_document_fingerprint = quote_request_fingerprint(target, list(target.items.select_for_update().order_by('id')), base)
    else:
        from .party_document_version import identity_fingerprint
        obj.source_document_fingerprint = identity_fingerprint(target)
    if replacement_target is not None:
        obj._replacement_descriptor = {'type': 'supplier' if target_type == 'purchase_order' else 'customer',
                                       'id': replacement_target.pk, 'name': replacement_target.name}
    obj.content_fingerprint = _digest(_content(obj))
    try:
        with transaction.atomic():
            obj.save(force_insert=True)
            if replacement_target is not None:
                from .party_replacement_models import PartyReplacementTarget
                PartyReplacementTarget.objects.create(request=obj, target_name=replacement_target.name,
                    **({'supplier': replacement_target} if target_type == 'purchase_order' else {'customer': replacement_target}))
    except IntegrityError as exc:
        raise ValidationError('该单据已有活跃的主体申请。') from exc
    return obj


@transaction.atomic
def baseline(*, request, target_type, target_id):
    actor = _actor(request)
    if target_type not in TARGETS:
        raise ValidationError('不支持的单据类型。')
    model, fields = TARGETS[target_type]
    target = model.objects.select_for_update().get(pk=target_id)
    _authorize(actor, target_type, target, write=False)
    snapshot = _effective_basis(target_type, target, fields)
    return {'snapshot': snapshot, 'fingerprint': _digest(snapshot)}


@transaction.atomic
def approve(*, request, request_id, expected_content_fingerprint, note):
    actor = _actor(request)
    obj, target_type, target, fields = _locked_request(request_id)
    _authorize(actor, target_type, target, write=True)
    _require_active(obj)
    if actor.pk == obj.initiator_id:
        raise ValidationError('发起人不能审批自己的申请。')
    if obj.content_fingerprint != _digest(_content(obj)) or expected_content_fingerprint != obj.content_fingerprint:
        raise ValidationError('申请内容指纹不一致。')
    _validate_saved_basis(obj, target_type, target, fields)
    _validate_source_document(obj, target_type, target)
    if PartyVersionApproval.objects.filter(request=obj).exists():
        raise ValidationError('申请已经批准。')
    return PartyVersionApproval.objects.create(request=obj, approver=actor, approved_fingerprint=obj.content_fingerprint, note=_text(note, 'note'))


@transaction.atomic
def verified_approval(*, request, request_id):
    """Return a point-in-time verified approval; never apply it to a document.

    Consumers must use this entry point rather than reading approval models
    directly. The result does not freeze the target after this transaction.
    """
    actor = _actor(request)
    obj, target_type, target, fields = _locked_request(request_id)
    _authorize(actor, target_type, target, write=False)
    if _terminal(obj) is not None:
        raise ValidationError('申请已结束，不能验证为有效批准。')
    decision = PartyVersionApproval.objects.select_for_update().filter(request_id=obj.pk).first()
    if decision is None:
        raise ValidationError('申请尚未批准。')
    content_fingerprint = _digest(_content(obj))
    if obj.content_fingerprint != content_fingerprint or decision.approved_fingerprint != content_fingerprint:
        raise ValidationError('批准内容指纹不一致。')
    _validate_saved_basis(obj, target_type, target, fields)
    _validate_source_document(obj, target_type, target)
    decision.request = obj
    return decision



def _quote_fingerprint(quote, items):
    """Fingerprint persisted document facts, preserving blank and unknown values."""
    def fields_of(instance, excluded):
        values = {}
        for field in instance._meta.concrete_fields:
            if field.name in excluded:
                continue
            value = getattr(instance, field.attname)
            values[field.attname] = value.name if isinstance(value, FieldFile) else value
        return values
    data = {
        # Quote status may legitimately change from sent to accepted; it is
        # not a commercial fact approved by this subject-correction request.
        'quote': fields_of(quote, {'created_at', 'updated_at', 'status'}),
        'items': [fields_of(item, set()) for item in items],
    }
    raw = json.dumps(data, cls=DjangoJSONEncoder, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def quote_request_fingerprint(quote, items, signed_snapshot):
    """Use the version committed by the signed snapshot; never downgrade V2."""
    if 'party_details' not in signed_snapshot:
        return _quote_fingerprint(quote, items)
    from .party_document_details_models import PartyDocumentDetailsStorage
    from .quote_party_fingerprint import quote_party_fingerprint
    row = PartyDocumentDetailsStorage.objects.filter(quote_id=quote.pk).first()
    if row is None or row.details is None:
        raise ValidationError('报价主体资料缺失。')
    return quote_party_fingerprint(quote, items, version=2, details=row.details)['sha256']


def _validate_source_document(obj, target_type, target):
    if obj.source_document_fingerprint is None:
        return  # Older requests remain verifiable but cannot be applied.
    if target_type in {'order', 'purchase_order'}:
        from .party_document_version import identity_fingerprint
        if obj.source_document_fingerprint != identity_fingerprint(target):
            raise ValidationError('单据主体身份已变更，请重新申请。')
        return
    if ('party_details' not in obj.base_snapshot
            and 'party_details' in _effective_basis('quote', target, TARGETS['quote'][1])):
        raise ValidationError('旧申请未覆盖报价主体资料，请重新申请。')
    items = list(target.items.select_for_update().order_by('id'))
    if quote_request_fingerprint(target, items, obj.base_snapshot) != obj.source_document_fingerprint:
        raise ValidationError('来源报价或明细已变更，请重新申请。')


def _approval_attestation_fingerprint(approval):
    return _digest({'approval_id': approval.pk, 'request_id': approval.request_id,
                    'approver_id': approval.approver_id, 'approved_fingerprint': approval.approved_fingerprint,
                    'note': approval.note, 'created_at': approval.created_at.isoformat()})


def _application_fingerprint(application):
    return _digest({
        'approval_id': application.approval_id, 'source_quote_id': application.source_quote_id,
        'result_quote_id': application.result_quote_id, 'applied_by_id': application.applied_by_id,
        'approved_fingerprint': application.approved_fingerprint,
        'approval_attestation_fingerprint': application.approval_attestation_fingerprint,
        'source_fingerprint': application.source_fingerprint,
        'revision_fingerprint': application.revision_fingerprint,
    })


def verify_quote_details_application(source, revision):
    """Validate an approved V2 boundary; caller locks revision then source in one transaction."""
    application = PartyQuoteApplication.objects.select_for_update().filter(result_quote_id=revision.pk).first()
    if application is None:
        raise ValidationError('报价资料缺少生效审批。')
    approval = PartyVersionApproval.objects.select_for_update().get(pk=application.approval_id)
    obj = PartyVersionRequest.objects.select_for_update().get(pk=approval.request_id)
    if (application.source_quote_id != source.pk or revision.parent_quote_id != source.pk
            or obj.quote_id != source.pk or obj.order_id is not None or obj.purchase_order_id is not None
            or obj.change_type != 'correction' or obj.quote_customer_id != source.customer_id
            or revision.customer_id != source.customer_id or approval.approver_id == obj.initiator_id
            or not obj.reason.strip() or not obj.evidence.strip() or not approval.note.strip()
            or _terminal(obj) is not None or 'party_details' not in obj.base_snapshot
            or obj.content_fingerprint != _digest(_content(obj))
            or approval.approved_fingerprint != obj.content_fingerprint
            or application.approved_fingerprint != approval.approved_fingerprint
            or application.approval_attestation_fingerprint != _approval_attestation_fingerprint(approval)
            or application.application_fingerprint != _application_fingerprint(application)):
        raise ValidationError('报价主体资料审批证据不一致。')
    _validate_saved_basis(obj, 'quote', source, TARGETS['quote'][1])
    _validate_source_document(obj, 'quote', source)
    if application.source_fingerprint != obj.source_document_fingerprint:
        raise ValidationError('报价来源指纹不一致。')
    items = list(revision.items.select_for_update().order_by('id'))
    if application.revision_fingerprint != quote_request_fingerprint(revision, items, obj.proposed_snapshot):
        raise ValidationError('报价修订或主体资料已变更。')
    expected = obj.proposed_snapshot
    current = _effective_basis('quote', revision, TARGETS['quote'][1])
    if current != expected:
        raise ValidationError('报价修订主体资料与批准内容不一致。')
    return current['party_details']


class _RetryApplicationLockOrder(Exception):
    pass


def apply_approved_quote_change(*, request, request_id):
    for _ in range(3):
        try:
            return _apply_approved_quote_change(request=request, request_id=request_id)
        except _RetryApplicationLockOrder:
            continue
    raise ValidationError('申请正在并发处理，请重试。')


@transaction.atomic
def _apply_approved_quote_change(*, request, request_id):
    """Apply one approved same-customer correction as a draft quote revision.

    Returns the immutable PartyQuoteApplication; repeated calls by an authorized
    user return the same association. The authenticated application actor is
    preserved on the original application and never overwritten on replay.
    """
    actor = _actor(request)
    # Guard/formalization locks a result quote before its parent. An unlocked
    # lookup chooses that order; if creation races us, restart without locks.
    hinted_result_id = PartyQuoteApplication.objects.filter(approval__request_id=request_id).values_list('result_quote_id', flat=True).first()
    if hinted_result_id is not None:
        Quote.objects.select_for_update().get(pk=hinted_result_id)
    obj, target_type, source, fields = _locked_request(request_id)
    if target_type != 'quote':
        raise ValidationError('只允许应用报价主体更正。')
    _authorize(actor, 'quote', source, write=True)
    if not user_can(actor, 'quotes', 'create'):
        raise PermissionDenied('无权创建报价修订。')
    approval = PartyVersionApproval.objects.select_for_update().filter(request_id=obj.pk).first()
    if approval is None:
        raise ValidationError('申请尚未批准。')
    if obj.change_type != 'correction':
        raise ValidationError('法律主体替换不能通过此流程应用。')
    if approval.approver_id == obj.initiator_id:
        raise ValidationError('发起人不能审批自己的申请。')
    if not obj.reason.strip() or not obj.evidence.strip() or not approval.note.strip():
        raise ValidationError('申请原因、依据和审批记录不能为空。')
    if obj.content_fingerprint != _digest(_content(obj)) or approval.approved_fingerprint != obj.content_fingerprint:
        raise ValidationError('批准内容指纹不一致。')
    if obj.quote_customer_id is None or obj.quote_customer_id != source.customer_id:
        raise ValidationError('申请未绑定当前客户身份，不能应用。')
    if not obj.source_document_fingerprint:
        raise ValidationError('旧申请缺少来源报价指纹，不能应用。')
    attestation = _approval_attestation_fingerprint(approval)
    existing = PartyQuoteApplication.objects.select_for_update().filter(approval_id=approval.pk).first()
    if existing is not None:
        if hinted_result_id != existing.result_quote_id:
            raise _RetryApplicationLockOrder()
        if (existing.source_quote_id != source.pk or existing.approved_fingerprint != approval.approved_fingerprint
                or existing.approval_attestation_fingerprint != attestation
                or existing.application_fingerprint != _application_fingerprint(existing)):
            raise ValidationError('主体更正生效记录不一致。')
        _validate_saved_basis(obj, 'quote', source, TARGETS['quote'][1])
        _validate_source_document(obj, 'quote', source)
        source_items = list(source.items.select_for_update().order_by('id'))
        if quote_request_fingerprint(source, source_items, obj.base_snapshot) != existing.source_fingerprint:
            raise ValidationError('来源报价或明细已变更，请重新核实。')
        result = Quote.objects.select_for_update().get(pk=existing.result_quote_id)
        result_items = list(result.items.select_for_update().order_by('id'))
        if quote_request_fingerprint(result, result_items, obj.proposed_snapshot) != existing.revision_fingerprint:
            raise ValidationError('生成修订或明细已变更，请重新核实。')
        return existing
    _require_active(obj)
    if source.status not in {'sent', 'accepted'}:
        raise ValidationError('只有已发送或已接受的正式报价可以生成主体更正修订。')
    fields = TARGETS['quote'][1]
    _validate_saved_basis(obj, 'quote', source, fields)
    _validate_source_document(obj, 'quote', source)
    if not isinstance(obj.proposed_snapshot, dict) or set(obj.proposed_snapshot) != set(obj.base_snapshot):
        raise ValidationError('建议主体快照字段无效。')
    if any(not isinstance(value, str) and not (key in {'tax_id', 'country'} and value is None)
           for key, value in obj.proposed_snapshot.items() if key != 'party_details'):
        raise ValidationError('建议主体快照内容无效。')
    for key in ('country', 'tax_id'):
        if key in obj.base_snapshot and obj.base_snapshot[key] is None and obj.proposed_snapshot[key] is not None:
            raise ValidationError('历史未知主体字段不能自动升级。')
    if 'party_details' in obj.proposed_snapshot:
        from .party_document_details import validate_details
        details = validate_details(obj.proposed_snapshot['party_details'])
        for side in ('buyer', 'seller'):
            for key, old in obj.base_snapshot['party_details'][side].items():
                if old is None and details[side][key] is not None:
                    raise ValidationError('未知历史主体字段不能自动补全。')
    _text(obj.proposed_snapshot.get('name'), 'name')
    if obj.proposed_snapshot == obj.base_snapshot:
        raise ValidationError('主体快照没有变化。')
    items = list(source.items.select_for_update().order_by('id'))
    source_fingerprint = quote_request_fingerprint(source, items, obj.base_snapshot)
    from .quote_numbers import allocate_revision_quote_no
    quote_no, revision_no = allocate_revision_quote_no(source)
    excluded = {'id', 'quote_no', 'root_quote', 'parent_quote', 'revision_no', 'revision_summary', 'status', 'created_at', 'updated_at'}
    values = {field.attname: deepcopy(getattr(source, field.attname))
              for field in Quote._meta.concrete_fields if field.name not in excluded}
    for key, value in obj.proposed_snapshot.items():
        if key == 'party_details':
            continue
        field_name = fields[key]
        if value != obj.base_snapshot[key]:
            Quote._meta.get_field(field_name).clean(value, source)
        values[field_name] = value
    revision = Quote.objects.create(quote_no=quote_no, revision_no=revision_no,
        root_quote_id=source.root_quote_id or source.pk, parent_quote_id=source.pk,
        revision_summary='已批准主体更正', status='draft', **values)
    if 'party_details' in obj.proposed_snapshot:
        from .party_document_details_models import PartyDocumentDetailsStorage
        PartyDocumentDetailsStorage.objects.create(quote=revision, details=deepcopy(obj.proposed_snapshot['party_details']))
    cloned = []
    for item in items:
        values = {}
        for field in QuoteItem._meta.concrete_fields:
            if field.name in {'id', 'quote'}:
                continue
            value = getattr(item, field.attname)
            values[field.attname] = value.name if isinstance(value, FieldFile) else deepcopy(value)
        cloned.append(QuoteItem(quote=revision, **values))
    QuoteItem.objects.bulk_create(cloned)
    revision_items = list(revision.items.order_by('id'))
    application = PartyQuoteApplication(approval=approval, source_quote=source, result_quote=revision,
        applied_by=actor, approved_fingerprint=approval.approved_fingerprint,
        approval_attestation_fingerprint=attestation,
        source_fingerprint=source_fingerprint, revision_fingerprint=quote_request_fingerprint(revision, revision_items, obj.proposed_snapshot))
    application.application_fingerprint = _application_fingerprint(application)
    application.save(force_insert=True)
    PartyVersionRequest._base_manager.filter(pk=obj.pk, is_active=True).update(is_active=False)
    return application


def _is_applied(approval, target_type):
    if approval is None:
        return False
    if approval.request.change_type == 'replacement':
        from django.db import connections
        from .party_replacement_models import PartyReplacementLink
        alias = approval._state.db or 'default'
        if PartyReplacementLink._meta.db_table in connections[alias].introspection.table_names():
            return PartyReplacementLink.objects.using(alias).filter(approval_id=approval.pk).exists()
        return False
    if target_type == 'quote':
        return PartyQuoteApplication.objects.filter(approval_id=approval.pk).exists()
    from .party_document_models import PartyDocumentVersion
    return PartyDocumentVersion.objects.filter(approval_id=approval.pk).exists()


@transaction.atomic
def get_request_lifecycle(*, request, request_id):
    actor = _actor(request)
    obj, kind, target, _fields = _locked_request(request_id)
    _authorize(actor, kind, target, write=False)
    event = _terminal(obj)
    approval = PartyVersionApproval.objects.filter(request_id=obj.pk).first()
    applied = _is_applied(approval, kind)
    status = event.kind if event else ('applied' if applied else ('approved' if approval else 'pending'))
    if event and (obj.is_active or event.request_fingerprint != obj.content_fingerprint or obj.content_fingerprint != _digest(_content(obj))):
        raise ValidationError('申请生命周期记录不一致。')
    if event is None and not obj.is_active and not applied:
        raise ValidationError('申请生命周期记录不一致。')
    replacement = None
    if applied and approval.request.change_type == 'replacement':
        from .party_replacement_models import PartyReplacementLink
        link = PartyReplacementLink.objects.get(approval_id=approval.pk)
        replacement = {'result_quote_id': link.result_quote_id, 'result_order_id': link.result_order_id,
                       'result_purchase_order_id': link.result_purchase_order_id}
    return {'status': status, 'replacement_result': replacement, 'terminal_event': None if event is None else {
        'id': event.pk, 'kind': event.kind, 'actor_id': event.actor_id,
        'note': event.note, 'created_at': event.created_at,
        'request_fingerprint': event.request_fingerprint,
    }}


def _end_request(*, request, request_id, note, kind):
    actor = _actor(request)
    obj, target_type, target, _fields = _locked_request(request_id)
    _authorize(actor, target_type, target, write=True)
    note = _text(note, 'note')
    previous = _terminal(obj)
    if obj.content_fingerprint != _digest(_content(obj)):
        raise ValidationError('申请内容指纹不一致。')
    if previous is not None:
        if obj.is_active or previous.request_fingerprint != obj.content_fingerprint:
            raise ValidationError('申请生命周期记录不一致。')
        if previous.kind == kind and previous.actor_id == actor.pk and previous.note == note:
            return previous
        raise ValidationError('申请已经结束。')
    approval = PartyVersionApproval.objects.select_for_update().filter(request_id=obj.pk).first()
    if _is_applied(approval, target_type):
        raise ValidationError('已应用的申请不能结束。')
    _require_active(obj)
    if obj.content_fingerprint != _digest(_content(obj)):
        raise ValidationError('申请内容指纹不一致。')
    if kind == 'withdrawn' and actor.pk != obj.initiator_id:
        raise PermissionDenied('只有发起人可以撤回申请。')
    if kind == 'rejected' and actor.pk == obj.initiator_id:
        raise ValidationError('发起人不能拒绝自己的申请。')
    if approval and kind in {'rejected', 'withdrawn'}:
        raise ValidationError('已批准申请不能拒绝或撤回。')
    event = PartyVersionTerminalEvent.objects.create(request=obj, kind=kind, actor=actor,
        note=note, request_fingerprint=obj.content_fingerprint)
    updated = PartyVersionRequest._base_manager.filter(pk=obj.pk, is_active=True).update(is_active=False)
    if updated != 1:
        raise ValidationError('申请状态已变化，请重试。')
    return event


@transaction.atomic
def reject(*, request, request_id, note):
    return _end_request(request=request, request_id=request_id, note=note, kind='rejected')


@transaction.atomic
def withdraw(*, request, request_id, note):
    return _end_request(request=request, request_id=request_id, note=note, kind='withdrawn')


@transaction.atomic
def invalidate(*, request, request_id, note):
    return _end_request(request=request, request_id=request_id, note=note, kind='invalidated')
