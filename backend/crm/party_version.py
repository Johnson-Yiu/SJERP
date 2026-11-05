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


def _snapshot(target, fields):
    return {key: getattr(target, field) for key, field in fields.items()}


def _validate_saved_basis(obj, target_type, target, fields):
    # Validate precisely the schema saved with this request; never fill missing
    # historical fields or alter either stored fingerprint.
    if not isinstance(obj.base_snapshot, dict):
        raise ValidationError('基准快照字段无效。')
    allowed_fields = [set(fields)]
    if target_type == 'quote':
        allowed_fields.append(set(fields) - {'tax_id'})
    if set(obj.base_snapshot) not in allowed_fields:
        raise ValidationError('基准快照字段无效。')
    if target_type == 'quote' and 'tax_id' not in obj.base_snapshot and target.buyer_tax_id is not None:
        raise ValidationError('基准快照已变更，请重新申请。')
    basis_fields = {key: fields[key] for key in obj.base_snapshot}
    if _digest(obj.base_snapshot) != obj.base_fingerprint or _digest(_snapshot(target, basis_fields)) != obj.base_fingerprint:
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
    return content


def _target_type(obj):
    targets = [name for name in TARGETS if getattr(obj, name + '_id') is not None]
    if len(targets) != 1:
        raise ValidationError('申请必须关联且仅关联一个单据。')
    return targets[0]


@transaction.atomic
def propose(*, request, target_type, target_id, expected_base_fingerprint, proposed_snapshot, change_type, reason, evidence, source_trust):
    actor = _actor(request)
    if target_type not in TARGETS:
        raise ValidationError('不支持的单据类型。')
    model, fields = TARGETS[target_type]
    target = model.objects.select_for_update().get(pk=target_id)
    _authorize(actor, target_type, target, write=True)
    if target_type == 'quote' and target.status not in {'sent', 'accepted'}:
        raise ValidationError('只有已发送或已接受的正式报价可以申请主体更正。')
    base = _snapshot(target, fields)
    base_hash = _digest(base)
    if not isinstance(expected_base_fingerprint, str) or expected_base_fingerprint != base_hash:
        raise ValidationError('基准快照已变更，请重新核对。')
    if not isinstance(proposed_snapshot, dict) or set(proposed_snapshot) != set(fields):
        raise ValidationError('必须提供完整的主体快照字段。')
    if any(not isinstance(value, str) and not (key in {'tax_id', 'country'} and value is None) for key, value in proposed_snapshot.items()):
        raise ValidationError('主体快照字段必须为字符串。')
    _text(proposed_snapshot['name'], 'name')
    if proposed_snapshot == base:
        raise ValidationError('主体快照没有变化。')
    if change_type not in {'correction', 'replacement'}:
        raise ValidationError('必须明确更正或法律主体替换。')
    if source_trust not in {'unknown', 'unverified'}:
        raise ValidationError('来源可信度必须为未知或未核验。')
    obj = PartyVersionRequest(**{target_type: target}, initiator=actor, base_snapshot=base,
        proposed_snapshot=proposed_snapshot, base_fingerprint=base_hash, change_type=change_type,
        reason=_text(reason, 'reason'), evidence=_text(evidence, 'evidence'), source_trust=source_trust)
    if target_type == 'quote':
        obj.quote_customer_id = target.customer_id
        obj.source_document_fingerprint = _quote_fingerprint(target, list(target.items.select_for_update().order_by('id')))
    obj.content_fingerprint = _digest(_content(obj))
    try:
        with transaction.atomic():
            obj.save(force_insert=True)
    except IntegrityError as exc:
        raise ValidationError('该单据的基准快照已有主体申请。') from exc
    return obj


def baseline(*, request, target_type, target_id):
    actor = _actor(request)
    if target_type not in TARGETS:
        raise ValidationError('不支持的单据类型。')
    model, fields = TARGETS[target_type]
    target = model.objects.get(pk=target_id)
    _authorize(actor, target_type, target, write=False)
    snapshot = _snapshot(target, fields)
    return {'snapshot': snapshot, 'fingerprint': _digest(snapshot)}


@transaction.atomic
def approve(*, request, request_id, expected_content_fingerprint, note):
    actor = _actor(request)
    obj = PartyVersionRequest.objects.select_for_update().get(pk=request_id)
    target_type = _target_type(obj)
    model, fields = TARGETS[target_type]
    target = model.objects.select_for_update().get(pk=getattr(obj, target_type + '_id'))
    _authorize(actor, target_type, target, write=True)
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
    obj = PartyVersionRequest.objects.select_for_update().get(pk=request_id)
    target_type = _target_type(obj)
    model, fields = TARGETS[target_type]
    target = model.objects.select_for_update().get(pk=getattr(obj, target_type + '_id'))
    _authorize(actor, target_type, target, write=False)
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


def _validate_source_document(obj, target_type, target):
    if target_type != 'quote' or obj.source_document_fingerprint is None:
        return  # Older requests remain verifiable but cannot be applied.
    items = list(target.items.select_for_update().order_by('id'))
    if _quote_fingerprint(target, items) != obj.source_document_fingerprint:
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


@transaction.atomic
def apply_approved_quote_change(*, request, request_id):
    """Apply one approved same-customer correction as a draft quote revision.

    Returns the immutable PartyQuoteApplication; repeated calls by an authorized
    user return the same association. The authenticated application actor is
    preserved on the original application and never overwritten on replay.
    """
    actor = _actor(request)
    obj = PartyVersionRequest.objects.select_for_update().get(pk=request_id)
    if _target_type(obj) != 'quote':
        raise ValidationError('只允许应用报价主体更正。')
    source = Quote.objects.select_for_update().get(pk=obj.quote_id)
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
        if (existing.source_quote_id != source.pk or existing.approved_fingerprint != approval.approved_fingerprint
                or existing.approval_attestation_fingerprint != attestation
                or existing.application_fingerprint != _application_fingerprint(existing)):
            raise ValidationError('主体更正生效记录不一致。')
        _validate_saved_basis(obj, 'quote', source, TARGETS['quote'][1])
        _validate_source_document(obj, 'quote', source)
        source_items = list(source.items.select_for_update().order_by('id'))
        if _quote_fingerprint(source, source_items) != existing.source_fingerprint:
            raise ValidationError('来源报价或明细已变更，请重新核实。')
        result = Quote.objects.select_for_update().get(pk=existing.result_quote_id)
        result_items = list(result.items.select_for_update().order_by('id'))
        if _quote_fingerprint(result, result_items) != existing.revision_fingerprint:
            raise ValidationError('生成修订或明细已变更，请重新核实。')
        return existing
    if source.status not in {'sent', 'accepted'}:
        raise ValidationError('只有已发送或已接受的正式报价可以生成主体更正修订。')
    fields = TARGETS['quote'][1]
    _validate_saved_basis(obj, 'quote', source, fields)
    _validate_source_document(obj, 'quote', source)
    if not isinstance(obj.proposed_snapshot, dict) or set(obj.proposed_snapshot) != set(obj.base_snapshot):
        raise ValidationError('建议主体快照字段无效。')
    if any(not isinstance(value, str) and not (key in {'tax_id', 'country'} and value is None)
           for key, value in obj.proposed_snapshot.items()):
        raise ValidationError('建议主体快照内容无效。')
    for key in ('country', 'tax_id'):
        if key in obj.base_snapshot and obj.base_snapshot[key] is None and obj.proposed_snapshot[key] is not None:
            raise ValidationError('历史未知主体字段不能自动升级。')
    _text(obj.proposed_snapshot.get('name'), 'name')
    if obj.proposed_snapshot == obj.base_snapshot:
        raise ValidationError('主体快照没有变化。')
    items = list(source.items.select_for_update().order_by('id'))
    source_fingerprint = _quote_fingerprint(source, items)
    from .quote_numbers import allocate_revision_quote_no
    quote_no, revision_no = allocate_revision_quote_no(source)
    excluded = {'id', 'quote_no', 'root_quote', 'parent_quote', 'revision_no', 'revision_summary', 'status', 'created_at', 'updated_at'}
    values = {field.attname: deepcopy(getattr(source, field.attname))
              for field in Quote._meta.concrete_fields if field.name not in excluded}
    for key, value in obj.proposed_snapshot.items():
        field_name = fields[key]
        if value != obj.base_snapshot[key]:
            Quote._meta.get_field(field_name).clean(value, source)
        values[field_name] = value
    revision = Quote.objects.create(quote_no=quote_no, revision_no=revision_no,
        root_quote_id=source.root_quote_id or source.pk, parent_quote_id=source.pk,
        revision_summary='已批准主体更正', status='draft', **values)
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
        source_fingerprint=source_fingerprint, revision_fingerprint=_quote_fingerprint(revision, revision_items))
    application.application_fingerprint = _application_fingerprint(application)
    application.save(force_insert=True)
    return application
