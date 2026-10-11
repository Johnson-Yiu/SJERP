from django.test import override_settings
from django.test.runner import DiscoverRunner


class DevelopmentAccessTestRunner(DiscoverRunner):
    """Preserve local development access for legacy API business-flow tests."""

    def setup_test_environment(self, **kwargs):
        super().setup_test_environment(**kwargs)
        self._development_access = override_settings(
            APP_STAGE="development",
            DEBUG=True,
            DEVELOPMENT_SUPERADMIN=True,
            RBAC_ENFORCEMENT=False,
        )
        self._development_access.enable()

    def teardown_test_environment(self, **kwargs):
        self._development_access.disable()
        super().teardown_test_environment(**kwargs)
