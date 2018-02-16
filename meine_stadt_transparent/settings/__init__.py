import logging
import os
import warnings

from meine_stadt_transparent.settings.env import *
from meine_stadt_transparent.settings.nested import *
from meine_stadt_transparent.settings.security import *

# Mute an irrelevant warning
warnings.filterwarnings("ignore", message="`django-leaflet` is not available.")

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REAL_HOST = env.str('REAL_HOST')
PRODUCT_NAME = "Meine Stadt Transparent"
ABSOLUTE_URI_BASE = env.str('ABSOLUTE_URI_BASE', 'https://' + REAL_HOST)

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.11/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env.str('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool('DEBUG', default=False)

ALLOWED_HOSTS = [
    REAL_HOST,
    '127.0.0.1',
    'localhost'
]


ROOT_URLCONF = 'meine_stadt_transparent.urls'

WSGI_APPLICATION = 'meine_stadt_transparent.wsgi.application'

# forcing request.build_absolute_uri to return https
os.environ['HTTPS'] = "on"

ANYMAIL = {
    "MAILJET_API_KEY": env.str('MAILJET_API_KEY'),
    "MAILJET_SECRET_KEY": env.str('MAILJET_SECRET_KEY')
}
EMAIL_BACKEND = "anymail.backends.mailjet.EmailBackend"
DEFAULT_FROM_EMAIL = env.str('DEFAULT_FROM_EMAIL', "info@" + REAL_HOST)
DEFAULT_FROM_EMAIL_NAME = env.str('DEFAULT_FROM_EMAIL_NAME', PRODUCT_NAME)

# Database
# https://docs.djangoproject.com/en/1.11/ref/settings/#databases

DATABASES = {
    'default': env.db()
}

# Internationalization
# https://docs.djangoproject.com/en/1.11/topics/i18n/

LANGUAGE_CODE = env.str('LANGUAGE_CODE', 'de-de')

TIME_ZONE = env.str('TIME_ZONE', 'Europe/Berlin')

USE_I18N = True

USE_L10N = True

USE_TZ = True

DATETIME_FORMAT = "%d.%m.%Y, %H:%M"
TIME_FORMAT = "%H:%M"

# Authentication

ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_EMAIL_REQUIRED = True
LOGIN_REDIRECT_URL = "/profile/"
ACCOUNT_EMAIL_CONFIRMATION_ANONYMOUS_REDIRECT_URL = True
ACCOUNT_DEFAULT_HTTP_PROTOCOL = "https"
ACCOUNT_SIGNUP_PASSWORD_ENTER_TWICE = False
ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_ADAPTER = 'mainapp.account_adapter.AccountAdapter'
SOCIALACCOUNT_EMAIL_VERIFICATION = False
SOCIALACCOUNT_QUERY_EMAIL = True
# Needed by allauth
SITE_ID = 1

# Password validation
# https://docs.djangoproject.com/en/1.11/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

AUTHENTICATION_BACKENDS = (
    # Needed to login by username in Django admin, regardless of `allauth`
    'django.contrib.auth.backends.ModelBackend',

    # `allauth` specific authentication methods, such as login by e-mail
    'allauth.account.auth_backends.AuthenticationBackend',
)

SOCIALACCOUNT_USE_FACEBOOK = env.bool('SOCIALACCOUNT_USE_FACEBOOK', False)
SOCIALACCOUNT_USE_TWITTER = env.bool('SOCIALACCOUNT_USE_TWITTER', False)

SOCIALACCOUNT_PROVIDERS = {}
if SOCIALACCOUNT_USE_FACEBOOK:
    SOCIALACCOUNT_PROVIDERS['facebook'] = {
        'EXCHANGE_TOKEN': True,
        'VERIFIED_EMAIL': False,
        'CLIENT_ID': env.str('FACEBOOK_CLIENT_ID'),
        'SECRET_KEY': env.str('FACEBOOK_SECRET_KEY'),
    }
    INSTALLED_APPS.append('allauth.socialaccount.providers.facebook')

if SOCIALACCOUNT_USE_TWITTER:
    SOCIALACCOUNT_PROVIDERS['twitter'] = {
        'CLIENT_ID': env.str('TWITTER_CLIENT_ID'),
        'SECRET_KEY': env.str('TWITTER_SECRET_KEY'),
    }
    INSTALLED_APPS.append('allauth.socialaccount.providers.twitter')

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.11/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = env.str('STATIC_ROOT', os.path.join(BASE_DIR, 'static/'))

STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'mainapp/assets'),
)

MEDIA_ROOT = env.str('MEDIA_ROOT', './storage/files/')
CACHE_ROOT = env.str('CACHE_ROOT', './storage/cache/')

WEBPACK_LOADER = {
    'DEFAULT': {
        'BUNDLE_DIR_NAME': 'bundles/',
        'STATS_FILE': os.path.join(BASE_DIR, 'webpack-stats.json'),
    }
}

# Elastic
USE_ELASTICSEARCH = env.bool('USE_ELASTICSEARCH', True)

if USE_ELASTICSEARCH:
    INSTALLED_APPS.append('django_elasticsearch_dsl')

ELASTICSEARCH_URL_PRIVATE = env.str('ELASTICSEARCH_URL_PRIVATE')

ELASTICSEARCH_DSL = {
    'default': {
        'hosts': ELASTICSEARCH_URL_PRIVATE
    },
}

ELASTICSEARCH_INDEX = env.str('ELASTICSEARCH_INDEX', 'meine_stadt_transparent_documents')

# Valid values for GEOEXTRACT_ENGINE: Nominatim, Opencagedata
GEOEXTRACT_ENGINE = env.str('GEOEXTRACT_ENGINE', 'Nominatim')
if GEOEXTRACT_ENGINE.lower() not in ['nominatim', 'opencagedata']:
    raise ValueError("Unknown Geocoder: " + GEOEXTRACT_ENGINE)

if GEOEXTRACT_ENGINE.lower() == 'opencagedata':
    OPENCAGEDATA_KEY = env.str('OPENCAGEDATA_KEY', None)

# Settings for Geo-Extraction
# @TODO Clarify if we want to distinguish other cities, and what would be the best way to get a
# good list
# of relevant city names
GEOEXTRACT_KNOWN_CITIES = ['München', 'Berlin', 'Köln', 'Hamburg', 'Karlsruhe']
GEOEXTRACT_SEARCH_COUNTRY = 'Deutschland'
GEOEXTRACT_DEFAULT_CITY = env.str('GEOEXTRACT_DEFAULT_CITY')
GEO_SEARCH_COUNTRY = env.str('GEO_SEARCH_COUNTRY', 'Deutschland')

# Configuration regarding the city of choice
SITE_GEO_LIMITS = env.json('SITE_GEO_LIMITS')
SITE_GEO_CENTER = env.json('SITE_GEO_CENTER')
SITE_GEO_INIT_ZOOM = env.int('SITE_GEO_INIT_ZOOM', 11)
SITE_DEFAULT_BODY = env.int('SITE_DEFAULT_BODY', 1)
SITE_DEFAULT_ORGANIZATION = env.int('SITE_DEFAULT_ORGANIZATION', 1)

SITE_MAPBOX_TILE_URL = env.str('SITE_MAPBOX_TILE_URL', None)
SITE_MAPBOX_ACCESS_TOKEN = env.str('SITE_MAPBOX_ACCESS_TOKEN')

CUSTOM_IMPORT_HOOKS = env.str('CUSTOM_IMPORT_HOOKS', None)

PARLIAMENTARY_GROUPS_TYPE = (1, "parliamentary group")
COMMITTEE_TYPE = (2, "committee")
DEPARTMENT_TYPE = (3, "department")
ORGANIZATION_TYPE_SORTING = env.list('ORGANIZATION_TYPE_SORTING', int,
                                     [PARLIAMENTARY_GROUPS_TYPE, COMMITTEE_TYPE, DEPARTMENT_TYPE])

# The documents of the last SITE_INDEX_DOCUMENT_DAY days will be shown on the home page
SITE_INDEX_DOCUMENT_DAY = env.int('SITE_INDEX_DOCUMENT_DAY', 7)

# Possible values: month, listYear, listMonth, listDay, basicWeek, basicDay, agendaWeek, agendaDay
CALENDAR_DEFAULT_VIEW = env.str('CALENDAR_DEFAULT_VIEW', 'listMonth')
CALENDAR_HIDE_WEEKENDS = env.bool('CALENDAR_HIDE_WEEKENDS', True)
CALENDAR_MIN_TIME = env.bool('CALENDAR_MIN_TIME', "08:00:00")
CALENDAR_MAX_TIME = env.bool('CALENDAR_MAX_TIME', "21:00:00")

# Configuration regarding Search Engine Optimization
SITE_SEO_NOINDEX = env.bool('SITE_SEO_NOINDEX', False)

SEARCH_PAGINATION_LENGTH = 20

DJANGO_LOG_LEVEL = env.str("DJANGO_LOG_LEVEL", None)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'extended': {
            'format': '%(asctime)s %(levelname)-8s %(name)-12s %(message)s',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
        'mainapp': {
            'class': 'logging.FileHandler',
            'filename': os.path.join(env.str("LOGGING_DIRECTORY", ""), 'mainapp.log'),
            'formatter': 'extended',
        },
        'importer': {
            'class': 'logging.FileHandler',
            'filename': os.path.join(env.str("LOGGING_DIRECTORY", ""), 'importer.log'),
            'formatter': 'extended',
        }
    },
    'loggers': {
        'mainapp': {
            'handlers': ['console', 'mainapp'],
            'level': DJANGO_LOG_LEVEL or 'INFO',
        },
        'mainapp.management.commands': {
            'level': DJANGO_LOG_LEVEL or 'DEBUG',
            'propagate': True,
        },
        'importer': {
            'handlers': ['console', 'importer'],
            'level': DJANGO_LOG_LEVEL or 'INFO',
            'propagate': True,
        },
    }
}

LOGGING.update(env.json("LOGGING", {}))

OPARL_ENDPOINTS_LIST = "https://dev.oparl.org/api/endpoints"

TEMPLATE_META = {
    "logo_name": env.str('TEMPLATE_LOGO_NAME', 'MST'),
    "product_name": PRODUCT_NAME,
    "prototype_fund": "https://prototypefund.de/project/open-source-ratsinformationssystem",
    "github": "https://github.com/meine-stadt-transparent/meine-stadt-transparent",
    "contact_mail": DEFAULT_FROM_EMAIL,
    "main_css": env.str('TEMPLATE_MAIN_CSS', "mainapp"),
    "location_limit_lng": 42,
    "location_limit_lat": 23,
}

FILE_DISCLAIMER = env.str("FILE_DISCLAIMER", None)
FILE_DISCLAIMER_URL = env.str("FILE_DISCLAIMER_URL", None)

SETTINGS_EXPORT = [
    'TEMPLATE_META',
    'FILE_DISCLAIMER',
    'FILE_DISCLAIMER_URL',
]

DEBUG_TOOLBAR_ACTIVE = False
DEBUG_TESTING = env.bool("DEBUG_TESTING", False)

if DEBUG and not TESTING:
    import pip

    installed_packages = [package.project_name for package in pip.get_installed_distributions()]
    if "django-debug-toolbar" in installed_packages:
        # Debug Toolbar
        INSTALLED_APPS.append('debug_toolbar')
        MIDDLEWARE.append('debug_toolbar.middleware.DebugToolbarMiddleware')
        DEBUG_TOOLBAR_CONFIG = {"JQUERY_URL": ""}
        DEBUG_TOOLBAR_ACTIVE = True
    else:
        logger = logging.getLogger(__name__)
        logger.warning('This is running in DEBUG mode, however the Django debug toolbar is not installed.')
        DEBUG_TOOLBAR_ACTIVE = False

    INTERNAL_IPS = [
        '127.0.0.1'
    ]

    # Make debugging css styles in firefox easier
    DEBUG_STYLES = env.bool("DEBUG_STYLES", False)
    if DEBUG_STYLES:
        CSP_STYLE_SRC = ("'self'", "'unsafe-inline'",)

    # Just an additional host you might want
    ALLOWED_HOSTS.append("meinestadttransparent.local")
