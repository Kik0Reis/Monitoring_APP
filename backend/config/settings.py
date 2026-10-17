# django settings of the backend

import os
from pathlib import Path

# base folder of the backend
BASE_DIR = Path(__file__).resolve().parent.parent


# main settings, read from environment variables

SECRET_KEY = os.getenv("SECRET_KEY")

DEBUG = os.getenv("DEBUG") == "True"

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "").split(",")


# mqtt broker settings, read from the environment so the credentials are not in the code

MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "")
MQTT_KEEPALIVE = int(os.getenv("MQTT_KEEPALIVE", "60"))
MQTT_TLS = os.getenv("MQTT_TLS", "True") == "True"


# data retention: how long each kind of record is kept
# heartbeats are deleted after this many days, the cleanup runs every cleanup interval

HEARTBEAT_RETENTION_DAYS = int(os.getenv("HEARTBEAT_RETENTION_DAYS", "14"))
HEARTBEAT_CLEANUP_INTERVAL_HOURS = int(
    os.getenv("HEARTBEAT_CLEANUP_INTERVAL_HOURS", "24")
)

# days a resolved alert is kept before it is deleted, active alerts are never deleted
ALERT_RETENTION_DAYS = int(os.getenv("ALERT_RETENTION_DAYS", "30"))

# hours without a new mqtt report before an error alert is resolved by the cleanup job
ALERT_STALE_HOURS = int(os.getenv("ALERT_STALE_HOURS", "24"))

# days a detection is kept before it is deleted
DETECTION_RETENTION_DAYS = int(os.getenv("DETECTION_RETENTION_DAYS", "10"))

# hours an error alert or a detection stays visible in the interface, the row is kept until its retention days
ALERT_VISIBLE_HOURS = int(os.getenv("ALERT_VISIBLE_HOURS", "24"))
DETECTION_VISIBLE_HOURS = int(os.getenv("DETECTION_VISIBLE_HOURS", "24"))


# mqtt reconciliation: how often the subscription is renewed and how many seconds to wait for the answers

MQTT_RECONCILE_INTERVAL_MINUTES = int(
    os.getenv("MQTT_RECONCILE_INTERVAL_MINUTES", "30")
)
MQTT_RECONCILE_WINDOW_SECONDS = int(os.getenv("MQTT_RECONCILE_WINDOW_SECONDS", "15"))


# installed apps and middleware

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "django_filters",
    "corsheaders",
    "core",
    "cameras",
    "countries",
    "customers",
    "locations",
    "devices",
    "mqtt",
    "monitoring",
]


MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
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
            ]
        },
    }
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# database

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.getenv("SQLITE_PATH", str(BASE_DIR / "db.sqlite3")),
        "OPTIONS": {
            # wait this many seconds when the database is locked, three processes share the same sqlite file
            # wal mode is not used because it is not reliable between windows and docker
            "timeout": int(os.getenv("SQLITE_TIMEOUT_SECONDS", "20")),
        },
    }
}


# password validation

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# language and time zone

CORS_ALLOW_ALL_ORIGINS = True

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# static files

STATIC_URL = "static/"

# only used in production, whitenoise serves the files collected during the build
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}



REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 10,
}

# send the logs to the console so they show in docker

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "console": {"format": "{levelname} {asctime} {name} - {message}", "style": "{"}
    },
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "console"}},
    "loggers": {"mqtt": {"handlers": ["console"], "level": "INFO", "propagate": False}},
}
