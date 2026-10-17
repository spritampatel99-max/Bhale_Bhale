"""
Django settings for NovaMart (educational prototype).

Reference: https://docs.djangoproject.com/en/6.1/ref/settings/
Deployment checklist: https://docs.djangoproject.com/en/6.1/howto/deployment/checklist/
"""
import os
from decimal import Decimal
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


# --------------------------------------------------------------------------
# Tiny .env loader (avoids an extra dependency). Real environment variables
# always win over values in the file.
# --------------------------------------------------------------------------
def _load_env_file(path):
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env_file(BASE_DIR / ".env")


def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name, default=""):
    return [v.strip() for v in os.environ.get(name, default).split(",") if v.strip()]


# --------------------------------------------------------------------------
# Core security settings
# --------------------------------------------------------------------------
DEBUG = env_bool("DJANGO_DEBUG", True)

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if DEBUG:
        # Local development only. Never use this key on a real server.
        SECRET_KEY = "django-insecure-novamart-local-development-key-do-not-use-in-production"
    else:
        raise ImproperlyConfigured("Set DJANGO_SECRET_KEY when DJANGO_DEBUG is False.")

ALLOWED_HOSTS = env_list(
    "DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]" if DEBUG else ""
)
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

# Demo accounts (10 customers + admin) may only be created when this is True.
ALLOW_DEMO_ACCOUNTS = env_bool("NOVAMART_ALLOW_DEMO_ACCOUNTS", DEBUG)

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", True)
    SECURE_HSTS_SECONDS = int(os.environ.get("DJANGO_HSTS_SECONDS", "0"))
    SECURE_CONTENT_TYPE_NOSNIFF = True

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14  # "Remember me" lasts 14 days
X_FRAME_OPTIONS = "DENY"


# --------------------------------------------------------------------------
# Applications
# --------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # NovaMart apps
    "accounts",
    "catalog",
    "cart",
    "orders",
    "dashboard",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "novamart_project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "catalog.context_processors.storefront",
            ],
        },
    },
]

WSGI_APPLICATION = "novamart_project.wsgi.application"
ASGI_APPLICATION = "novamart_project.asgi.application"


# --------------------------------------------------------------------------
# Database: SQLite for the prototype. PostgreSQL is optional (see README).
# --------------------------------------------------------------------------
if os.environ.get("DB_ENGINE", "").lower() in {"postgres", "postgresql"}:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("DB_NAME", "novamart"),
            "USER": os.environ.get("DB_USER", "novamart"),
            "PASSWORD": os.environ.get("DB_PASSWORD", ""),
            "HOST": os.environ.get("DB_HOST", "127.0.0.1"),
            "PORT": os.environ.get("DB_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "novamart.sqlite3",
        }
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# --------------------------------------------------------------------------
# Authentication
# --------------------------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "catalog:home"
LOGOUT_REDIRECT_URL = "accounts:login"

import sys  # noqa: E402

if "test" in sys.argv:
    # Much faster than PBKDF2 and only used by the automated tests.
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# --------------------------------------------------------------------------
# Internationalisation
# --------------------------------------------------------------------------
LANGUAGE_CODE = "en-in"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True


# --------------------------------------------------------------------------
# Static and media files
# --------------------------------------------------------------------------
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"  # used by `collectstatic` in production

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# Uploads
MAX_IMAGE_UPLOAD_BYTES = 3 * 1024 * 1024  # 3 MB
DATA_UPLOAD_MAX_NUMBER_FILES = 20
FILE_UPLOAD_PERMISSIONS = 0o644


# --------------------------------------------------------------------------
# Store rules (money is always Decimal, never float)
# --------------------------------------------------------------------------
CURRENCY_SYMBOL = "\u20b9"  # Indian rupee sign
DELIVERY_FEE = Decimal(os.environ.get("NOVAMART_DELIVERY_FEE", "49"))
FREE_DELIVERY_THRESHOLD = Decimal(os.environ.get("NOVAMART_FREE_DELIVERY_THRESHOLD", "999"))
LOW_STOCK_THRESHOLD = 5
MAX_CART_QUANTITY_PER_ITEM = 20
