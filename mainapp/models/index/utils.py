# Name of the Elasticsearch index
from django.conf import settings
from django_elasticsearch_dsl import Index
from elasticsearch_dsl import analyzer, token_filter

fileIndex = Index(settings.ELASTICSEARCH_INDEX)
# See Elasticsearch Indices API reference for available settings
fileIndex.settings(
    number_of_shards=1,
    number_of_replicas=0
)


autocomplete_filter = token_filter(
    "autocomplete_filter",
    "edge_ngram",
    min_gram=1,
    max_gram=20,
)

autocomplete_analyzer = analyzer(
    'autocomplete',
    tokenizer="standard",
    filter=["lowercase", autocomplete_filter],
)
fileIndex.analyzer(autocomplete_analyzer)
