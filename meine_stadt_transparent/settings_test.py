"""
Settings environment for running tests
 - The host is fixed to meine-stadt-transparent.local
 - The database is sqlite
 - elasticsearch is disabled
"""

from .settings import *

REAL_HOST = "meine-stadt-transparent.local"

ALLOWED_HOSTS = [
    REAL_HOST,
    '127.0.0.1',
    'localhost'
]

# noinspection PyUnresolvedReferences
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

if USE_ELASTICSEARCH:
    INSTALLED_APPS.remove('elasticsearch_admin')
    INSTALLED_APPS.remove('django_elasticsearch_dsl')

USE_ELASTICSEARCH = False


