from django_elasticsearch_dsl import DocType, fields

from mainapp.models import File
from .utils import fileIndex


@fileIndex.doc_type
class FileDocument(DocType):
    coordinates = fields.GeoPointField(attr="coordinates")

    class Meta:
        model = File  # The model associate with this DocType

        # The fields of the model you want to be indexed in Elasticsearch
        fields = [
            'id',
            'storage_filename',
            'parsed_text',
            'created',
        ]

        # To ignore auto updating of Elasticsearch when a model is save
        # or delete
        # ignore_signals = True
        # Don't perform an index refresh after every update (overrides global setting)
        # auto_refresh = False
