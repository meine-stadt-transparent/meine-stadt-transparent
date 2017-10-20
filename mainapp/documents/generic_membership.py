from django_elasticsearch_dsl import fields

from .utils import autocomplete_analyzer


class GenericMembershipDocument:
    autocomplete = fields.StringField(attr="name", analyzer=autocomplete_analyzer)

    body = fields.ObjectField(properties={
        'id': fields.IntegerField(),
        'name': fields.StringField(),
    })

    class Meta:
        fields = [
            'id',
            'name',
            'short_name'
        ]
