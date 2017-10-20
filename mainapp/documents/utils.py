# Name of the Elasticsearch index
from django.conf import settings
from django_elasticsearch_dsl import Index, DEDField, Integer
from elasticsearch_dsl import analyzer, token_filter


class RelatedToValueList(DEDField, Integer):
    def get_value_from_instance(self, data):
        return [obj.id for obj in super().get_value_from_instance(data)]


mainIndex = Index(settings.ELASTICSEARCH_INDEX)
# See Elasticsearch Indices API reference for available settings
mainIndex.settings(
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
mainIndex.analyzer(autocomplete_analyzer)
