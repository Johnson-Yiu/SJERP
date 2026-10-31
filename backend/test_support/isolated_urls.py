"""URL configuration used only by the isolated Playwright server process."""

import os

from django.conf import settings
from django.http import JsonResponse
from django.urls import path

from config.urls import urlpatterns as application_urlpatterns
from .isolated_runtime import IsolationError, verify_isolated_runtime


def isolation_identity(request, token):
    if token != os.environ.get("ISOLATED_TEST_TOKEN"):
        return JsonResponse({"error": "isolation identity mismatch"}, status=404)
    try:
        identity = verify_isolated_runtime(settings=settings, database_must_exist=True)
    except IsolationError:
        return JsonResponse({"error": "isolation verification failed"}, status=503)
    return JsonResponse(identity)


urlpatterns = [
    path("api/__test__/isolation/<str:token>/", isolation_identity),
    *application_urlpatterns,
]
