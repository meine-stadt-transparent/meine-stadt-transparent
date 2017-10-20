from django_elasticsearch_dsl import DocType

from mainapp.documents.generic_membership import GenericMembershipDocument
from mainapp.models import ParliamentaryGroup
from .utils import fileIndex


@fileIndex.doc_type
class ParliamentaryGroupDocument(DocType, GenericMembershipDocument):
    autocomplete = GenericMembershipDocument.autocomplete
    body = GenericMembershipDocument.body

    class Meta(GenericMembershipDocument.Meta):
        model = ParliamentaryGroup

        fields = GenericMembershipDocument.Meta.fields + ["start", "end"]
