"""Require an intact approval before a changed quote party becomes formal."""
from django.apps import apps
from django.core.exceptions import ValidationError

PARTY_FIELDS = {
    'name': 'buyer_company_name', 'country': 'buyer_country_snapshot',
    'address': 'buyer_address', 'contact': 'recipient_name',
    'phone': 'buyer_phone', 'email': 'buyer_email', 'tax_id': 'buyer_tax_id',
}
MESSAGE = '报价主体变更须先完成独立审批。'


def _party(quote):
    return {key: getattr(quote, field) for key, field in PARTY_FIELDS.items()}


def _approved_boundary(source, revision):
    Application = apps.get_model('crm', 'PartyQuoteApplication')
    application = Application.objects.select_for_update().filter(result_quote_id=revision.pk).first()
    if application is None:
        return False
    from .party_version import (_application_fingerprint, _approval_attestation_fingerprint,
                                _content, _digest, _validate_saved_basis, _quote_fingerprint,
                                _validate_source_document, TARGETS)
    Approval = apps.get_model('crm', 'PartyVersionApproval')
    Request = apps.get_model('crm', 'PartyVersionRequest')
    approval = Approval.objects.select_for_update().get(pk=application.approval_id)
    request = Request.objects.select_for_update().get(pk=approval.request_id)
    try:
        if (application.source_quote_id != source.pk or revision.parent_quote_id != source.pk
                or request.quote_id != source.pk or request.order_id is not None
                or request.purchase_order_id is not None or request.quote_customer_id != source.customer_id
                or revision.customer_id != source.customer_id or request.change_type != 'correction'
                or approval.approver_id == request.initiator_id
                or not request.reason.strip() or not request.evidence.strip() or not approval.note.strip()
                or request.content_fingerprint != _digest(_content(request))
                or approval.approved_fingerprint != request.content_fingerprint
                or application.approved_fingerprint != approval.approved_fingerprint
                or application.approval_attestation_fingerprint != _approval_attestation_fingerprint(approval)
                or application.application_fingerprint != _application_fingerprint(application)):
            return False
        _validate_saved_basis(request, 'quote', source, TARGETS['quote'][1])
        if not request.source_document_fingerprint:
            return False
        _validate_source_document(request, 'quote', source)
        if application.source_fingerprint != request.source_document_fingerprint:
            return False
        items = list(revision.items.select_for_update().order_by('id'))
        if _quote_fingerprint(revision, items) != application.revision_fingerprint:
            return False
        proposal = request.proposed_snapshot
        if not isinstance(proposal, dict) or set(proposal) != set(request.base_snapshot):
            return False
        expected = _party(source)
        expected.update(proposal)
        return _party(revision) == expected
    except (AttributeError, TypeError, ValueError, ValidationError):
        return False


def guard_quote_party_approval(quote, *, status=None, update_fields=None):
    """Called in an atomic block before a revision can become sent/accepted."""
    if (status or quote.status) not in {'sent', 'accepted'} or not quote.parent_quote_id:
        return
    Quote = apps.get_model('crm', 'Quote')
    if quote.pk and not quote._state.adding:
        persisted = Quote.objects.select_for_update().filter(pk=quote.pk).values_list('status', flat=True).first()
        if persisted != 'draft' or (status is None and update_fields is not None and 'status' not in update_fields):
            return
    chain = [quote]
    seen = {quote.pk} if quote.pk else set()
    parent_id = quote.parent_quote_id
    while parent_id:
        if parent_id in seen:
            raise ValidationError(MESSAGE)
        seen.add(parent_id)
        parent = Quote.objects.select_for_update().filter(pk=parent_id).first()
        if parent is None:
            raise ValidationError(MESSAGE)
        chain.append(parent)
        parent_id = parent.parent_quote_id
    # The nearest formal ancestor defines the historical baseline. Drafts cannot
    # themselves become a trusted baseline, even across multiple generations.
    formal_index = next((i for i, node in enumerate(chain[1:], 1) if node.status != 'draft'), None)
    if formal_index is None:
        return
    source = chain[formal_index]
    if quote.customer_id != source.customer_id:
        raise ValidationError(MESSAGE)
    if _party(quote) == _party(source):
        return
    for index in range(formal_index - 1, -1, -1):
        revision = chain[index]
        parent = chain[index + 1]
        if revision.pk and _approved_boundary(parent, revision):
            if _party(quote) == _party(revision) and quote.customer_id == revision.customer_id:
                return
    raise ValidationError(MESSAGE)
