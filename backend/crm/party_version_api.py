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


class ApprovalInput(serializers.Serializer):
    expected_content_fingerprint = serializers.CharField(max_length=64)
    note = serializers.CharField()


def _translate(error):
    if isinstance(error, ObjectDoesNotExist):
        from rest_framework.exceptions import NotFound
        raise NotFound('报价或主体申请不存在。') from error
    raise serializers.ValidationError(getattr(error, 'message_dict', error.messages)) from error


def _payload(obj):
    decision = getattr(obj, 'approval', None)
    application = getattr(decision, 'application', None) if decision else None
    return {
        'id': obj.pk, 'initiator_id': obj.initiator_id, 'created_at': obj.created_at, 'change_type': obj.change_type,
        'reason': obj.reason, 'evidence': obj.evidence, 'source_trust': obj.source_trust,
        'base_snapshot': obj.base_snapshot, 'proposed_snapshot': obj.proposed_snapshot,
        'content_fingerprint': obj.content_fingerprint,
        'approval': {'id': decision.pk, 'approver_id': decision.approver_id, 'note': decision.note, 'created_at': decision.created_at} if decision else None,
        'application': {'result_quote_id': application.result_quote_id, 'applied_by_id': application.applied_by_id,
                        'created_at': application.created_at} if application else None,
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
        except (DjangoValidationError, ObjectDoesNotExist) as error:
            _translate(error)
        from rest_framework.exceptions import NotFound
        raise NotFound('不支持的主体申请操作。')
