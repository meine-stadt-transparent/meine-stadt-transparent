"""
Settings environment for running tests
 - The host is fixed to meine-stadt-transparent.local
 - The database is sqlite
"""

from .settings import *

REAL_HOST = "meine-stadt-transparent.local"

ALLOWED_HOSTS = [
    REAL_HOST,
    '127.0.0.1',
    'localhost'
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}