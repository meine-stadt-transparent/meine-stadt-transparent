import logging
from typing import Dict, Any

from django.conf import settings

from importer.oparl_embedded import OParlEmbedded
from importer.oparl_utils import OParlUtils
from mainapp.models import (
    Body,
    Paper,
    Meeting,
    Person,
    AgendaItem,
    OrganizationMembership,
    Organization,
)
from mainapp.models.consultation import Consultation
from mainapp.models.organization_type import OrganizationType
from mainapp.models.paper_type import PaperType

logger = logging.getLogger(__name__)


class OParlObjects:
    """ Methods for saving the oparl objects as database entries. """

    def __init__(self, helper: OParlUtils):
        self.utils = helper
        self.embedded = OParlEmbedded(helper)
        # Ensure the existence of the three predefined organization types
        group = settings.PARLIAMENTARY_GROUPS_TYPE
        OrganizationType.objects.get_or_create(id=group[0], defaults={"name": group[1]})

        committee = settings.COMMITTEE_TYPE
        OrganizationType.objects.get_or_create(
            id=committee[0], defaults={"name": committee[1]}
        )

        department = settings.DEPARTMENT_TYPE
        OrganizationType.objects.get_or_create(
            id=department[0], defaults={"name": department[1]}
        )

    def body(self, libobject: Dict[str, Any]) -> Any:
        return self.utils.process_object(
            libobject, Body, self.body_core, self.body_embedded
        )

    def body_core(self, libobject: Dict[str, Any], body: Body) -> None:
        logger.info("Processing {}".format(libobject["id"]))

        self.utils.normalize_body_name(body)

    def body_embedded(self, libobject: Dict[str, Any], body: Body) -> bool:
        changed = False
        terms = []
        for term in libobject.get("legislativeTerm", []):
            saved_term = self.embedded.term(term)
            if saved_term:
                terms.append(saved_term)
        changed = changed or not self.utils.is_queryset_equal_list(
            body.legislative_terms, terms
        )
        body.legislative_terms.set(terms)
        location = self.embedded.location(libobject.get("location"))
        if location and location.geometry:
            if location.geometry["type"] == "Point":
                changed = changed or body.center != location
                body.center = location
                body.outline = None
            elif location.geometry["type"] == "Polygon":
                changed = changed or body.outline != location
                body.center = None
                body.outline = location
            else:
                logger.warning(
                    "Location object is of type {}, which is neither 'Point' nor 'Polygon'."
                    "Skipping this location.".format(location.geometry["type"])
                )
        return changed

    def paper(self, libobject: Dict[str, Any]) -> Any:
        return self.utils.process_object(
            libobject, Paper, self.paper_core, self.paper_embedded
        )

    def paper_embedded(self, libobject: Dict[str, Any], paper: Paper) -> bool:
        changed = False
        files_with_none = [
            self.embedded.file(file) for file in libobject.get("auxiliaryFile", [])
        ]
        files_without_none = [file for file in files_with_none if file is not None]
        changed = changed or not self.utils.is_queryset_equal_list(
            paper.files, files_without_none
        )
        paper.files.set(files_without_none)
        old_main_file = paper.main_file
        paper.main_file = self.embedded.file(libobject.get("mainFile"))
        changed = changed or old_main_file != paper.main_file

        consultation_ids = []
        for consultation in libobject.get("consultation", []):
            self.embedded.consultations.append((libobject["id"], consultation))
            consultation_ids.append(consultation["id"])

        if not paper.deleted:
            Consultation.objects.filter(paper__oparl_id=libobject["id"]).exclude(
                oparl_id__in=consultation_ids
            ).update(deleted=True)
        else:
            Consultation.objects.filter(paper__oparl_id=libobject["id"]).update(
                deleted=True
            )

        organizations = []
        for org_url in libobject.get("underDirectionOf", []):
            organization = Organization.objects.filter(oparl_id=org_url).first()
            if organization:
                organizations.append(organization)
            else:
                self.embedded.paper_organization_queue.append((paper, org_url))
        changed = changed or not self.utils.is_queryset_equal_list(
            paper.organizations, organizations
        )
        paper.organizations.set(organizations)
        return changed

    def paper_core(self, libobject: Dict[str, Any], paper: Paper) -> None:
        logger.info("Processing Paper {}".format(libobject["id"]))
        if libobject.get("paperType"):
            paper_type, _ = PaperType.objects.get_or_create(
                defaults={"paper_type": libobject.get("paperType")}
            )
        else:
            paper_type = None
        paper.legal_date = self.utils.parse_date(libobject.get("date"))
        paper.sort_date = paper.created
        paper.reference_number = libobject.get("reference")
        paper.paper_type = paper_type

        self.utils.call_custom_hook("sanitize_paper", paper)

    def organization(self, libobject: Dict[str, Any]) -> Organization:
        return self.utils.process_object(
            libobject, Organization, self.organization_core, lambda x, y: False
        )

    def organization_without_embedded(self, libobject: Dict[str, Any]) -> Organization:
        return self.utils.process_object(
            libobject, Organization, self.organization_core, lambda x, y: False
        )

    def organization_core(
        self, libobject: Dict[str, Any], organization: Organization
    ) -> None:
        logger.info("Processing Organization {}".format(libobject["id"]))
        type_id = self.utils.organization_classification.get(
            libobject.get("organizationType")
        )
        if type_id:
            orgtype = OrganizationType.objects.get(id=type_id)
        else:
            orgtype, _ = OrganizationType.objects.get_or_create(
                name=libobject.get("organizationType")
            )
        organization.organization_type = orgtype
        organization.body = Body.by_oparl_id(libobject["body"])
        organization.start = self.utils.parse_date(libobject.get("startDate"))
        organization.end = self.utils.parse_date(libobject.get("endDate"))

        self.utils.call_custom_hook("sanitize_organization", organization)

    def meeting(self, libobject: Dict[str, Any]) -> Meeting:
        return self.utils.process_object(
            libobject, Meeting, self.meeting_core, self.meeting_embedded
        )

    def meeting_embedded(self, libobject: Dict[str, Any], meeting: Meeting) -> bool:
        changed = False
        auxiliary_files = []
        for oparlfile in libobject.get("auxiliaryFile", []):
            djangofile = self.embedded.file(oparlfile)
            if djangofile:
                auxiliary_files.append(djangofile)
        changed = changed or not self.utils.is_queryset_equal_list(
            meeting.auxiliary_files, auxiliary_files
        )
        meeting.auxiliary_files.set(auxiliary_files)
        persons = []
        for oparlperson in libobject.get("participant", []):
            djangoperson = Person.by_oparl_id(oparlperson)
            if djangoperson:
                persons.append(djangoperson)
            else:
                self.embedded.meeting_person_queue[libobject["id"]].append(oparlperson)
        changed = changed or not self.utils.is_queryset_equal_list(
            meeting.persons, persons
        )
        meeting.persons.set(persons)

        agendaitem_ids = []
        for index, oparlitem in enumerate(libobject.get("agendaItem", [])):
            self.embedded.agendaitems.append((libobject["id"], index, oparlitem))
            agendaitem_ids.append(oparlitem["id"])

        if not meeting.deleted:
            AgendaItem.objects.filter(meeting__oparl_id=libobject["id"]).exclude(
                oparl_id__in=agendaitem_ids
            ).update(deleted=True)
        else:
            AgendaItem.objects.filter(meeting__oparl_id=libobject["id"]).update(
                deleted=True
            )

        organizations = []
        for organization_url in libobject.get("organization", []):
            djangoorganization = Organization.objects.filter(
                oparl_id=organization_url
            ).first()
            if djangoorganization:
                organizations.append(djangoorganization)
            else:
                self.embedded.meeting_organization_queue[meeting].append(
                    organization_url
                )
        changed = changed or not self.utils.is_queryset_equal_list(
            meeting.organizations, organizations
        )
        meeting.organizations.set(organizations)

        return changed

    def meeting_core(self, libobject: Dict[str, Any], meeting: Meeting) -> None:
        logger.info("Processing Meeting {}".format(libobject["id"]))
        meeting.start = self.utils.parse_datetime(libobject.get("start"))
        meeting.end = self.utils.parse_datetime(libobject.get("end"))
        meeting.location = self.embedded.location(libobject.get("location"))
        meeting.invitation = self.embedded.file(libobject.get("invitation"))
        meeting.verbatim_protocol = self.embedded.file(
            libobject.get("verbatimProtocol")
        )
        meeting.results_protocol = self.embedded.file(libobject.get("resultsProtocol"))
        meeting.cancelled = libobject.get("cancelled", False)

        self.utils.call_custom_hook("sanitize_meeting", meeting)

    def person(self, libobject: Dict[str, Any]) -> Paper:
        return self.utils.process_object(
            libobject, Person, self.person_core, self.person_embedded
        )

    def person_embedded(self, libobject: Dict[str, Any], person: Person) -> bool:
        old_location = person.location
        person.location = self.embedded.location(libobject.get("location"))

        membership_ids = []
        for membership in libobject.get("membership", []):
            self.embedded.memberships.append((libobject["id"], membership))
            membership_ids.append(membership["id"])

        if not person.deleted:
            OrganizationMembership.objects.filter(
                person__oparl_id=libobject["id"]
            ).exclude(oparl_id__in=membership_ids).update(deleted=True)
        else:
            OrganizationMembership.objects.filter(
                person__oparl_id=libobject["id"]
            ).update(deleted=True)

        return old_location != person.location

    def person_core(self, libobject: Dict[str, Any], person: Person) -> None:
        logger.info("Processing Person {}".format(libobject["id"]))
        person.name = libobject.get("name")
        person.given_name = libobject.get("givenName")
        person.family_name = libobject.get("familyName")

        self.utils.call_custom_hook("sanitize_person", person)
