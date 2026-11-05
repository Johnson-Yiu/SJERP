"""ERP session endpoints backed by Django authentication and CSRF middleware."""
import json

from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST


@never_cache
@ensure_csrf_cookie
@require_GET
def csrf(request):
    get_token(request)
    return JsonResponse({"detail": "可以登录。"})


@never_cache
@csrf_protect
@require_POST
def sign_in(request):
    try:
        payload = json.loads(request.body)
    except (ValueError, UnicodeDecodeError):
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    username, password = payload.get("username"), payload.get("password")
    if not isinstance(username, str) or not isinstance(password, str) or not username or not password:
        return JsonResponse({"detail": "账号或密码不正确。"}, status=400)
    user = authenticate(request, username=username, password=password)
    if user is None or not user.is_active:
        return JsonResponse({"detail": "账号或密码不正确。"}, status=400)
    login(request, user)
    return JsonResponse({"detail": "登录成功。"})


@never_cache
@csrf_protect
@require_POST
def sign_out(request):
    logout(request)
    return JsonResponse({"detail": "已退出登录。"})
