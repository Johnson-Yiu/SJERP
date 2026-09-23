from django.contrib.auth.models import AnonymousUser
from django.test import SimpleTestCase, override_settings
from rest_framework.test import APIRequestFactory

from crm.permissions import development_superadmin_enabled, is_permission_admin, QuoteExportPermission
from crm.views import current_operator


@override_settings(APP_STAGE="development", DEBUG=True, DEVELOPMENT_SUPERADMIN=True, RBAC_ENFORCEMENT=False)
class DevelopmentAccessTests(SimpleTestCase):
    def request(self):
        request = APIRequestFactory().get("/api/session/current-operator/")
        request.user = AnonymousUser()
        return request

    def test_development_has_full_access_without_claiming_login(self):
        self.assertTrue(is_permission_admin(AnonymousUser()))
        self.assertTrue(QuoteExportPermission().has_permission(self.request(), None))
        data = current_operator(self.request()).data
        self.assertTrue(data["has_all_permissions"])
        self.assertEqual(data["role"], "超级管理员")
        self.assertFalse(data["authenticated"])
        self.assertFalse(data["audit_log_enabled"])

    def test_each_environment_guard_disables_development_access(self):
        for settings in ({"APP_STAGE": "internal_test"}, {"APP_STAGE": "production"},
                         {"DEBUG": False}, {"DEVELOPMENT_SUPERADMIN": False}, {"RBAC_ENFORCEMENT": True}):
            with self.subTest(settings=settings), override_settings(**settings):
                self.assertFalse(development_superadmin_enabled())
                self.assertFalse(is_permission_admin(AnonymousUser()))
                self.assertFalse(QuoteExportPermission().has_permission(self.request(), None))
                data = current_operator(self.request()).data
                self.assertFalse(data["has_all_permissions"])
                self.assertEqual(data["role"], "未登录")
