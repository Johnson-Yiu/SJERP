"""Create a new document only from an independently approved target and payload."""
import hashlib
import json
from dataclasses import dataclass

from django.core.exceptions import PermissionDenied, ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import connections, transaction

from .models import Customer, Supplier, PartyVersionApproval
from .party_replacement_models import PartyReplacementLink, PartyReplacementTarget
from .permissions import user_can
from .sales_scope import customer_in_scope
from . import party_version as pv


def lock_target(actor, kind, source, target_id):
    if not isinstance(target_id, int) or isinstance(target_id, bool) or target_id <= 0:
        raise ValidationError('请选择替换目标。')
    supplier = kind == 'purchase_order'
    model = Supplier if supplier else Customer
    target = model.objects.select_for_update().get(pk=target_id)
    if not user_can(actor, 'suppliers' if supplier else 'customers', 'view'):
        raise PermissionDenied('无权访问替换目标。')
    if supplier and not target.is_active:
        raise ValidationError('替换供应商已停用。')
    if not supplier and not customer_in_scope(target.pk, actor):
        raise PermissionDenied('替换客户不在账号范围内。')
    if target.pk == getattr(source, 'supplier_id' if supplier else 'customer_id'):
        raise ValidationError('替换目标必须不同于原主体。')
    return target


_FIELDS = {
    'quote': {'customer', 'quote_date', 'valid_until', 'currency', 'exchange_rate', 'shipping_fee', 'discount', 'notes', 'recipient_name', 'buyer_address', 'buyer_email', 'buyer_phone', 'buyer_tax_id', 'lead_time_days', 'deposit_ratio', 'trading_terms', 'shipping_details', 'items'},
    'order': {'customer', 'order_date', 'expected_ship_date', 'tail_goods_policy', 'currency', 'exchange_rate', 'shipping_fee', 'discount', 'notes', 'items'},
    'purchase_order': {'supplier', 'order_date', 'expected_arrival_date', 'currency', 'exchange_rate', 'notes', 'payment_terms_snapshot', 'items'},
}
_LINE_FIELDS = {'sku', 'quantity', 'unit_price', 'notes', 'supplier_sku', 'cost_price', 'trade_unit', 'trade_quantity', 'trade_unit_price'}


def _payload(kind, payload, target_id):
    if not isinstance(payload, dict) or set(payload) - _FIELDS[kind]:
        raise ValidationError('新单包含不允许的字段或来源关联。')
    party = 'supplier' if kind == 'purchase_order' else 'customer'
    required = {party, 'quote_date' if kind == 'quote' else 'order_date', 'currency', 'exchange_rate', 'items'}
    required |= {'shipping_fee', 'discount', 'deposit_ratio', 'trading_terms', 'shipping_details', 'recipient_name', 'buyer_address', 'buyer_phone', 'buyer_email', 'buyer_tax_id'} if kind == 'quote' else {'shipping_fee', 'discount', 'tail_goods_policy'} if kind == 'order' else {'payment_terms_snapshot'}
    if not required.issubset(payload) or payload[party] != target_id:
        raise ValidationError('请完整填写新单条款并选择已批准的目标。')
    if any(payload[key] in (None, '') for key in (party, 'quote_date' if kind == 'quote' else 'order_date', 'currency', 'exchange_rate')):
        raise ValidationError('新单日期、币种和汇率不能为空。')
    rows = payload['items']
    if not isinstance(rows, list) or not rows:
        raise ValidationError('请明确提供新单商品明细。')
    for row in rows:
        if not isinstance(row, dict) or set(row) - _LINE_FIELDS or any(row.get(k) in (None, '') for k in ('sku', 'quantity', 'unit_price')):
            raise ValidationError('商品明细必须明确填写 SKU、数量和单价，不能包含来源记录。')
    return payload


def _hash_payload(value):
    try:
        raw = json.dumps(value, cls=DjangoJSONEncoder, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValidationError('新单内容无法校验。') from exc
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def _link_hash(link):
    return pv._digest({'target_id': link.target_id, 'approval_id': link.approval_id,
        'result_quote_id': link.result_quote_id, 'result_order_id': link.result_order_id,
        'result_purchase_order_id': link.result_purchase_order_id, 'created_by_id': link.created_by_id,
        'approved_fingerprint': link.approved_fingerprint, 'approval_fingerprint': link.approval_fingerprint,
        'payload_fingerprint': link.payload_fingerprint})


def _verify_replay(link, approval, kind, target_id, payload_hash, proposed_snapshot):
    """Return the same link without restoring later edits to the new document.

    The caller already holds the source/request/target/approval/link locks.
    Lock the result last, as formalization does. Changed original payload,
    association, approved party, or approval evidence makes retry fail closed.
    """
    if (link.approval_id != approval.pk or link.approved_fingerprint != approval.approved_fingerprint
        or link.approval_fingerprint != pv._approval_attestation_fingerprint(approval)
        or link.payload_fingerprint != payload_hash or link.link_fingerprint != _link_hash(link)):
        raise ValidationError('替换记录或重试内容不一致。')
    result_id = getattr(link, 'result_' + kind + '_id')
    if result_id is None:
        raise ValidationError('替换结果类型不一致。')
    result = pv.TARGETS[kind][0].objects.select_for_update().get(pk=result_id)
    actual_id = result.supplier_id if kind == 'purchase_order' else result.customer_id
    source_relation = result.quote_id if kind == 'order' else result.order_id if kind == 'purchase_order' else result.parent_quote_id
    if actual_id != target_id or source_relation is not None:
        raise ValidationError('替换结果主体或来源已变更。')
    if kind == 'quote' and pv._snapshot(result, pv.TARGETS[kind][1]) != {key: proposed_snapshot[key] for key in pv.TARGETS[kind][1]}:
        raise ValidationError('替换报价主体已变更。')
    if 'party_details' in proposed_snapshot:
        from .party_document_details_models import PartyDocumentDetailsStorage
        row = PartyDocumentDetailsStorage.objects.filter(**{kind + '_id': result.pk}).first()
        stored_details = row.details if row else None
        if stored_details != proposed_snapshot['party_details']:
            raise ValidationError('替换结果的扩展主体资料已变更。')
    return link


@transaction.atomic
def create_replacement(*, request, request_id, payload):
    actor = pv._actor(request)
    if not request.user.is_authenticated or request.user.pk != actor.pk:
        raise PermissionDenied('需要与会话一致的认证账号。')
    obj, kind, source, fields = pv._locked_request(request_id)
    pv._authorize(actor, kind, source, write=True)
    if not user_can(actor, {'quote': 'quotes', 'order': 'orders', 'purchase_order': 'purchases'}[kind], 'create'):
        raise PermissionDenied('无权创建新单据。')
    if obj.change_type != 'replacement':
        raise ValidationError('申请不是法律主体替换。')
    binding = PartyReplacementTarget.objects.select_for_update().filter(request_id=obj.pk).first()
    if binding is None:
        raise ValidationError('旧申请未绑定替换目标，不能创建新单。')
    target_id = binding.supplier_id if kind == 'purchase_order' else binding.customer_id
    target = lock_target(actor, kind, source, target_id)
    if obj.proposed_snapshot.get('name') != binding.target_name:
        raise ValidationError('已批准的替换目标不一致。')
    approval = PartyVersionApproval.objects.select_for_update().filter(request_id=obj.pk).first()
    if (approval is None or approval.approver_id == obj.initiator_id or
        approval.approved_fingerprint != obj.content_fingerprint or obj.content_fingerprint != pv._digest(pv._content(obj))):
        raise ValidationError('申请内容或独立审批无效。')
    if not obj.source_document_fingerprint:
        raise ValidationError('旧申请缺少来源单据指纹。')
    approved_details = None
    if 'party_details' in obj.proposed_snapshot:
        from .party_document_details import validate_details
        approved_details = validate_details(obj.proposed_snapshot['party_details'])
        side = 'seller' if kind == 'purchase_order' else 'buyer'
        if approved_details[side]['name'] != binding.target_name:
            raise ValidationError('扩展资料中的目标名称必须与已批准的替换目标一致。')
        if kind == 'quote':
            raise ValidationError('现有报价模板尚不能展示完整扩展资料，不能创建替换报价。')
    pv._validate_saved_basis(obj, kind, source, fields)
    pv._validate_source_document(obj, kind, source)
    if pv._terminal(obj):
        raise ValidationError('申请已结束。')
    data = _payload(kind, payload, target_id)
    payload_hash = _hash_payload(data)
    existing = PartyReplacementLink.objects.select_for_update().filter(target=binding).first()
    if existing:
        return _verify_replay(existing, approval, kind, target_id, payload_hash, obj.proposed_snapshot)
    pv._require_active(obj)
    if target.name != binding.target_name:
        raise ValidationError('替换目标名称已变更。')
    allowed = {'quote': {'sent', 'accepted'}, 'order': {'confirmed', 'production', 'shipped', 'completed'}, 'purchase_order': {'ordered', 'partial', 'completed'}}
    if source.status not in allowed[kind]:
        raise ValidationError('原单状态不能创建替换单。')
    if kind != 'quote' and any(value is None for value in obj.proposed_snapshot.values()):
        raise ValidationError('新单主体字段不支持未知值，请先明确核对。')
    from .serializers import QuoteSerializer, OrderSerializer, PurchaseOrderSerializer
    serializer = {'quote': QuoteSerializer, 'order': OrderSerializer, 'purchase_order': PurchaseOrderSerializer}[kind](data=data, context={'request': request})
    serializer.is_valid(raise_exception=True)
    quote_snapshots = {}
    if kind == 'quote':
        # These fields are read-only in the public serializer. Supply the
        # approved values at creation instead of defaulting to today's master.
        for key in ('name', 'country'):
            field = fields[key]
            value = obj.proposed_snapshot[key]
            if not isinstance(value, str):
                raise ValidationError('替换报价的主体快照不完整。')
            quote_snapshots[field] = pv.TARGETS[kind][0]._meta.get_field(field).clean(value, None)
    result = serializer.save(**quote_snapshots)
    if result.status != 'draft' or (kind == 'quote' and pv._snapshot(result, fields) != {key: obj.proposed_snapshot[key] for key in fields}):
        raise ValidationError('新单主体快照与批准内容不一致，请核对目标资料。')
    if approved_details is not None:
        from .party_document_details_models import PartyDocumentDetailsStorage
        PartyDocumentDetailsStorage.objects.create(**{kind: result}, details=approved_details)
    from .audit import record_operation
    record_operation(request=request, instance=result, action='create')
    link = PartyReplacementLink(target=binding, approval=approval, created_by=actor,
        approved_fingerprint=approval.approved_fingerprint, approval_fingerprint=pv._approval_attestation_fingerprint(approval),
        payload_fingerprint=payload_hash, **{'result_' + kind: result})
    link.link_fingerprint = _link_hash(link)
    link.save(force_insert=True)
    if obj.__class__._base_manager.filter(pk=obj.pk, is_active=True).update(is_active=False) != 1:
        raise ValidationError('申请状态已变化。')
    return link


@dataclass(frozen=True)
class FormalizationContext:
    """A lock token valid only inside the transaction that obtained it."""
    kind: str
    result_id: int
    link_id: int
    alias: str
    outer_atomic: object


def _link_table_ready(using):
    connection = connections[using]
    if PartyReplacementLink._meta.db_table in connection.introspection.table_names():
        return True
    from django.db.migrations.recorder import MigrationRecorder
    if MigrationRecorder.Migration.objects.using(using).filter(app='crm', name='0115_party_replacement').exists():
        raise ValidationError('主体替换关联表缺失，拒绝正式化。')
    return False


def prepare_formalization(kind, result_id, *, using='default'):
    """Lock source, request, target, approval, link, then result, in that order.

    Call before *any* lock on the result document. A caller must remain in the
    same outer transaction and pass the returned token to the capture guard.
    No link means an ordinary document; its existing workflow is unchanged.
    """
    if kind not in pv.TARGETS or using != 'default':
        raise ValidationError('不支持的单据类型。')
    connection = connections[using]
    if not connection.in_atomic_block or not connection.atomic_blocks:
        raise ValidationError('主体替换正式化必须在事务内锁定。')
    if not _link_table_ready(using):
        return None
    ref = (PartyReplacementLink.objects.using(using).filter(**{'result_' + kind + '_id': result_id})
           .values('pk', 'target__request_id').first())
    if ref is None:
        return None
    obj, source_kind, source, fields = pv._locked_request(ref['target__request_id'])
    if source_kind != kind or obj._state.db != using:
        raise ValidationError('替换来源单据不一致。')
    binding = PartyReplacementTarget.objects.using(using).select_for_update().get(request_id=obj.pk)
    model = Supplier if kind == 'purchase_order' else Customer
    target_id = binding.supplier_id if kind == 'purchase_order' else binding.customer_id
    model.objects.using(using).select_for_update().get(pk=target_id)
    PartyVersionApproval.objects.using(using).select_for_update().get(request_id=obj.pk)
    link = PartyReplacementLink.objects.using(using).select_for_update().get(pk=ref['pk'], target_id=binding.pk)
    result_model = pv.TARGETS[kind][0]
    result = result_model.objects.using(using).select_for_update().get(pk=result_id)
    if getattr(link, 'result_' + kind + '_id') != result.pk:
        raise ValidationError('替换结果关联已变更。')
    pv._validate_saved_basis(obj, kind, source, fields)
    if not obj.source_document_fingerprint:
        raise ValidationError('替换申请缺少来源身份指纹。')
    pv._validate_source_document(obj, kind, source)
    token = FormalizationContext(kind, result.pk, link.pk, using, connection.atomic_blocks[-1])
    snapshot_for_confirmation(result, kind, context=token)
    return token


def snapshot_for_confirmation(document, kind, *, context=None):
    """Return the approved snapshot for a linked draft, or None for ordinary drafts.

    The caller must hold the document row lock and persist these values only as
    part of its existing atomic formalization operation.
    """
    alias = document._state.db or 'default'
    if not _link_table_ready(alias):
        return None
    link = PartyReplacementLink.objects.using(alias).select_for_update().filter(**{'result_' + kind: document}).first()
    if link is None:
        return None
    connection = connections[alias]
    if (not isinstance(context, FormalizationContext) or context.kind != kind or context.result_id != document.pk
            or context.link_id != link.pk or context.alias != alias or not connection.atomic_blocks
            or not any(block is context.outer_atomic for block in connection.atomic_blocks)):
        raise ValidationError('替换单据必须先按来源顺序锁定并复核。')
    binding = link.target
    approval = link.approval
    obj = approval.request
    actual_id = document.supplier_id if kind == 'purchase_order' else document.customer_id
    bound_id = binding.supplier_id if kind == 'purchase_order' else binding.customer_id
    source_relation = document.quote_id if kind == 'order' else document.order_id if kind == 'purchase_order' else document.parent_quote_id
    if (binding.request_id != obj.pk or obj.change_type != 'replacement' or pv._target_type(obj) != kind
        or obj.is_active or pv._terminal(obj) is not None or source_relation is not None
        or actual_id != bound_id or obj.proposed_snapshot.get('name') != binding.target_name
        or not obj.source_document_fingerprint or not obj.reason.strip() or not obj.evidence.strip()
        or approval.approver_id == obj.initiator_id or not approval.note.strip()
        or approval.approved_fingerprint != obj.content_fingerprint
        or obj.content_fingerprint != pv._digest(pv._content(obj))
        or link.approved_fingerprint != approval.approved_fingerprint
        or link.approval_fingerprint != pv._approval_attestation_fingerprint(approval)
        or link.link_fingerprint != _link_hash(link)):
        raise ValidationError('替换单据的主体批准或关联记录不一致。')
    fields = pv.TARGETS[kind][1]
    proposed = obj.proposed_snapshot
    has_details = isinstance(proposed, dict) and 'party_details' in proposed
    expected_fields = set(fields) | ({'party_details'} if has_details else set())
    if (not isinstance(proposed, dict) or set(proposed) != expected_fields
            or any(not isinstance(proposed[key], str) for key in fields)):
        raise ValidationError('替换单据的主体快照不完整。')
    from .party_document_details_models import PartyDocumentDetailsStorage
    row = (PartyDocumentDetailsStorage.objects.using(alias)
           .filter(**{kind + '_id': document.pk}).first())
    stored_details = row.details if row else None
    if has_details:
        from .party_document_details import validate_details
        if kind == 'quote':
            raise ValidationError('替换报价不能包含扩展主体资料。')
        approved_details = validate_details(proposed['party_details'])
        side = 'seller' if kind == 'purchase_order' else 'buyer'
        if approved_details[side]['name'] != binding.target_name or stored_details != approved_details:
            raise ValidationError('替换单据的扩展主体资料与批准内容不一致。')
    elif stored_details is not None:
        raise ValidationError('替换单据包含未经批准的扩展主体资料。')
    return {field: proposed[key] for key, field in fields.items()}
