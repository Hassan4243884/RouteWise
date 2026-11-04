"""
Django settings for the Weather-Aware Truck Routing backend.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# ──────────────────────────────────────────────────────────────────────────────
# Base directory & environment
# ──────────────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-dev-key-change-in-production",
)
DEBUG = os.environ.get("DEBUG", "True") == "True"

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# ──────────────────────────────────────────────────────────────────────────────
# Application definition
# ──────────────────────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "routing",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

# ──────────────────────────────────────────────────────────────────────────────
# Database — SQLite is fine; nothing is persisted for route requests
# ──────────────────────────────────────────────────────────────────────────────
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# ──────────────────────────────────────────────────────────────────────────────
# Django REST Framework
# ──────────────────────────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "EXCEPTION_HANDLER": "routing.views.custom_exception_handler",
}

# ──────────────────────────────────────────────────────────────────────────────
# CORS — allow the Vite dev server
# ──────────────────────────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = os.environ.get(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
).split(",")
CORS_ALLOW_ALL_ORIGINS = DEBUG  # open in dev only

# ──────────────────────────────────────────────────────────────────────────────
# Static files & Frontend distribution
# ──────────────────────────────────────────────────────────────────────────────
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

FRONTEND_DIST = BASE_DIR.parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    STATICFILES_DIRS = [FRONTEND_DIST]
    WHITENOISE_ROOT = FRONTEND_DIST

STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"

# ──────────────────────────────────────────────────────────────────────────────
# Templates (only needed if serving HTML error pages)
# ──────────────────────────────────────────────────────────────────────────────
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": []},
    }
]

# ──────────────────────────────────────────────────────────────────────────────
# Third-party API keys
# ──────────────────────────────────────────────────────────────────────────────
ORS_API_KEY = os.environ.get(
    "ORS_API_KEY",
    os.environ.get("OPENROUTESERVICE_API_KEY", ""),
)
HERE_API_KEY = os.environ.get("HERE_API_KEY", "")

# ──────────────────────────────────────────────────────────────────────────────
# External API timeouts (seconds)
# ──────────────────────────────────────────────────────────────────────────────
HTTP_TIMEOUT = 15  # per-request timeout for HERE and Open-Meteo calls

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
