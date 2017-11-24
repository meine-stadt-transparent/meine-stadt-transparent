from django.utils.translation import pgettext as _

from .file import FileDocument
from .meeting import MeetingDocument
from .paper import PaperDocument
from .organization import OrganizationDocument
from .person import PersonDocument

DOCUMENT_TYPES = ["file", "meeting", "paper", "organization", "person"]

DOCUMENT_TYPE_NAMES = {
    "file": _('Document Type Name', 'File'),
    "meeting": _('Document Type Name', 'Meeting'),
    "paper": _('Document Type Name', 'Paper'),
    "organization": _('Document Type Name', 'Organization'),
    "person": _('Document Type Name', 'Person'),
}

DOCUMENT_TYPE_NAMES_PL = {
    "file": _('Document Type Name', 'Files'),
    "meeting": _('Document Type Name', 'Meetings'),
    "paper": _('Document Type Name', 'Papers'),
    "organization": _('Document Type Name', 'Organizations'),
    "person": _('Document Type Name', 'Persons'),
}