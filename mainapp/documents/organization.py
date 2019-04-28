from django_elasticsearch_dsl import (
    DocType,
    TextField,
    ObjectField,
    IntegerField,
    DateField,
)

from mainapp.documents.index import elastic_index_organization
from mainapp.models import Organization
from .generic_membership import GenericMembershipDocument
from .index import autocomplete_analyzer


@elastic_index_organization.doc_type
class OrganizationDocument(DocType, GenericMembershipDocument):
    autocomplete = TextField(attr="name", analyzer=autocomplete_analyzer)
    sort_date = DateField()
    body = ObjectField(properties={"id": IntegerField(), "name": TextField()})

    def get_queryset(self):
        return Organization.objects.prefetch_related("body").order_by("id")

    class Meta(GenericMembershipDocument.Meta):
        model = Organization
        queryset_pagination = 500

        fields = ["id", "name", "short_name", "start", "end", "created", "modified"]
