"""Authorization-aware serving for files stored by CRM models."""
import logging
import warnings

from PIL import Image, UnidentifiedImageError
from django.http import FileResponse, Http404
from rest_framework.decorators import api_view, permission_classes

from .models import FollowUpAttachment, ProductCertificate, QuoteItem, SKU
from .permissions import SecureDefaultPermission, user_can
from .sales_scope import scope_customer_related_queryset


logger = logging.getLogger(__name__)


_SAFE_INLINE_IMAGE_TYPES = {
    "GIF": "image/gif",
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}
_FILE_UNAVAILABLE_MESSAGE = "附件当前不可访问，请联系管理员核查。"


def _verified_inline_image_type(file_obj):
    """Use decoded file bytes, never the upload MIME or suffix, for previews."""
    try:
        file_obj.seek(0)
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            image = Image.open(file_obj)
            content_type = _SAFE_INLINE_IMAGE_TYPES.get(image.format)
            if not content_type:
                return None
            image.verify()
            return content_type
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError,
            Image.DecompressionBombError, Image.DecompressionBombWarning):
        return None
    except Exception:
        # A preview parser failure must fall back to a download, not a 500 or
        # an error page that exposes storage details to the caller.
        return None
    finally:
        try:
            file_obj.seek(0)
        except (OSError, ValueError):
            pass


@api_view(["GET"])
@permission_classes([SecureDefaultPermission])
def protected_media(request, relative_path):
    """Serve only a stored file whose owning business record is authorized."""
    file_field = None
    display_filename = None

    attachment = scope_customer_related_queryset(
        FollowUpAttachment.objects.select_related("follow_up"),
        request.user,
        relation="follow_up__customer",
    ).filter(file=relative_path).first()
    if attachment:
        if not user_can(request.user, "followups", "view"):
            raise Http404(_FILE_UNAVAILABLE_MESSAGE)
        file_field = attachment.file
        display_filename = attachment.name

    if file_field is None:
        quote_item = scope_customer_related_queryset(
            QuoteItem.objects.select_related("quote"), request.user, relation="quote__customer",
        ).filter(image_snapshot=relative_path).first()
        if quote_item:
            if not user_can(request.user, "quotes", "view") or not user_can(request.user, "skus", "view"):
                raise Http404(_FILE_UNAVAILABLE_MESSAGE)
            file_field = quote_item.image_snapshot

    if file_field is None:
        sku = SKU.objects.filter(image=relative_path).first()
        if sku:
            if not user_can(request.user, "skus", "view"):
                raise Http404(_FILE_UNAVAILABLE_MESSAGE)
            file_field = sku.image

    if file_field is None:
        certificate = ProductCertificate.objects.filter(file=relative_path).first()
        if certificate:
            if not user_can(request.user, "certificates", "view"):
                raise Http404(_FILE_UNAVAILABLE_MESSAGE)
            file_field = certificate.file

    if file_field is None:
        raise Http404(_FILE_UNAVAILABLE_MESSAGE)
    source = None
    try:
        filename = display_filename or file_field.name.rsplit("/", 1)[-1]
        source = file_field.open("rb")
        resolved_content_type = _verified_inline_image_type(source) or "application/octet-stream"
        response = FileResponse(
            source,
            as_attachment=resolved_content_type == "application/octet-stream",
            filename=filename,
            content_type=resolved_content_type,
        )
    except (OSError, ValueError) as exc:
        if source is not None:
            source.close()
        logger.warning(
            "Protected media read failed for storage key %r (%s)",
            getattr(file_field, "name", ""),
            type(exc).__name__,
        )
        raise Http404(_FILE_UNAVAILABLE_MESSAGE)
    response["X-Content-Type-Options"] = "nosniff"
    response["Cache-Control"] = "private, no-store"
    response["Content-Security-Policy"] = "default-src 'none'; sandbox"
    response["Cross-Origin-Resource-Policy"] = "same-origin"
    response["Referrer-Policy"] = "no-referrer"
    return response
