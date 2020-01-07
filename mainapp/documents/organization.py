from django.conf import settings
from django_elasticsearch_dsl import (
    Document,
    TextField,
    ObjectField,
    IntegerField,
    DateField,
)
from django_elasticsearch_dsl.registries import registry

from mainapp.models import Organization
from .generic_membership import GenericMembershipDocument
from .index import autocomplete_analyzer


@registry.register_document
class OrganizationDocument(Document, GenericMembershipDocument):
    autocomplete = TextField(attr="name", analyzer=autocomplete_analyzer)
    sort_date = DateField()
    body = ObjectField(properties={"id": IntegerField(), "name": TextField()})

    def get_queryset(self):
        return Organization.objects.prefetch_related("body").order_by("id")

    class Index:
        name = settings.ELASTICSEARCH_PREFIX + "-organization"

    class Django(GenericMembershipDocument.Django):
        model = Organization
        queryset_pagination = settings.ELASTICSEARCH_QUERYSET_PAGINATION

        fields = ["id", "name", "short_name", "start", "end", "created", "modified"]
