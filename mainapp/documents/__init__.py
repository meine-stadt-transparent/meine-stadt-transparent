from django.utils.translation import pgettext

from .file import FileDocument
from .meeting import MeetingDocument
from .organization import OrganizationDocument
from .paper import PaperDocument
from .person import PersonDocument

DOCUMENT_TYPES = ["file", "meeting", "paper", "organization", "person"]

DOCUMENT_TYPE_NAMES = {
    "file": pgettext("Document Type Name", "File"),
    "meeting": pgettext("Document Type Name", "Meeting"),
    "paper": pgettext("Document Type Name", "Paper"),
    "organization": pgettext("Document Type Name", "Organization"),
    "person": pgettext("Document Type Name", "Person"),
}

DOCUMENT_TYPE_NAMES_PL = {
    "file": pgettext("Document Type Name", "Files"),
    "meeting": pgettext("Document Type Name", "Meetings"),
    "paper": pgettext("Document Type Name", "Papers"),
    "organization": pgettext("Document Type Name", "Organizations"),
    "person": pgettext("Document Type Name", "Persons"),
}
