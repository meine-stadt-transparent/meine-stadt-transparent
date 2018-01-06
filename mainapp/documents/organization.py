from django_elasticsearch_dsl import DocType, StringField, ObjectField, IntegerField

from mainapp.models import Organization
from .generic_membership import GenericMembershipDocument
from .utils import mainIndex, autocomplete_analyzer


@mainIndex.doc_type
class OrganizationDocument(DocType, GenericMembershipDocument):
    autocomplete = StringField(attr="name", analyzer=autocomplete_analyzer)
    body = ObjectField(properties={
        'id': IntegerField(),
        'name': StringField(),
    })

    class Meta(GenericMembershipDocument.Meta):
        model = Organization

        fields = ["id", "name", "short_name", "start", "end", "created", "modified"]
