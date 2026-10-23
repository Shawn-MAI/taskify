"""Django settings for the Taskify web service.

The web service holds no business data: it renders pages and relays calls to the API
service. Sessions are signed cookies, so no database is configured. Secrets come from
the environment only.
"""

import os
from pathlib import Path

from django.core.management.utils import get_random_secret_key

BASE_DIR = Path(__file__).resolve().parent.parent

ENVIRONMENT = os.environ.get("TASKIFY_ENV", "development")
PRODUCTION = ENVIRONMENT == "production"
DEBUG = os.environ.get("TASKIFY_DEBUG") == "1" and not PRODUCTION

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if PRODUCTION:
        raise RuntimeError("DJANGO_SECRET_KEY must be set when TASKIFY_ENV=production")
    SECRET_KEY = get_random_secret_key()  # per-process key for local development

ALLOWED_HOSTS = [h for h in os.environ.get("TASKIFY_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(",") if h]

INSTALLED_APPS = ["django.contrib.staticfiles", "boards"]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "boards.middleware.SecurityHeadersMiddleware",
]

ROOT_URLCONF = "taskify_web.urls"
WSGI_APPLICATION = "taskify_web.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": ["django.template.context_processors.request"]},
    }
]

DATABASES: dict = {}
SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

STATIC_URL = "/static/"
WHITENOISE_USE_FINDERS = True
USE_TZ = True
TIME_ZONE = "UTC"

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

if PRODUCTION:
    # TLS terminates at the reverse proxy (deploy/Caddyfile).
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True
    SECURE_REDIRECT_EXEMPT = [r"^health$"]
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
