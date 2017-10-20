from django_elasticsearch_dsl import DocType

from mainapp.documents.generic_membership import GenericMembershipDocument
from mainapp.models.department import Department
from .utils import fileIndex


@fileIndex.doc_type
class DepartmentDocument(DocType, GenericMembershipDocument):
    autocomplete = GenericMembershipDocument.autocomplete
    body = GenericMembershipDocument.body

    class Meta(GenericMembershipDocument.Meta):
        model = Department
