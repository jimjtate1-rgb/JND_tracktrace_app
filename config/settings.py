from pathlib import Path

import environ

from config.env import env

BASE_DIR = Path(__file__).resolve().parent.parent

# Load a local .env if present (never required to run).
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY", default="django-insecure-dev-only-change-me")
DEBUG = env.bool("DEBUG", default=True)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["127.0.0.1", "localhost", "*"])

# Domains allowed to send authenticated POSTs (admin, etc.) over HTTPS. Django 4+
# requires the scheme, e.g. https://your-app.onrender.com
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

# Render injects RENDER_EXTERNAL_HOSTNAME at runtime — trust it automatically so
# you don't have to hardcode the domain.
RENDER_EXTERNAL_HOSTNAME = env("RENDER_EXTERNAL_HOSTNAME", default="")
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)
    CSRF_TRUSTED_ORIGINS.append(f"https://{RENDER_EXTERNAL_HOSTNAME}")

# Behind Render's TLS-terminating proxy: trust the forwarded scheme and secure cookies.
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "django_filters",
    "drf_spectacular",
    "django_celery_beat",
]

LOCAL_APPS = [
    "tracktrace.common",
    "tracktrace.weather",
    "tracktrace.traceapi",
    "tracktrace.web",
    "tracktrace.feeds",
]

INSTALLED_APPS = [*DJANGO_APPS, *THIRD_PARTY_APPS, *LOCAL_APPS]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# SQLite by default so the project runs with zero external services.
# Set DATABASE_URL=psql://user:pass@host:5432/db to use PostgreSQL (enables full-text search).
if env("DATABASE_URL", default="").startswith(("psql", "postgres")):
    DATABASES = {"default": env.db("DATABASE_URL")}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# WhiteNoise serves static files in production (compressed + cache-busted hashes),
# so the site is styled with DEBUG=False without a separate web server / CDN.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_FILTER_BACKENDS": ("django_filters.rest_framework.DjangoFilterBackend",),
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Tracking & Tracing API",
    "DESCRIPTION": "Track a shipment by tracking number + carrier and get live weather at its destination.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# --- Celery ---------------------------------------------------------------
# A worker/beat is OPTIONAL: the API runs without them. They're only needed
# for the automatic 2-hourly weather refresh.
CELERY_BROKER_URL = env("REDIS_LOCATION", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = "django-db" if "django_celery_results" in INSTALLED_APPS else None
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# OpenWeatherMap. Accept the correct spelling and the original repo's typo'd key.
WEATHER_API_KEY = env("WEATHER_API_KEY", default=env("WEATHER_API_KYE", default=""))

# --- Carrier feeds --------------------------------------------------------
# DCSA Track & Trace v2 is the default provider. Point DCSA_BASE_URL at any
# DCSA-compliant carrier's T&T v2 endpoint and set the API key.
FEED_PROVIDER = env("FEED_PROVIDER", default="dcsa")
DCSA_BASE_URL = env("DCSA_BASE_URL", default="")          # e.g. https://api.<carrier>.com/dcsa/tnt/v2
DCSA_API_KEY = env("DCSA_API_KEY", default="")
DCSA_API_KEY_HEADER = env("DCSA_API_KEY_HEADER", default="API-Key")
DCSA_CARRIER_NAME = env("DCSA_CARRIER_NAME", default="")  # optional label stamped on shipments
DCSA_CARRIER_SCAC = env("DCSA_CARRIER_SCAC", default="")

# Air cargo feed (IATA Cargo-IMP FSU model).
AIR_FEED_BASE_URL = env("AIR_FEED_BASE_URL", default="")
AIR_FEED_API_KEY = env("AIR_FEED_API_KEY", default="")
AIR_FEED_API_KEY_HEADER = env("AIR_FEED_API_KEY_HEADER", default="API-Key")

# DCSA inbound subscription callbacks (carrier -> us). Set the secret returned at
# subscription time so callbacks verify (HMAC-SHA256 of the body).
DCSA_WEBHOOK_SECRET = env("DCSA_WEBHOOK_SECRET", default="")
DCSA_WEBHOOK_SIGNATURE_HEADER = env("DCSA_WEBHOOK_SIGNATURE_HEADER", default="Notification-Signature")

# Air inbound webhooks (provider -> us). HMAC-signed FSU callbacks.
AIR_WEBHOOK_SECRET = env("AIR_WEBHOOK_SECRET", default="")
AIR_WEBHOOK_SIGNATURE_HEADER = env("AIR_WEBHOOK_SIGNATURE_HEADER", default="X-Signature")
