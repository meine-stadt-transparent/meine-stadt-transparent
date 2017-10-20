from django_elasticsearch_dsl import DocType, fields

from mainapp.models import ParliamentaryGroup
from .utils import autocomplete_analyzer, fileIndex


@fileIndex.doc_type
class ParliamentaryGroupDocument(DocType):
    autocomplete = fields.StringField(attr="name_autocomplete", analyzer=autocomplete_analyzer)

    body = fields.ObjectField(properties={
        'id': fields.IntegerField(),
        'name': fields.StringField(),
    })

    class Meta:
        model = ParliamentaryGroup

        fields = [
            'id',
            'name',
            'short_name',
        ]
