from django_elasticsearch_dsl import DocType, Index, fields

from mainapp.models import Committee

# Name of the Elasticsearch index
fileIndex = Index('ris_files')
# See Elasticsearch Indices API reference for available settings
fileIndex.settings(
    number_of_shards=1,
    number_of_replicas=0
)


@fileIndex.doc_type
class CommitteeDocument(DocType):
    autocomplete = fields.CompletionField(attr="name_autocomplete")

    body = fields.ObjectField(properties={
        'id': fields.IntegerField(),
        'name': fields.StringField(),
    })

    class Meta:
        model = Committee  # The model associate with this DocType

        # The fields of the model you want to be indexed in Elasticsearch
        fields = [
            'id',
            'name',
            'short_name',
        ]

        # To ignore auto updating of Elasticsearch when a model is save
        # or delete
        # ignore_signals = True
        # Don't perform an index refresh after every update (overrides global setting)
        # auto_refresh = False
