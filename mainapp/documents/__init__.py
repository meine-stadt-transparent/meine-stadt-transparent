from .committee import CommitteeDocument
from .department import DepartmentDocument
from .file import FileDocument
from .meeting import MeetingDocument
from .paper import PaperDocument
from .parliamentary_group import ParliamentaryGroupDocument
from .person import PersonDocument
from django.utils.translation import pgettext as _

DOCUMENT_TYPES = ["committee", "department", "file", "meeting", "paper", "parliamentary_group", "person"]

DOCUMENT_TYPE_NAMES = {
    "committee": _('Document Type Name', 'Committee'),
    "department": _('Document Type Name', 'Department'),
    "file": _('Document Type Name', 'File'),
    "meeting": _('Document Type Name', 'Meeting'),
    "paper": _('Document Type Name', 'Paper'),
    "parliamentary_group": _('Document Type Name', 'Parliamentary group'),
    "person": _('Document Type Name', 'Person'),
}

DOCUMENT_TYPE_NAMES_PL = {
    "committee": _('Document Type Name', 'Committees'),
    "department": _('Document Type Name', 'Departments'),
    "file": _('Document Type Name', 'Files'),
    "meeting": _('Document Type Name', 'Meetings'),
    "paper": _('Document Type Name', 'Papers'),
    "parliamentary_group": _('Document Type Name', 'Parliamentary groups'),
    "person": _('Document Type Name', 'Persons'),
}
