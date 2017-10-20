from django_elasticsearch_dsl.documents import DocType

from mainapp.models import Committee
from .generic_membership import GenericMembershipDocument
from .utils import RelatedToValueList
from .utils import fileIndex


@fileIndex.doc_type
class CommitteeDocument(DocType, GenericMembershipDocument):
    autocomplete = GenericMembershipDocument.autocomplete
    body = GenericMembershipDocument.body
    legislative_terms = RelatedToValueList(attr="legislative_terms")

    class Meta(GenericMembershipDocument.Meta):
        model = Committee

        fields = GenericMembershipDocument.Meta.fields + ["start", "end"]
