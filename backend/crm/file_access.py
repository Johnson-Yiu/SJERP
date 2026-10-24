"""Authorization-aware serving for files stored by CRM models."""
import mimetypes

from django.http import FileResponse, Http404
from rest_framework.decorators import api_view, permission_classes

from .models import FollowUpAttachment, ProductCertificate, QuoteItem, SKU
from .permissions import SecureDefaultPermission, user_can
from .sales_scope import scope_customer_related_queryset


@api_view(["GET"])
@permission_classes([SecureDefaultPermission])
def protected_media(request, relative_path):
    """Serve only a stored file whose owning business record is authorized."""
    file_field = None
    content_type = None

    attachment = scope_customer_related_queryset(
        FollowUpAttachment.objects.select_related("follow_up"),
        request.user,
        relation="follow_up__customer",
    ).filter(file=relative_path).first()
    if attachment:
        if not user_can(request.user, "followups", "view"):
            raise Http404
        file_field = attachment.file
        content_type = attachment.content_type

    if file_field is None:
        quote_item = scope_customer_related_queryset(
            QuoteItem.objects.select_related("quote"), request.user, relation="quote__customer",
        ).filter(image_snapshot=relative_path).first()
        if quote_item:
            if not user_can(request.user, "quotes", "view") or not user_can(request.user, "skus", "view"):
                raise Http404
            file_field = quote_item.image_snapshot

    if file_field is None:
        sku = SKU.objects.filter(image=relative_path).first()
        if sku:
            if not user_can(request.user, "skus", "view"):
                raise Http404
            file_field = sku.image

    if file_field is None:
        certificate = ProductCertificate.objects.filter(file=relative_path).first()
        if certificate:
            if not user_can(request.user, "certificates", "view"):
                raise Http404
            file_field = certificate.file

    if file_field is None:
        raise Http404
    try:
        response = FileResponse(
            file_field.open("rb"),
            as_attachment=False,
            filename=file_field.name.rsplit("/", 1)[-1],
            content_type=content_type or mimetypes.guess_type(file_field.name)[0] or "application/octet-stream",
        )
    except (OSError, ValueError):
        raise Http404
    response["X-Content-Type-Options"] = "nosniff"
    response["Cache-Control"] = "private, no-store"
    return response
