import os
from pathlib import Path
from urllib.parse import urlparse

from celery.schedules import crontab
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")

SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-dev-only-change-me")

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]

if DEBUG:
    for dev_tunnel_host in (".trycloudflare.com",):
        if dev_tunnel_host not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(dev_tunnel_host)

_csrf_origins = os.getenv("CSRF_TRUSTED_ORIGINS", "").strip()
if _csrf_origins:
    CSRF_TRUSTED_ORIGINS = [
        origin.strip() for origin in _csrf_origins.split(",") if origin.strip()
    ]

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.core",
    "apps.bot",
    "apps.ai",
    "apps.memory",
]

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
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://my_agent:my_agent@localhost:5432/my_agent",
)
_db_url = urlparse(DATABASE_URL)

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": _db_url.path.lstrip("/") or "my_agent",
        "USER": _db_url.username or "my_agent",
        "PASSWORD": _db_url.password or "",
        "HOST": _db_url.hostname or "localhost",
        "PORT": str(_db_url.port or 5432),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_BEAT_SCHEDULER = "celery.beat:PersistentScheduler"

CELERY_BEAT_SCHEDULE = {
    "send-morning-briefing": {
        "task": "apps.memory.tasks.send_morning_briefing",
        "schedule": crontab(hour=7, minute=30),
    },
    "check-upcoming-events": {
        "task": "apps.memory.tasks.check_upcoming_events",
        "schedule": crontab(minute="*/15"),
    },
    "check-scheduled-reminders": {
        "task": "apps.memory.tasks.check_scheduled_reminders",
        "schedule": crontab(minute="*/1"),
    },
}

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_ALLOWED_USER_ID = os.getenv("TELEGRAM_ALLOWED_USER_ID", "")
TELEGRAM_PROXY_URL = os.getenv("TELEGRAM_PROXY_URL", "").strip()
TELEGRAM_BOOTSTRAP_RETRIES = int(os.getenv("TELEGRAM_BOOTSTRAP_RETRIES", "-1"))
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_LLM_MODEL = os.getenv("GROQ_LLM_MODEL", "openai/gpt-oss-120b")
GROQ_WHISPER_MODEL = os.getenv("GROQ_WHISPER_MODEL", "whisper-large-v3-turbo")
GEOFENCE_WEBHOOK_TOKEN = os.getenv("GEOFENCE_WEBHOOK_TOKEN", "")
PWA_API_TOKEN = os.getenv("PWA_API_TOKEN", "").strip()
PWA_API_TOKEN_PREVIOUS = os.getenv("PWA_API_TOKEN_PREVIOUS", "").strip()
PWA_PAIRING_TTL_SECONDS = int(os.getenv("PWA_PAIRING_TTL_SECONDS", "900"))
PWA_PUBLIC_BASE_URL = os.getenv("PWA_PUBLIC_BASE_URL", "").strip().rstrip("/")
PWA_WRITE_RATE_LIMIT_PER_MINUTE = int(os.getenv("PWA_WRITE_RATE_LIMIT_PER_MINUTE", "60"))
PWA_AUDIO_MAX_BYTES = int(os.getenv("PWA_AUDIO_MAX_BYTES", str(5 * 1024 * 1024)))
VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY", "").strip()
VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY", "").strip()
VAPID_ADMIN_EMAIL = os.getenv("VAPID_ADMIN_EMAIL", "mailto:admin@localhost").strip()
GEOFENCE_RATE_LIMIT_SECONDS = int(os.getenv("GEOFENCE_RATE_LIMIT_SECONDS", "120"))

# Lembrete de compromisso: ~EVENT_REMINDER_MINUTES_BEFORE (janela ± EVENT_REMINDER_WINDOW_MINUTES).
# Celery Beat consulta a cada 15 min — mantenha window ≥ metade do intervalo do beat.
EVENT_REMINDER_MINUTES_BEFORE = int(os.getenv("EVENT_REMINDER_MINUTES_BEFORE", "30"))
EVENT_REMINDER_WINDOW_MINUTES = int(os.getenv("EVENT_REMINDER_WINDOW_MINUTES", "8"))

TTS_ENABLED = os.getenv("TTS_ENABLED", "True").lower() in ("true", "1", "yes")
TTS_VOICE = os.getenv("TTS_VOICE", "pt-BR-AntonioNeural")
TTS_MAX_CHARS = int(os.getenv("TTS_MAX_CHARS", "900"))

TELEGRAM_CONNECT_TIMEOUT = float(os.getenv("TELEGRAM_CONNECT_TIMEOUT", "30"))
TELEGRAM_READ_TIMEOUT = float(os.getenv("TELEGRAM_READ_TIMEOUT", "60"))
TELEGRAM_WRITE_TIMEOUT = float(os.getenv("TELEGRAM_WRITE_TIMEOUT", "60"))
TELEGRAM_MEDIA_WRITE_TIMEOUT = float(os.getenv("TELEGRAM_MEDIA_WRITE_TIMEOUT", "180"))