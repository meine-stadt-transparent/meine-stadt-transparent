from django_elasticsearch_dsl import DocType, fields

from mainapp.models import Person

from .utils import fileIndex, autocomplete_analyzer


@fileIndex.doc_type
class PersonDocument(DocType):
    autocomplete = fields.StringField(attr="name_autocomplete", analyzer=autocomplete_analyzer)

    class Meta:
        model = Person  # The model associate with this DocType

        # The fields of the model you want to be indexed in Elasticsearch
        fields = [
            'id',
            'name',
            'given_name',
            'family_name',
        ]

        # To ignore auto updating of Elasticsearch when a model is save
        # or delete
        # ignore_signals = True
        # Don't perform an index refresh after every update (overrides global setting)
        # auto_refresh = False
