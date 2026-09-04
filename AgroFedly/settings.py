from pathlib import Path
import os
import dj_database_url
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from the Annadata directory
env_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=env_path)

_raw_secret = (
    os.getenv("DJANGO_SECRET_KEY")
    or os.getenv("SECRET_KEY")
    or ""
).strip().strip('\'\"')
SECRET_KEY = _raw_secret or "django-insecure-feedora-super-secret-key-production-fallback-123456789"

DEBUG = os.getenv("DJANGO_DEBUG", "0") == "1"
ALLOWED_HOSTS = ["127.0.0.1", "localhost", "*"]
CSRF_TRUSTED_ORIGINS = [
    "https://*.vercel.app",
    "https://*.now.sh",
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "feedly",
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

ROOT_URLCONF = "AgroFedly.urls"

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
            ],
        },
    },
]

WSGI_APPLICATION = "AgroFedly.wsgi.application"

DATABASE_URL = (
    os.getenv("DATABASE_URL")
    or os.getenv("POSTGRES_URL")
    or os.getenv("POSTGRES_PRISMA_URL")
    or os.getenv("POSTGRES_URL_NON_POOLING")
    or os.getenv("DB_URL")
    or ""
).strip().strip("'\"")

if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=int(os.getenv("DJANGO_CONN_MAX_AGE", "0")),
            conn_health_checks=True,
        )
    }
else:
    db_path = BASE_DIR / "db.sqlite3"
    backup_db = BASE_DIR / "db.sqlite3.backup"
    if os.getenv("VERCEL"):
        tmp_db = Path("/tmp") / "db.sqlite3"
        if backup_db.exists() and not tmp_db.exists():
            import shutil
            shutil.copy2(backup_db, tmp_db)
        db_path = tmp_db
    elif not db_path.exists() and backup_db.exists():
        import shutil
        shutil.copy2(backup_db, db_path)

    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": db_path,
        }
    }

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "login"

WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "")
