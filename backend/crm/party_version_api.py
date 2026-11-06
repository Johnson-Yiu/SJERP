"""Authenticated quotation party-change endpoints; existing permission rules apply."""
from django.core.exceptions import ObjectDoesNotExist, ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .authentication import SessionAuthenticationWithChallenge
from .models import PartyVersionRequest, Quote
from .party_version import approve, baseline, propose


class ProposalInput(serializers.Serializer):
    expected_base_fingerprint = serializers.CharField(max_length=64)
    proposed_snapshot = serializers.JSONField()
    change_type = serializers.ChoiceField(choices=['correction', 'replacement'])
    reason = serializers.CharField()
    evidence = serializers.CharField()
    source_trust = serializers.ChoiceField(choices=['unknown', 'unverified'])
    replacement_target_id = serializers.IntegerField(min_value=1, required=False)


class ApprovalInput(serializers.Serializer):
    expected_content_fingerprint = serializers.CharField(max_length=64)
    note = serializers.CharField()


class PartyDetailsView(APIView):
    authentication_classes = [SessionAuthenticationWithChallenge]
    from .permissions import SecureDefaultPermission
    permission_classes = [SecureDefaultPermission]

    def get(self, request, target_type, document_id):
        from .party_document_details import read_document_details, validate_details
        from .party_document_details_models import PartyDocumentDetailsStorage
        try:
            details = read_document_details(request=request, target_type=target_type, target_id=document_id)
            row = PartyDocumentDetailsStorage.objects.filter(**{target_type + '_id': document_id}).first()
            original = validate_details(row.details) if row and row.details is not None else None
        except (DjangoValidationError, ObjectDoesNotExist) as error:
            _translate(error)
        return Response({'details': details, 'original_details': original})

    def put(self, request, target_type, document_id):
        from .party_document_details import save_draft_details
        try:
            details = save_draft_details(request=request, target_type=target_type,
                                         target_id=document_id, details=request.data.get('details'))
        except (DjangoValidationError, ObjectDoesNotExist) as error:
            _translate(error)
        return Response({'details': details})


def _translate(error):
    if isinstance(error, ObjectDoesNotExist):
        from rest_framework.exceptions import NotFound
        raise NotFound('报价或主体申请不存在。') from error
    raise serializers.ValidationError(getattr(error, 'message_dict', error.messages)) from error


def _payload(obj):
    decision = getattr(obj, 'approval', None)
    application = getattr(decision, 'application', None) if decision else None
    document_version = getattr(decision, 'document_version', None) if decision else None
    binding = getattr(obj, 'replacement_target', None)
    replacement = getattr(binding, 'link', None) if binding else None
    terminal = getattr(obj, 'terminal_event', None)
    lifecycle_status = terminal.kind if terminal else ('applied' if application or document_version or replacement else ('approved' if decision else 'pending'))
    return {
        'id': obj.pk, 'initiator_id': obj.initiator_id, 'created_at': obj.created_at, 'change_type': obj.change_type,
        'reason': obj.reason, 'evidence': obj.evidence, 'source_trust': obj.source_trust,
        'base_snapshot': obj.base_snapshot, 'proposed_snapshot': obj.proposed_snapshot,
        'content_fingerprint': obj.content_fingerprint,
        'replacement_target': {'customer_id': binding.customer_id, 'supplier_id': binding.supplier_id, 'name': binding.target_name} if binding else None,
        'replacement_result': {'result_quote_id': replacement.result_quote_id, 'result_order_id': replacement.result_order_id, 'result_purchase_order_id': replacement.result_purchase_order_id, 'created_by_id': replacement.created_by_id, 'created_at': replacement.created_at} if replacement else None,
        'status': lifecycle_status,
        'terminal_event': {'id': terminal.pk, 'kind': terminal.kind, 'actor_id': terminal.actor_id,
                           'note': terminal.note, 'created_at': terminal.created_at,
                           'request_fingerprint': terminal.request_fingerprint} if terminal else None,
        'approval': {'id': decision.pk, 'approver_id': decision.approver_id, 'note': decision.note, 'created_at': decision.created_at} if decision else None,
        'application': {'result_quote_id': application.result_quote_id, 'applied_by_id': application.applied_by_id,
                        'created_at': application.created_at} if application else None,
        'document_version': {'id': document_version.pk, 'version_no': document_version.version_no,
                             'applied_by_id': document_version.applied_by_id, 'created_at': document_version.created_at}
                            if document_version else None,
    }


class QuotePartyChangeView(APIView):
    authentication_classes = [SessionAuthenticationWithChallenge]
    permission_classes = [IsAuthenticated]

    def get(self, request, quote_id):
        try:
            current = baseline(request=request, target_type='quote', target_id=quote_id)
        except (DjangoValidationError, ObjectDoesNotExist) as error:
            _translate(error)
        requests = PartyVersionRequest.objects.filter(quote_id=quote_id).order_by('-created_at', '-id')
        from .party_version_models import PartyQuoteApplication
        cursor = Quote.objects.only('pk', 'parent_quote_id', 'customer_id').get(pk=quote_id)
        customer_id, seen, origin = cursor.customer_id, set(), None
        while cursor and cursor.pk not in seen and cursor.customer_id == customer_id:
            seen.add(cursor.pk)
            origin = PartyQuoteApplication.objects.filter(result_quote_id=cursor.pk).select_related('approval__request').first()
            if origin and (cursor.parent_quote_id != origin.source_quote_id or origin.approval.request.quote_id != origin.source_quote_id):
                origin = None
                break
            if origin or not cursor.parent_quote_id:
                break
            cursor = Quote.objects.only('pk', 'parent_quote_id', 'customer_id').filter(pk=cursor.parent_quote_id).first()
        origin_data = ({'source_quote_id': origin.source_quote_id, 'request_id': origin.approval.request_id,
                        'source_trust': origin.approval.request.source_trust} if origin else None)
        return Response({'baseline': current, 'requests': [_payload(obj) for obj in requests],
                         'current_user_id': request.user.pk, 'origin': origin_data})

    def post(self, request, quote_id):
        data = ProposalInput(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            obj = propose(request=request, target_type='quote', target_id=quote_id, **data.validated_data)
        except (DjangoValidationError, ObjectDoesNotExist) as error:
            _translate(error)
        return Response(_payload(obj), status=status.HTTP_201_CREATED)


class QuotePartyChangeDecisionView(APIView):
    authentication_classes = [SessionAuthenticationWithChallenge]
    permission_classes = [IsAuthenticated]

    def post(self, request, quote_id, request_id, operation):
        try:
            baseline(request=request, target_type='quote', target_id=quote_id)
            obj = get_object_or_404(PartyVersionRequest.objects.filter(quote_id=quote_id), pk=request_id)
            if operation == 'approve':
                data = ApprovalInput(data=request.data)
                data.is_valid(raise_exception=True)
                approve(request=request, request_id=obj.pk, **data.validated_data)
                return Response(_payload(PartyVersionRequest.objects.get(pk=obj.pk)))
            if operation == 'apply':
                from .party_version import apply_approved_quote_change
                result = apply_approved_quote_change(request=request, request_id=obj.pk)
                return Response({'result_quote_id': result.result_quote_id})
            if operation == 'create-replacement':
                from .party_replacement import create_replacement
                result = create_replacement(request=request, request_id=obj.pk, payload=request.data)
                return Response({'result_quote_id': result.result_quote_id})
            if operation in {'reject', 'withdraw', 'invalidate'}:
                from .party_version import reject, withdraw, invalidate
                data = ApprovalInput(data={'expected_content_fingerprint': obj.content_fingerprint,
                                           'note': request.data.get('note', '')})
                data.is_valid(raise_exception=True)
                {'reject': reject, 'withdraw': withdraw, 'invalidate': invalidate}[operation](
                    request=request, request_id=obj.pk, note=data.validated_data['note'])
                return Response(_payload(PartyVersionRequest.objects.get(pk=obj.pk)))
        except (DjangoValidationError, ObjectDoesNotExist) as error:
            _translate(error)
        from rest_framework.exceptions import NotFound
        raise NotFound('不支持的主体申请操作。')


class DocumentPartyChangeView(APIView):
    authentication_classes = [SessionAuthenticationWithChallenge]
    permission_classes = [IsAuthenticated]

    def get(self, request, target_type, document_id):
        if target_type not in {'order', 'purchase_order'}:
            from rest_framework.exceptions import NotFound
            raise NotFound('不支持的单据类型。')
        try:
            current = baseline(request=request, target_type=target_type, target_id=document_id)
        except (DjangoValidationError, ObjectDoesNotExist) as error:
            _translate(error)
        requests = PartyVersionRequest.objects.filter(**{target_type + '_id': document_id}).order_by('-created_at', '-id')
        return Response({'baseline': current, 'requests': [_payload(obj) for obj in requests],
                         'current_user_id': request.user.pk})

    def post(self, request, target_type, document_id):
        if target_type not in {'order', 'purchase_order'}:
            from rest_framework.exceptions import NotFound
            raise NotFound('不支持的单据类型。')
        data = ProposalInput(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            obj = propose(request=request, target_type=target_type, target_id=document_id, **data.validated_data)
        except (DjangoValidationError, ObjectDoesNotExist) as error:
            _translate(error)
        return Response(_payload(obj), status=status.HTTP_201_CREATED)


class DocumentPartyChangeDecisionView(APIView):
    authentication_classes = [SessionAuthenticationWithChallenge]
    permission_classes = [IsAuthenticated]

    def post(self, request, target_type, document_id, request_id, operation):
        if target_type not in {'order', 'purchase_order'}:
            from rest_framework.exceptions import NotFound
            raise NotFound('不支持的单据类型。')
        try:
            baseline(request=request, target_type=target_type, target_id=document_id)
            obj = get_object_or_404(PartyVersionRequest.objects.filter(**{target_type + '_id': document_id}), pk=request_id)
            if operation == 'approve':
                data = ApprovalInput(data=request.data)
                data.is_valid(raise_exception=True)
                approve(request=request, request_id=obj.pk, **data.validated_data)
                return Response(_payload(PartyVersionRequest.objects.get(pk=obj.pk)))
            if operation == 'apply':
                from .party_document_version import apply
                result = apply(request=request, request_id=obj.pk)
                return Response({'version_id': result.pk, 'version_no': result.version_no})
            if operation == 'create-replacement':
                from .party_replacement import create_replacement
                result = create_replacement(request=request, request_id=obj.pk, payload=request.data)
                return Response({'result_order_id': result.result_order_id, 'result_purchase_order_id': result.result_purchase_order_id})
            if operation in {'reject', 'withdraw', 'invalidate'}:
                from .party_version import reject, withdraw, invalidate
                note = serializers.CharField().run_validation(request.data.get('note', ''))
                {'reject': reject, 'withdraw': withdraw, 'invalidate': invalidate}[
                    operation](request=request, request_id=obj.pk, note=note)
                return Response(_payload(PartyVersionRequest.objects.get(pk=obj.pk)))
        except (DjangoValidationError, ObjectDoesNotExist) as error:
            _translate(error)
        from rest_framework.exceptions import NotFound
        raise NotFound('不支持的主体申请操作。')
