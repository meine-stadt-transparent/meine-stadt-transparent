from django_elasticsearch_dsl import StringField, IntegerField, ObjectField, DateField

from .utils import autocomplete_analyzer


class GenericMembershipDocument:
    autocomplete = StringField(attr="name", analyzer=autocomplete_analyzer)
    sort_date = DateField()

    body = ObjectField(properties={
        'id': IntegerField(),
        'name': StringField(),
    })

    class Meta:
        fields = ['id', 'name', 'short_name']
