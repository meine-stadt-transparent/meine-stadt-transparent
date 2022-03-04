import json
import logging
import os
import subprocess
import warnings

from importlib.util import find_spec
from logging import Filter, LogRecord
from subprocess import CalledProcessError
from typing import Dict, Union, Optional
from pathlib import Path

import sentry_sdk
from sentry_sdk import configure_scope
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.logging import ignore_logger

from meine_stadt_transparent.settings.env import env, TESTING
from meine_stadt_transparent.settings.nested import (
    INSTALLED_APPS,
    MIDDLEWARE,
    Q_CLUSTER,
)
from meine_stadt_transparent.settings.env import *  # noqa F403
from meine_stadt_transparent.settings.nested import *  # noqa F403
from meine_stadt_transparent.settings.security import *  # noqa F403

# Mute irrelevant warnings
warnings.filterwarnings("ignore", message="`django-leaflet` is not available.")
# This comes from PGPy with enigmail keys
warnings.filterwarnings(
    "ignore", message=".*does not have the required usage flag EncryptStorage.*"
)

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REAL_HOST = env.str("REAL_HOST")
PRODUCT_NAME = env.str("PRODUCT_NAME", "Meine Stadt Transparent")
SITE_NAME = env.str("SITE_NAME", PRODUCT_NAME)
ABSOLUTE_URI_BASE = env.str("ABSOLUTE_URI_BASE", "https://" + REAL_HOST)

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.11/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env.str("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool("DEBUG", default=False)

ALLOWED_HOSTS = [REAL_HOST, "127.0.0.1", "localhost"]

ROOT_URLCONF = "meine_stadt_transparent.urls"

WSGI_APPLICATION = "meine_stadt_transparent.wsgi.application"

# forcing request.build_absolute_uri to return https
os.environ["HTTPS"] = "on"

MAIL_PROVIDER = env.str("MAIL_PROVIDER", "smtp").lower()
if MAIL_PROVIDER != "smtp":
    ANYMAIL = json.loads(env.str("ANYMAIL"))
    # TODO: Validation of MAIL_PROVIDER
    EMAIL_BACKEND = f"anymail.backends.{MAIL_PROVIDER}.EmailBackend"
elif "EMAIL_URL" in env:
    # If EMAIL_URL is not configured, django's SMTP defaults will be used
    EMAIL_CONFIG = env.email_url("EMAIL_URL")
    vars().update(EMAIL_CONFIG)

EMAIL_FROM = env.str("EMAIL_FROM", "info@" + REAL_HOST)
EMAIL_FROM_NAME = env.str("EMAIL_FROM_NAME", SITE_NAME)
# required for django-allauth. See https://github.com/pennersr/django-allauth/blob/0.41.0/allauth/account/adapter.py#L95
DEFAULT_FROM_EMAIL = f"{EMAIL_FROM_NAME} <{EMAIL_FROM}>"

# Encrypted email are currently plaintext only (html is just rendered as plaintext in thunderbird),
# which is why this feature is disabled by default
ENABLE_PGP = env.bool("ENABLE_PGP", False)
# The pgp keyservevr, following the sks protocol
SKS_KEYSERVER = env.str("SKS_KEYSERVER", "gpg.mozilla.org")

# Database
# https://docs.djangoproject.com/en/1.11/ref/settings/#databases

DATABASES = {"default": env.db()}
# https://stackoverflow.com/a/45233653/3549270
SILENCED_SYSTEM_CHECKS = ["mysql.E001"]
# https://docs.djangoproject.com/en/3.2/releases/3.2/#customizing-type-of-auto-created-primary-keys
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

# Internationalization
# https://docs.djangoproject.com/en/1.11/topics/i18n/

LANGUAGE_CODE = env.str("LANGUAGE_CODE", "de-de")

TIME_ZONE = env.str("TIME_ZONE", "Europe/Berlin")

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Authentication

ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_EMAIL_REQUIRED = True
LOGIN_REDIRECT_URL = "/profile/"
ACCOUNT_DEFAULT_HTTP_PROTOCOL = "https"
ACCOUNT_SIGNUP_PASSWORD_ENTER_TWICE = False
ACCOUNT_AUTHENTICATION_METHOD = "email"
ACCOUNT_ADAPTER = "mainapp.account_adapter.AccountAdapter"
SOCIALACCOUNT_EMAIL_VERIFICATION = False
SOCIALACCOUNT_QUERY_EMAIL = True
ACCOUNT_MANAGEMENT_VISIBLE = env.bool("ACCOUNT_MANAGEMENT_VISIBLE", True)
# Needed by allauth
SITE_ID = 1

# Password validation
# https://docs.djangoproject.com/en/1.11/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTHENTICATION_BACKENDS = (
    # Needed to login by username in Django admin, regardless of `allauth`
    "django.contrib.auth.backends.ModelBackend",
    # `allauth` specific authentication methods, such as login by e-mail
    "allauth.account.auth_backends.AuthenticationBackend",
)

SOCIALACCOUNT_USE_FACEBOOK = env.bool("SOCIALACCOUNT_USE_FACEBOOK", False)
SOCIALACCOUNT_USE_TWITTER = env.bool("SOCIALACCOUNT_USE_TWITTER", False)

SOCIALACCOUNT_PROVIDERS = {}
if SOCIALACCOUNT_USE_FACEBOOK:
    SOCIALACCOUNT_PROVIDERS["facebook"] = {
        "EXCHANGE_TOKEN": True,
        "VERIFIED_EMAIL": False,
        "APP": {
            "client_id": env.str("FACEBOOK_CLIENT_ID"),
            "secret": env.str("FACEBOOK_SECRET_KEY"),
        },
    }
    INSTALLED_APPS.append("allauth.socialaccount.providers.facebook")

if SOCIALACCOUNT_USE_TWITTER:
    SOCIALACCOUNT_PROVIDERS["twitter"] = {
        "APP": {
            "client_id": env.str("TWITTER_CLIENT_ID"),
            "secret": env.str("TWITTER_SECRET_KEY"),
        }
    }
    INSTALLED_APPS.append("allauth.socialaccount.providers.twitter")

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.11/howto/static-files/

STATIC_URL = "/static/"
STATIC_ROOT = env.str("STATIC_ROOT", os.path.join(BASE_DIR, "static/"))

STATICFILES_DIRS = (
    os.path.join(BASE_DIR, "mainapp/assets"),
    os.path.join(BASE_DIR, "node_modules/pdfjs-dist/viewer"),  # See desgin.md
)

MINIO_PREFIX = env.str("MINIO_PREFIX", "meine-stadt-transparent-")
MINIO_ACCESS_KEY = env.str("MINIO_ACCESS_KEY", "meinestadttransparent")
MINIO_SECRET_KEY = env.str("MINIO_SECRET_KEY", "meinestadttransparent")
MINIO_REGION = env.str("MINIO_REGION", "us-east-1")
MINIO_HOST = env.str("MINIO_HOST", "localhost:9000")
MINIO_SECURE = env.bool("MINIO_SECURE", False)

MINIO_REDIRECT = env.bool("MINIO_REDIRECT", False)
MINIO_PUBLIC_HOST = env.str("MINIO_PUBLIC_HOST", None)
MINIO_PUBLIC_SECURE = env.bool("MINIO_PUBLIC_SECURE", True)

SCHEDULES_ENABLED = env.bool("SCHEDULES_ENABLED", False)

# When webpack compiles, it replaces the stats file contents with a compiling placeholder.
# If debug is False and the stats file is in the project root, this leads to a WebpackLoaderBadStatsError.
# So we place the file besides the assets, so it will be copied over by collectstatic
# only after the compilation finished, so that django only ever sees a finished stats file
if DEBUG or TESTING:
    webpack_stats = "mainapp/assets/bundles/webpack-stats.json"
else:
    webpack_stats = os.path.join(STATIC_ROOT, "bundles", "webpack-stats.json")

WEBPACK_LOADER = {
    "DEFAULT": {"BUNDLE_DIR_NAME": "bundles/", "STATS_FILE": webpack_stats}
}

# Elastic
ELASTICSEARCH_ENABLED = env.bool("ELASTICSEARCH_ENABLED", True)

if ELASTICSEARCH_ENABLED and "django_elasticsearch_dsl" not in INSTALLED_APPS:
    if "django_elasticsearch_dsl" not in INSTALLED_APPS:
        INSTALLED_APPS.append("django_elasticsearch_dsl")

ELASTICSEARCH_URL = env.str("ELASTICSEARCH_URL", "localhost:9200")

ELASTICSEARCH_DSL = {
    "default": {
        "hosts": ELASTICSEARCH_URL,
        "timeout": env.int("ELASTICSEARCH_TIMEOUT", 10),
        "verify_certs": env.bool("ELASTICSEARCH_VERIFY_CERTS", True),
    }
}

ELASTICSEARCH_PREFIX = env.str("ELASTICSEARCH_PREFIX", "meine-stadt-transparent")
if not ELASTICSEARCH_PREFIX.islower():
    raise ValueError("ELASTICSEARCH_PREFIX must be lowercase")

# Language use for stemming, stop words, etc.
ELASTICSEARCH_LANG = env.str("ELASTICSEARCH_LANG", "german")
ELASTICSEARCH_QUERYSET_PAGINATION = env.int("ELASTICSEARCH_QUERYSET_PAGINATION", 50)

# Valid values for GEOEXTRACT_ENGINE: Nominatim, Opencage, Mapbox
GEOEXTRACT_ENGINE = env.str("GEOEXTRACT_ENGINE", "Nominatim").lower()
if GEOEXTRACT_ENGINE not in ["nominatim", "mapbox", "opencage"]:
    raise ValueError("Unknown Geocoder: " + GEOEXTRACT_ENGINE)

if GEOEXTRACT_ENGINE == "opencage":
    OPENCAGE_KEY = env.str("OPENCAGE_KEY")

NOMINATIM_URL = env.str("NOMINATIM_URL", "https://nominatim.openstreetmap.org")

# Settings for Geo-Extraction
GEOEXTRACT_LANGUAGE = env.str("GEOEXTRACT_LANGUAGE", LANGUAGE_CODE.split("-")[0])

GEOEXTRACT_SEARCH_COUNTRY = env.str("GEOEXTRACT_SEARCH_COUNTRY", "Deutschland")
GEOEXTRACT_SEARCH_CITY = env.str("GEOEXTRACT_SEARCH_CITY", None)

SUBPROCESS_MAX_RAM = env.int("SUBPROCESS_MAX_RAM", 1024 * 1024 * 1024)  # 1 GB

CITY_AFFIXES = env.list(
    "CITY_AFFIXES",
    default=[
        "Stadt",
        "Landeshauptstadt",
        "Gemeinde",
        "Kreisverwaltung",
        "Landkreis",
        "Kreis",
    ],
)

DISTRICT_REGEX = env.str("DISTRICT_REGEX", r"(^| )kreis|kreis( |$)")

TEXT_CHUNK_SIZE = env.int("TEXT_CHUNK_SIZE", 1024 * 1024)

OCR_AZURE_KEY = env.str("OCR_AZURE_KEY", None)
OCR_AZURE_LANGUAGE = env.str("OCR_AZURE_LANGUAGE", "de")
OCR_AZURE_API = env.str(
    "OCR_AZURE_API", "https://westcentralus.api.cognitive.microsoft.com"
)

# Configuration regarding the city of choice
SITE_DEFAULT_BODY = env.int("SITE_DEFAULT_BODY", 1)
SITE_DEFAULT_ORGANIZATION = env.int("SITE_DEFAULT_ORGANIZATION", 1)

# Possible values: OSM, Mapbox
MAP_TILES_PROVIDER = env.str("MAP_TILES_PROVIDER", "OSM")
MAP_TILES_URL = env.str("MAP_TILES_URL", None)
MAPBOX_TOKEN = env.str("MAPBOX_TOKEN", None)

CUSTOM_IMPORT_HOOKS = env.str("CUSTOM_IMPORT_HOOKS", None)

PARLIAMENTARY_GROUPS_TYPE = (1, "parliamentary group")
COMMITTEE_TYPE = (2, "committee")
DEPARTMENT_TYPE = (3, "department")
ORGANIZATION_ORDER = env.list(
    "ORGANIZATION_ORDER",
    int,
    [PARLIAMENTARY_GROUPS_TYPE, COMMITTEE_TYPE, DEPARTMENT_TYPE],
)

# Possible values: month, listYear, listMonth, listDay, basicWeek, basicDay, agendaWeek, agendaDay
CALENDAR_DEFAULT_VIEW = env.str("CALENDAR_DEFAULT_VIEW", "listMonth")
CALENDAR_HIDE_WEEKENDS = env.bool("CALENDAR_HIDE_WEEKENDS", True)
CALENDAR_MIN_TIME = env.bool("CALENDAR_MIN_TIME", "08:00:00")
CALENDAR_MAX_TIME = env.bool("CALENDAR_MAX_TIME", "21:00:00")

# Configuration regarding Search Engine Optimization
SITE_SEO_NOINDEX = env.bool("SITE_SEO_NOINDEX", False)

# Include the plain text of PDFs next to the PDF viewer, visible only for Screenreaders
# On by default to improve accessibility, deactivatable in case there are legal concerns
EMBED_PARSED_TEXT_FOR_SCREENREADERS = env.bool(
    "EMBED_PARSED_TEXT_FOR_SCREENREADERS", True
)

SEARCH_PAGINATION_LENGTH = 20

SENTRY_DSN = env.str("SENTRY_DSN", None)
SENTRY_ENVIRONMENT = env.str(
    "SENTRY_ENVIRONMENT", "development" if DEBUG else "production"
)

# SENTRY_HEADER_ENDPOINT is defined in security.py

if SENTRY_DSN:
    if os.environ.get("DOCKER_GIT_SHA"):
        version = os.environ.get("DOCKER_GIT_SHA")
    else:
        try:
            version = (
                subprocess.check_output(
                    ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL
                )
                .strip()
                .decode()
            )
        except CalledProcessError:
            # Note however that logging isn't configured at this point
            import importlib.metadata

            try:
                version = importlib.metadata.version("meine_stadt_transparent")
            except importlib.metadata.PackageNotFoundError:
                version = "unknown"
    release = "meine-stadt-transparent@" + version

    sentry_sdk.init(
        SENTRY_DSN,
        integrations=[DjangoIntegration()],
        release=release,
        ignore_errors=[KeyboardInterrupt],
        environment=SENTRY_ENVIRONMENT,
        traces_sample_rate=env.int("SENTRY_TRACES_SAMPLE_RATE", 0.05),
    )
    ignore_logger("django.security.DisallowedHost")
    with configure_scope() as scope:
        scope.set_tag("real_host", REAL_HOST)

    Q_CLUSTER["error_reporter"] = {"sentry": {"dsn": SENTRY_DSN}}

DJANGO_LOG_LEVEL = env.str("DJANGO_LOG_LEVEL", None)
MAINAPP_LOG_LEVEL = env.str("MAINAPP_LOG_LEVEL", None)
IMPORTER_LOG_LEVEL = env.str("IMPORTER_LOG_LEVEL", None)

# Anchoring this in this file is required for running tests from other directories
LOG_DIRECTORY = env.str(
    "LOG_DIRECTORY", Path(__file__).parent.parent.parent.joinpath("log")
)
NO_LOG_FILES = env.bool("NO_LOG_FILES", False)


def make_handler(
    log_name: str, level: Optional[str] = None
) -> Dict[str, Union[str, int]]:
    if NO_LOG_FILES:
        return {"class": "logging.NullHandler"}

    handler = {
        "class": "logging.handlers.RotatingFileHandler",
        "filename": os.path.join(LOG_DIRECTORY, log_name),
        "formatter": "extended",
        "maxBytes": 8 * 1024 * 1024,
        "backupCount": 2 if not DEBUG else 0,
    }

    if level:
        handler["level"] = level

    return handler


class WarningsFilter(Filter):
    """
    Removes bogus warnings.

    We handle the warnings through the logging module so they get properly
    tracked in the log files, but this also means we can't use the warning
    module to filter them.
    """

    def filter(self, record: LogRecord) -> bool:
        irrelevant = (
            "Xref table not zero-indexed. ID numbers for objects will be corrected."
        )
        if irrelevant in record.getMessage():
            return False
        return True


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "extended": {"format": "%(asctime)s %(levelname)-8s %(name)-12s %(message)s"},
        "with_time": {"format": "%(asctime)s %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "with_time"},
        "django": make_handler("django.log"),
        "django-error": make_handler("django-error.log", "WARNING"),
        "importer": make_handler("importer.log"),
        "importer-error": make_handler("importer-error.log", "WARNING"),
    },
    "filters": {"warnings-filters": {"()": WarningsFilter}},
    "loggers": {
        "mainapp": {
            "handlers": ["console", "django-error", "django"],
            "level": MAINAPP_LOG_LEVEL or "INFO",
            "propagate": False,
        },
        "importer": {
            "handlers": ["console", "importer-error", "importer"],
            "level": IMPORTER_LOG_LEVEL or "INFO",
            "propagate": False,
        },
        "django": {
            "level": DJANGO_LOG_LEVEL or "WARNING",
            "handlers": ["console", "django-error", "django"],
            "propagate": False,
        },
        "django-q": {
            "level": DJANGO_LOG_LEVEL or "WARNING",
            "handlers": ["console", "django-error", "django"],
            "propagate": False,
        },
        "py.warnings": {
            "level": "WARNING",
            "handlers": ["console", "django-error", "django"],
            "propagate": False,
            "filters": ["warnings-filters"],
        },
    },
}

LOGGING.update(env.json("LOGGING", {}))

# Not sure what is going on, but this make caplog work
if TESTING:
    LOGGING["loggers"] = {}

logging.captureWarnings(True)

OPARL_INDEX = env.str("OPARL_INDEX", "https://mirror.oparl.org/bodies")

TEMPLATE_META = {
    "logo_name": env.str("TEMPLATE_LOGO_NAME", "MST"),
    "site_name": SITE_NAME,
    "prototype_fund": "https://prototypefund.de/project/open-source-ratsinformationssystem",
    "github": "https://github.com/meine-stadt-transparent/meine-stadt-transparent",
    "contact_mail": EMAIL_FROM,
    "main_css": env.str("TEMPLATE_MAIN_CSS", "mainapp"),
    "location_limit_lng": 42,
    "location_limit_lat": 23,
    "sks_keyserver": SKS_KEYSERVER,
    "enable_pgp": ENABLE_PGP,
    "sentry_dsn": SENTRY_DSN,
}

FILE_DISCLAIMER = env.str("FILE_DISCLAIMER", None)
FILE_DISCLAIMER_URL = env.str("FILE_DISCLAIMER_URL", None)

SETTINGS_EXPORT = [
    "TEMPLATE_META",
    "FILE_DISCLAIMER",
    "FILE_DISCLAIMER_URL",
    "ABSOLUTE_URI_BASE",
    "ACCOUNT_MANAGEMENT_VISIBLE",
]

# Mandatory but afaik unsused value
WAGTAIL_SITE_NAME = SITE_NAME

# Workaround to avoid filling up disk space
PROXY_ONLY_TEMPLATE = env.str("PROXY_ONLY_TEMPLATE", None)

DEBUG_TOOLBAR_ACTIVE = False
DEBUG_TESTING = env.bool("DEBUG_TESTING", False)

if DEBUG and not TESTING:
    # For some reason pycharm needs the latter condition (might just be misconfiguration)
    if find_spec("debug_toolbar"):
        # Debug Toolbar
        if "debug_toolbar" not in INSTALLED_APPS:
            INSTALLED_APPS.append("debug_toolbar")
            MIDDLEWARE.append("debug_toolbar.middleware.DebugToolbarMiddleware")
        DEBUG_TOOLBAR_CONFIG = {"JQUERY_URL": ""}
        DEBUG_TOOLBAR_ACTIVE = True
    else:
        logger = logging.getLogger(__name__)
        logger.warning(
            "This is running in DEBUG mode, however the Django debug toolbar is not installed."
        )
        DEBUG_TOOLBAR_ACTIVE = False

    if env.bool("DEBUG_SHOW_SQL", False):
        LOGGING["loggers"]["django.db.backends"] = {
            "level": "DEBUG",
            "handlers": ["console"],
            "propagate": False,
        }

    INTERNAL_IPS = ["127.0.0.1"]

    # Make debugging css styles in firefox easier
    DEBUG_STYLES = env.bool("DEBUG_STYLES", False)
    if DEBUG_STYLES:
        CSP_STYLE_SRC = ("'self'", "'unsafe-inline'")

    # Just an additional host you might want
    ALLOWED_HOSTS.append("meinestadttransparent.local")
