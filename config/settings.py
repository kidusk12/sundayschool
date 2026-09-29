"""
Django settings for the Sunday School Administration System.

Architecture (see SRS §1.1): single Django project, session-based auth,
server-rendered templates + htmx + Alpine.js + Tailwind. No DRF, no JWT,
no CORS — there is only one origin.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Paths and environment
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

# Loads variables from a .env file at the project root (see .env.example).
# Nothing secret is ever hardcoded below.
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]

# DEBUG must be explicitly "True" in .env for local dev; anything else -> False.
DEBUG = os.environ.get("DJANGO_DEBUG", "False") == "True"

ALLOWED_HOSTS = [
    h.strip() for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",") if h.strip()
]

# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_htmx",
    "school",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "school.middleware.ForcePasswordChangeMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "school" / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "school.context_processors.role_flags",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
# SQLite is enough at the SRS's target scale (~2,000 students, a few dozen
# staff accounts). Swap DJANGO_DB_ENGINE/etc. in .env for Postgres later
# without touching this file's logic.

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ["DB_NAME"],
        "USER": os.environ["DB_USER"],
        "PASSWORD": os.environ["DB_PASSWORD"],
        "HOST": os.environ.get("DB_HOST", "localhost"),
        "PORT": os.environ.get("DB_PORT", "5432"),
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
# Django's built-in User model + a one-to-one Profile (school.Profile) that
# carries must_change_password, per SRS §3.1. No custom AUTH_USER_MODEL.

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "school.validators.AmMinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "school.validators.AmCommonPasswordValidator"},
    {"NAME": "school.validators.AmNumericValidator"},
    {"NAME": "school.validators.AmNotUsernameValidator"},
]

LOGIN_URL = "school:login"
LOGIN_REDIRECT_URL = "school:dashboard"
LOGOUT_REDIRECT_URL = "school:login"

# ---------------------------------------------------------------------------
# Sessions / CSRF
# ---------------------------------------------------------------------------
# Session-based auth is the entire auth mechanism (SRS §1.1) — no tokens.

SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False  # htmx needs to read the CSRF cookie via JS to send it back
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()
]

# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------
# The Amharic-first UI (SRS §5) is literal Amharic text written directly into
# templates, not run through Django's translation framework — so USE_I18N
# stays off. The Ethiopian calendar is computed server-side in
# school/ethiopic.py, not via locale machinery.

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Addis_Ababa"
USE_I18N = False
USE_TZ = True

# ---------------------------------------------------------------------------
# Static and media files
# ---------------------------------------------------------------------------
# Tailwind's compiled CSS + app.js live under school/static/school/ and are
# committed as static files — no bundler, no separate frontend package
# manager (SRS §5, "simplicity as a requirement").

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "school" / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# StudentFile uploads (SRS §3.7) — attached to a student or a class.
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# ---------------------------------------------------------------------------
# Misc
# ---------------------------------------------------------------------------

MESSAGE_STORAGE = "django.contrib.messages.storage.session.SessionStorage"