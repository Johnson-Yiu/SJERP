import os
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

_TRUE_VALUES = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"0", "false", "no", "off"}
_DEPLOYED_STAGES = {"staging", "production"}


def _env_bool(name, default):
    raw = os.getenv(name)
    if raw is None:
        return default
    value = raw.strip().lower()
    if value in _TRUE_VALUES:
        return True
    if value in _FALSE_VALUES:
        return False
    raise ImproperlyConfigured(f"{name} must be a boolean value.")


def _env_int(name, default):
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw.strip())
    except ValueError as exc:
        raise ImproperlyConfigured(f"{name} must be an integer.") from exc


def _env_list(name, default=()):
    raw = os.getenv(name)
    if raw is None:
        return list(default)
    return [item.strip() for item in raw.split(",") if item.strip()]


APP_STAGE = os.getenv("APP_STAGE", "development").strip().lower()
if APP_STAGE not in {"development", "staging", "production"}:
    raise ImproperlyConfigured("APP_STAGE must be development, staging, or production.")

DEBUG = _env_bool("DJANGO_DEBUG", APP_STAGE == "development")
if APP_STAGE in _DEPLOYED_STAGES and DEBUG:
    raise ImproperlyConfigured("DJANGO_DEBUG must be false outside development.")

SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "dev-only-change-me" if APP_STAGE == "development" else "",
).strip()
if APP_STAGE in _DEPLOYED_STAGES:
    if not SECRET_KEY:
        raise ImproperlyConfigured("DJANGO_SECRET_KEY is required outside development.")
    if len(SECRET_KEY) < 32 or SECRET_KEY in {"dev-only-change-me", "change-me"}:
        raise ImproperlyConfigured("DJANGO_SECRET_KEY must be an independently managed value of at least 32 characters.")

# Development operators share full application access. Never infer this from a role label.
DEVELOPMENT_SUPERADMIN = _env_bool("DEVELOPMENT_SUPERADMIN", APP_STAGE == "development")
if APP_STAGE in _DEPLOYED_STAGES and DEVELOPMENT_SUPERADMIN:
    raise ImproperlyConfigured("DEVELOPMENT_SUPERADMIN must be false outside development.")

RBAC_ENFORCEMENT = _env_bool("RBAC_ENFORCEMENT", APP_STAGE != "development")
if APP_STAGE in _DEPLOYED_STAGES and not RBAC_ENFORCEMENT:
    raise ImproperlyConfigured("RBAC_ENFORCEMENT must be true outside development.")

DEFAULT_OPERATOR_NAME = os.getenv("DEFAULT_OPERATOR_NAME", "Johnson" if APP_STAGE == "development" else "").strip()
# Controlled aliases only; no account numbers, credentials, cutover date or balance.
RMB_CASH_ACCOUNT_IDS = tuple(value.strip() for value in os.getenv("RMB_CASH_ACCOUNT_IDS", "").split(",") if value.strip())
# Audit records stay disabled only in local development. Deployed environments
# must fail closed instead of silently accepting business writes without audit.
AUDIT_LOG_ENABLED = _env_bool("AUDIT_LOG_ENABLED", APP_STAGE != "development")
if APP_STAGE in _DEPLOYED_STAGES and not AUDIT_LOG_ENABLED:
    raise ImproperlyConfigured("AUDIT_LOG_ENABLED must be true outside development.")
ALLOWED_HOSTS = _env_list(
    "DJANGO_ALLOWED_HOSTS",
    ("localhost", "127.0.0.1") if APP_STAGE == "development" else (),
)
if APP_STAGE in _DEPLOYED_STAGES and (not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS):
    raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS must contain explicit hosts outside development.")

CORS_ALLOWED_ORIGINS = _env_list(
    "CORS_ALLOWED_ORIGINS",
    ("http://localhost:5191", "http://127.0.0.1:5191") if APP_STAGE == "development" else (),
)
CSRF_TRUSTED_ORIGINS = _env_list("CSRF_TRUSTED_ORIGINS")
if APP_STAGE in _DEPLOYED_STAGES:
    insecure_origins = [
        origin for origin in [*CORS_ALLOWED_ORIGINS, *CSRF_TRUSTED_ORIGINS]
        if not origin.lower().startswith("https://")
    ]
    if insecure_origins:
        raise ImproperlyConfigured("CORS_ALLOWED_ORIGINS and CSRF_TRUSTED_ORIGINS must use HTTPS outside development.")

SECURE_SSL_REDIRECT = _env_bool("SECURE_SSL_REDIRECT", APP_STAGE == "production")
SESSION_COOKIE_SECURE = _env_bool("SESSION_COOKIE_SECURE", APP_STAGE in _DEPLOYED_STAGES)
CSRF_COOKIE_SECURE = _env_bool("CSRF_COOKIE_SECURE", APP_STAGE in _DEPLOYED_STAGES)
if APP_STAGE == "production" and not all((SECURE_SSL_REDIRECT, SESSION_COOKIE_SECURE, CSRF_COOKIE_SECURE)):
    raise ImproperlyConfigured("Production requires HTTPS redirect and secure session/CSRF cookies.")

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https") if APP_STAGE in _DEPLOYED_STAGES else None
SECURE_HSTS_SECONDS = _env_int("SECURE_HSTS_SECONDS", 31536000 if APP_STAGE == "production" else 0)
SECURE_HSTS_INCLUDE_SUBDOMAINS = _env_bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", APP_STAGE == "production")
SECURE_HSTS_PRELOAD = _env_bool("SECURE_HSTS_PRELOAD", APP_STAGE == "production")
if APP_STAGE == "production" and SECURE_HSTS_SECONDS <= 0:
    raise ImproperlyConfigured("Production requires a positive SECURE_HSTS_SECONDS value.")
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "crm",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]
WSGI_APPLICATION = "config.wsgi.application"

def _database_config():
    """Keep SQLite for development while requiring PostgreSQL outside development."""
    database_url = os.getenv("DATABASE_URL", "").strip()
    if APP_STAGE in {"staging", "production"}:
        if not database_url:
            raise ImproperlyConfigured("DATABASE_URL is required for staging/production.")
        config = dj_database_url.parse(database_url, conn_max_age=60)
        if config.get("ENGINE") != "django.db.backends.postgresql":
            raise ImproperlyConfigured("DATABASE_URL must use PostgreSQL for staging/production.")
        return config
    return dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=60,
    )


DATABASES = {"default": _database_config()}

AUTH_PASSWORD_VALIDATORS = [] if APP_STAGE == "development" else [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LANGUAGE_CODE = "zh-hans"
TIME_ZONE = "Asia/Shanghai"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
_media_root_value = os.getenv("MEDIA_ROOT", "").strip()
if APP_STAGE in _DEPLOYED_STAGES and not _media_root_value:
    raise ImproperlyConfigured("MEDIA_ROOT is required outside development and must point to a persistent private volume.")
MEDIA_ROOT = Path(_media_root_value or BASE_DIR / "media")
if APP_STAGE in _DEPLOYED_STAGES and not MEDIA_ROOT.is_absolute():
    raise ImproperlyConfigured("MEDIA_ROOT must be an absolute path outside development.")

# FileField/ImageField already use Django's storage abstraction. Keep the
# initial deployment on a local filesystem while leaving one explicit seam for
# a future object-storage backend. No URL route is added for MEDIA_URL; ERP
# files are served only by crm.file_access after authorization.
MEDIA_STORAGE_BACKEND = os.getenv(
    "MEDIA_STORAGE_BACKEND",
    "django.core.files.storage.FileSystemStorage",
).strip()
if not MEDIA_STORAGE_BACKEND:
    raise ImproperlyConfigured("MEDIA_STORAGE_BACKEND must not be empty.")
_resolved_media_root = MEDIA_ROOT.resolve()
_resolved_static_root = STATIC_ROOT.resolve()
if _resolved_media_root == _resolved_static_root or _resolved_media_root in _resolved_static_root.parents or _resolved_static_root in _resolved_media_root.parents:
    raise ImproperlyConfigured("MEDIA_ROOT and STATIC_ROOT must be separate directories.")
STORAGES = {
    "default": {"BACKEND": MEDIA_STORAGE_BACKEND},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CORS_ALLOW_CREDENTIALS = True

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ["crm.permissions.ModuleActionPermission"],
    # The Browsable API builds HTML forms from serializer relation querysets;
    # those choices can disclose out-of-scope customers on otherwise denied
    # detail routes. The ERP client uses JSON, so keep API responses JSON-only.
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_FILTER_BACKENDS": [
        "crm.filters.PermissionAwareSearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
}

if APP_STAGE in _DEPLOYED_STAGES:
    # SessionAuthentication normally returns 403 when no authenticator can
    # provide a challenge.  Production uses a challenge-bearing subclass so
    # API clients receive an explicit 401 while the normal Django session
    # cookie remains the only supported ERP login mechanism.
    REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"] = [
        "crm.authentication.SessionAuthenticationWithChallenge",
    ]

# The legacy business-flow suite models the local unauthenticated development
# operator. RBAC-specific tests override these values to exercise restricted
# and production behavior explicitly.
TEST_RUNNER = "crm.test_runner.DevelopmentAccessTestRunner"
