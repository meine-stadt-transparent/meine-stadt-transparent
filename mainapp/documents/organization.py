from django_elasticsearch_dsl import DocType

from mainapp.models import Organization
from .generic_membership import GenericMembershipDocument
from .utils import mainIndex


@mainIndex.doc_type
class OrganizationDocument(DocType, GenericMembershipDocument):
    autocomplete = GenericMembershipDocument.autocomplete
    body = GenericMembershipDocument.body

    class Meta(GenericMembershipDocument.Meta):
        model = Organization

        fields = GenericMembershipDocument.Meta.fields + ["start", "end"]
