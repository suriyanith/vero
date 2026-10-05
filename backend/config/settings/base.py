"""Base settings shared by every environment.

All configuration comes from environment variables (see the repository's
`.env.example`), parsed with django-environ so a bad value fails at startup
with a clear message rather than deep inside a request.
"""

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # backend/
REPO_ROOT = BASE_DIR.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    LOG_LEVEL=(str, "INFO"),
    VERO_LLM_MODE=(str, "fake"),
    VERO_LLM_MAX_RPM=(int, 10),
    VERO_LLM_TIMEOUT_SECONDS=(int, 60),
    VERO_LLM_MAX_OUTPUT_TOKENS=(int, 8192),
    VERO_RETRIEVAL_TOP_K=(int, 10),
    VERO_MAX_NOTE_CHARS=(int, 20000),
    VERO_MAX_BATCH_FILES=(int, 25),
)

# A committed .env never exists; this reads the developer's local copy.
environ.Env.read_env(REPO_ROOT / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY", default="change-me-dev-only")
DEBUG = env("DJANGO_DEBUG")
ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "ninja",  # for the export_openapi_schema management command
    "django_tasks_db",
    "apps.accounts",
    "apps.reference",
    "apps.llm",
    "apps.notes",
    "apps.runs",
    "apps.review",
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

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": env.db("DATABASE_URL", default="postgres://vero:vero@localhost:5432/vero"),
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Background tasks: jobs live in Postgres, executed by `manage.py db_worker`.
TASKS = {
    "default": {
        "BACKEND": "django_tasks_db.DatabaseBackend",
        "QUEUES": ["default"],
    },
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Logs carry IDs, step names, durations, and error codes — never note text,
# prompts, or AI responses (see the privacy rules in the project plan).
LOG_LEVEL = env("LOG_LEVEL")
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {
            "format": "{asctime} {levelname} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
    },
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
}

# Vero settings (Section 21 of the plan). Thresholds live here, not in code.
GEMINI_API_KEY = env("GEMINI_API_KEY", default="")
GEMINI_MODEL = env("GEMINI_MODEL", default="")
VERO_LLM_MODE = env("VERO_LLM_MODE")
VERO_LLM_MAX_RPM = env("VERO_LLM_MAX_RPM")
VERO_LLM_TIMEOUT_SECONDS = env("VERO_LLM_TIMEOUT_SECONDS")
VERO_LLM_MAX_OUTPUT_TOKENS = env("VERO_LLM_MAX_OUTPUT_TOKENS")
VERO_RETRIEVAL_TOP_K = env("VERO_RETRIEVAL_TOP_K")
VERO_MAX_NOTE_CHARS = env("VERO_MAX_NOTE_CHARS")
VERO_MAX_BATCH_FILES = env("VERO_MAX_BATCH_FILES")
