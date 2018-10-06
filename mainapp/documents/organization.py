from django_elasticsearch_dsl import (
    DocType,
    StringField,
    ObjectField,
    IntegerField,
    DateField,
)

from mainapp.models import Organization
from .generic_membership import GenericMembershipDocument
from .index import elastic_index, autocomplete_analyzer


@elastic_index.doc_type
class OrganizationDocument(DocType, GenericMembershipDocument):
    autocomplete = StringField(attr="name", analyzer=autocomplete_analyzer)
    sort_date = DateField(attr="sort_date")
    body = ObjectField(properties={"id": IntegerField(), "name": StringField()})

    def get_queryset(self):
        return Organization.objects.prefetch_related("body").order_by('id')

    class Meta(GenericMembershipDocument.Meta):
        model = Organization
        queryset_pagination = 500

        fields = ["id", "name", "short_name", "start", "end", "created", "modified"]
