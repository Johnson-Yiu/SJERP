"""Version-only SO/PO same-party corrections; does not modify business facts.

Integration contract: shared baseline/propose/approve must call
``effective_snapshot(target)`` while holding the target row lock for writes.
"""
from django.apps import apps
from django.core.exceptions import ValidationError
from django.db import transaction
from .party_document_models import PartyDocumentVersion
from .party_version import (_actor, _authorize, _content, _digest, _locked_request,
                            _approval_attestation_fingerprint, _target_type, TARGETS)


def _kind(target):
    if target._meta.label_lower == 'crm.order': return 'order'
    if target._meta.label_lower == 'crm.purchaseorder': return 'purchase_order'
    raise ValidationError('仅支持销售或采购单据。')


def identity_fingerprint(target):
    kind = _kind(target)
    party_id = target.customer_id if kind == 'order' else target.supplier_id
    return _digest({'schema':'party-document-identity-v1', 'target_type':kind, 'target_id':target.pk, 'party_id':party_id})


def _version_hash(row):
    return _digest({'order_id':row.order_id, 'purchase_order_id':row.purchase_order_id,
        'previous_id':row.previous_id, 'approval_id':row.approval_id, 'applied_by_id':row.applied_by_id,
        'version_no':row.version_no, 'identity_fingerprint':row.identity_fingerprint, 'base_snapshot':row.base_snapshot, 'snapshot':row.snapshot,
        'base_fingerprint':row.base_fingerprint, 'snapshot_fingerprint':row.snapshot_fingerprint,
        'approved_fingerprint':row.approved_fingerprint,
        'approval_attestation_fingerprint':row.approval_attestation_fingerprint, 'source_trust':row.source_trust})


def _effective(target, *, lock=False):
    kind = _kind(target)
    fields = TARGETS[kind][1]
    current = {key:getattr(target, field) for key,field in fields.items()}
    original = dict(current)
    from .party_document_details_models import PartyDocumentDetailsStorage
    from .party_document_details import validate_details
    storage = PartyDocumentDetailsStorage.objects.filter(**{kind: target}).first()
    initial_details = validate_details(storage.details) if storage and storage.details is not None else None
    versions = PartyDocumentVersion.objects.filter(**{kind:target}).order_by('version_no', 'pk')
    if lock: versions = versions.select_for_update()
    previous = None
    for sequence, row in enumerate(versions, 1):
        if isinstance(row.base_snapshot, dict) and 'party_details' in row.base_snapshot and 'party_details' not in current:
            if initial_details is None:
                raise ValidationError('主体资料基准缺失，请核实。')
            current = {**current, 'party_details': initial_details}
        expected_fields = set(fields) | ({'party_details'} if 'party_details' in current else set())
        if (row.version_no != sequence or row.previous_id != (previous.pk if previous else None)
                or row.base_snapshot != current or row.base_fingerprint != _digest(current)
                or not isinstance(row.snapshot, dict) or set(row.snapshot) != expected_fields
                or row.snapshot_fingerprint != _digest(row.snapshot)
                or row.identity_fingerprint != identity_fingerprint(target)
                or row.version_fingerprint != _version_hash(row)):
            raise ValidationError('主体版本链不一致，请核实。')
        if 'party_details' in row.snapshot:
            validate_details(row.snapshot['party_details'])
        approval = row.approval
        req = approval.request
        if (req.source_document_fingerprint != row.identity_fingerprint
                or req.content_fingerprint != _digest(_content(req))
                or approval.approved_fingerprint != req.content_fingerprint
                or row.approved_fingerprint != approval.approved_fingerprint
                or row.approval_attestation_fingerprint != _approval_attestation_fingerprint(approval)
                or approval.approver_id == req.initiator_id
                or _target_type(req) != kind or getattr(req, kind + '_id') != target.pk or req.change_type != 'correction'
                or not req.reason.strip() or not req.evidence.strip() or not approval.note.strip()
                or apps.get_model('crm', 'PartyVersionTerminalEvent').objects.filter(request_id=req.pk).exists()
                or req.base_snapshot != row.base_snapshot or req.proposed_snapshot != row.snapshot
                or req.source_trust != row.source_trust):
            raise ValidationError('主体版本审批证据不一致，请核实。')
        current, previous = row.snapshot, row
    if initial_details is not None and 'party_details' not in current:
        current = {**current, 'party_details': initial_details}
    return original, dict(current), previous


def effective_snapshot(target):
    """Internal consumer: authorize target access before calling; never fill from master."""
    return _effective(target)[1]


@transaction.atomic
def apply(*, request, request_id):
    """Apply an independently approved correction as an append-only version."""
    actor = _actor(request)
    obj, kind, target, fields = _locked_request(request_id)
    if kind not in ('order', 'purchase_order'):
        raise ValidationError('仅支持销售或采购单据。')
    _authorize(actor, kind, target, write=True)
    if obj.change_type != 'correction':
        raise ValidationError('法律主体替换须新建关联单据，不能应用为主体更正。')
    if obj.source_document_fingerprint != identity_fingerprint(target):
        raise ValidationError('申请缺少有效的单据主体身份指纹，不能应用。')
    if target.status == 'draft':
        raise ValidationError('草稿单据不能应用正式主体更正。')
    Approval = apps.get_model('crm', 'PartyVersionApproval')
    approval = Approval.objects.select_for_update().filter(request_id=obj.pk).first()
    if approval is None:
        raise ValidationError('申请尚未批准。')
    if (approval.approver_id == obj.initiator_id or not obj.reason.strip() or not obj.evidence.strip()
            or not approval.note.strip() or obj.content_fingerprint != _digest(_content(obj))
            or approval.approved_fingerprint != obj.content_fingerprint):
        raise ValidationError('申请或独立审批记录不一致。')
    if apps.get_model('crm', 'PartyVersionTerminalEvent').objects.filter(request_id=obj.pk).exists():
        raise ValidationError('申请已结束，不能应用。')
    existing = PartyDocumentVersion.objects.select_for_update().filter(approval_id=approval.pk).first()
    original, base, previous = _effective(target, lock=True)
    attestation = _approval_attestation_fingerprint(approval)
    if existing:
        if (getattr(existing, kind + '_id') != target.pk or existing.version_no > previous.version_no
                or existing.approved_fingerprint != approval.approved_fingerprint
                or existing.approval_attestation_fingerprint != attestation):
            raise ValidationError('主体版本记录不一致。')
        return existing
    if not obj.is_active:
        raise ValidationError('申请已结束，不能应用。')
    if (obj.base_snapshot != base or obj.base_fingerprint != _digest(base)
            or not isinstance(obj.proposed_snapshot, dict) or set(obj.proposed_snapshot) != set(base)
            or any(not isinstance(obj.proposed_snapshot[k], str) for k in fields)
            or not obj.proposed_snapshot.get('name', '').strip() or obj.proposed_snapshot == base
            or obj.source_trust not in ('unknown', 'unverified')):
        raise ValidationError('申请基准或主体内容无效，请重新核实。')
    if 'party_details' in base:
        from .party_document_details import validate_details
        proposed_details = validate_details(obj.proposed_snapshot['party_details'])
        for side in ('buyer', 'seller'):
            for key, old in base['party_details'][side].items():
                if old is None and proposed_details[side][key] is not None:
                    raise ValidationError('未知历史主体字段不能自动补全。')
    # Empty historical values have no known source. Do not invent or promote them.
    if any(base[k] in ('', None) and obj.proposed_snapshot[k] not in ('', None) for k in fields):
        raise ValidationError('未知历史主体字段不能自动补全。')
    record = PartyDocumentVersion(**{kind:target}, previous=previous, approval=approval, applied_by=actor,
        version_no=previous.version_no + 1 if previous else 1, identity_fingerprint=identity_fingerprint(target), base_snapshot=base,
        snapshot=dict(obj.proposed_snapshot), base_fingerprint=obj.base_fingerprint,
        snapshot_fingerprint=_digest(obj.proposed_snapshot), approved_fingerprint=approval.approved_fingerprint,
        approval_attestation_fingerprint=attestation, source_trust=obj.source_trust)
    record.version_fingerprint = _version_hash(record)
    record.save(force_insert=True)
    if obj.__class__._base_manager.filter(pk=obj.pk, is_active=True).update(is_active=False) != 1:
        raise ValidationError('申请状态已变化，请重新核实。')
    return record
