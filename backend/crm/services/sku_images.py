"""Generate static list thumbnails on demand, never while serializing a list."""
from hashlib import sha256
from io import BytesIO

from django.core.cache import cache
from django.http import Http404, HttpResponse, HttpResponseNotModified
from PIL import Image, ImageOps, UnidentifiedImageError


def thumbnail_response(field, request):
    if not field:
        raise Http404("暂无图片")
    try:
        storage = field.storage
        revision = f"{field.name}:{storage.size(field.name)}:{storage.get_modified_time(field.name)}"
        digest = sha256(revision.encode()).hexdigest()
        etag = f'"sku-thumb-v1-{digest}"'
        if request.headers.get("If-None-Match") == etag:
            response = HttpResponseNotModified()
        else:
            key = f"sku-thumb-v1:{digest}"
            content = cache.get(key)
            if content is None:
                with storage.open(field.name, "rb") as source, Image.open(source) as original:
                    # The first frame makes animated GIF/WebP inexpensive in lists.
                    original.seek(0)
                    original.thumbnail((84, 84), Image.Resampling.LANCZOS)
                    thumbnail = ImageOps.exif_transpose(original).convert("RGBA")
                    output = BytesIO()
                    thumbnail.save(output, format="WEBP", quality=80)
                    content = output.getvalue()
                cache.set(key, content, timeout=86400)
            response = HttpResponse(content, content_type="image/webp")
        response["ETag"] = etag
        response["Cache-Control"] = "private, max-age=0, must-revalidate"
        return response
    except (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombError) as error:
        raise Http404("图片不可用") from error
