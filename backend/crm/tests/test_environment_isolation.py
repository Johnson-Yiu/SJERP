from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.test import APIClient, APIRequestFactory
from rest_framework.views import APIView

from crm.authentication import SessionAuthenticationWithChallenge


PRODUCTION_API_SETTINGS = {
    "DEFAULT_PERMISSION_CLASSES": ["crm.permissions.ModuleActionPermission"],
    "DEFAULT_AUTHENTICATION_CLASSES": ["crm.authentication.SessionAuthenticationWithChallenge"],
}


@override_settings(
    APP_STAGE="production",
    DEBUG=False,
    DEVELOPMENT_SUPERADMIN=False,
    RBAC_ENFORCEMENT=True,
    REST_FRAMEWORK=PRODUCTION_API_SETTINGS,
)
class ProductionAuthenticationTests(TestCase):
    def test_anonymous_business_api_returns_401_with_session_challenge(self):
        class ProtectedView(APIView):
            authentication_classes = [SessionAuthenticationWithChallenge]
            permission_classes = [IsAuthenticated]

            def get(self, request):
                return Response({"ok": True})

        request = APIRequestFactory().get("/api/production-protected/")
        response = ProtectedView.as_view()(request)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.headers.get("WWW-Authenticate"), "Session")

    def test_authenticated_user_without_module_permission_returns_403(self):
        user = get_user_model().objects.create_user(username="iss051-restricted", password="test-password")
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get("/api/customers/")

        self.assertEqual(response.status_code, 403)
