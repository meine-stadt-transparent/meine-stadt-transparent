OPENCAGEDATA_KEY = ''

# HTTP is used during development, as self-signed certificates seem to make some problems with urllib3
ELASTICSEARCH_URL_PRIVATE = 'http://elastic:changeme@opensourceris.local:80/elasticsearch/'
ELASTICSEARCH_URL_PUBLIC = 'https://opensourceris.local/elasticsearch/'

ELASTICSEARCH_DSL = {
    'default': {
        'hosts': ELASTICSEARCH_URL_PRIVATE
    },
}
