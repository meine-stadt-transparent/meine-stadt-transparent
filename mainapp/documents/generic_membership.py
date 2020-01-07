from django_elasticsearch_dsl import TextField, IntegerField, ObjectField, DateField

from meine_stadt_transparent import settings
from .index import autocomplete_analyzer


class GenericMembershipDocument:
    autocomplete = TextField(attr="name", analyzer=autocomplete_analyzer)
    sort_date = DateField()

    body = ObjectField(properties={"id": IntegerField(), "name": TextField()})

    class Django:
        fields = ["id", "name", "short_name"]
        queryset_pagination = settings.ELASTICSEARCH_QUERYSET_PAGINATION
