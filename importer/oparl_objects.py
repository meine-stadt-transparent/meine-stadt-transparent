import mimetypes
import textwrap
from collections import defaultdict
from tempfile import NamedTemporaryFile
from typing import Optional, Dict, Any, List, Tuple

import requests
from django.conf import settings
from django.utils.translation import ugettext as _
from requests import HTTPError
from slugify.slugify import slugify

from importer.functions import normalize_body_name
from importer.oparl_helper import OParlHelper
from mainapp.functions.document_parsing import extract_locations, extract_persons
from mainapp.functions.geo_functions import geocode
from mainapp.functions.minio import minio_client, minio_file_bucket
from mainapp.models import (
    Body,
    LegislativeTerm,
    Paper,
    Meeting,
    Location,
    File,
    Person,
    AgendaItem,
    OrganizationMembership,
    Organization,
)
from mainapp.models.consultation import Consultation
from mainapp.models.organization_type import OrganizationType
from mainapp.models.paper_type import PaperType


class OParlObjects(OParlHelper):
    """ Methods for saving the oparl objects as database entries. """

    def __init__(self, options: Dict[str, Any]):
        super().__init__(options)

        # mappings that could not be resolved because the target object
        # hasn't been imported yet
        self.meeting_person_queue = defaultdict(list)
        self.meeting_organization_queue = defaultdict(list)
        self.paper_organization_queue = []

        # Inner objects need to be defered until all the Main objects are parsed
        self.memberships = []  # type: List[Tuple[str, Dict[str, Any]]]
        self.consultations = []  # type: List[Tuple[str, Dict[str, Any]]]
        self.agendaitems = []  # type: List[Tuple[str, int, Dict[str, Any]]]

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
        return self.process_object(libobject, Body, self.body_core, self.body_embedded)

    def body_core(self, libobject: Dict[str, Any], body: Body) -> None:
        self.logger.info("Processing {}".format(libobject["id"]))

        normalize_body_name(body)

    def body_embedded(self, libobject: Dict[str, Any], body: Body) -> bool:
        changed = False
        terms = []
        for term in libobject.get("legislativeTerm", []):
            saved_term = self.term(term)
            if saved_term:
                terms.append(saved_term)
        changed = changed or not self.is_queryset_equal_list(
            body.legislative_terms, terms
        )
        body.legislative_terms.set(terms)
        location = self.location(libobject.get("location"))
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
                message = (
                    "Location object is of type {}, which is neither 'Point' nor 'Polygon'."
                    "Skipping this location.".format(location.geometry["type"])
                )
                self.errorlist.append(message)
        return changed

    def term(self, libobject: Dict[str, Any]) -> Optional[LegislativeTerm]:
        if not libobject.get("startDate") or not libobject.get("endDate"):
            self.logger.error("Term has no start or end date - skipping")
            return

        term, do_update = self.check_for_modification(libobject, LegislativeTerm)
        if not term or not do_update:
            return term

        self.logger.info("Processing {}".format(libobject.get("name")))

        term.start = self.parse_date(libobject.get("startDate"))
        term.end = self.parse_date(libobject.get("endDate"))

        term.save()

        return term

    def paper(self, libobject: Dict[str, Any]) -> Any:
        return self.process_object(
            libobject, Paper, self.paper_core, self.paper_embedded
        )

    def paper_embedded(self, libobject: Dict[str, Any], paper: Paper) -> bool:
        changed = False
        files_with_none = [
            self.file(file) for file in libobject.get("auxiliaryFile", [])
        ]
        files_without_none = [file for file in files_with_none if file is not None]
        changed = changed or not self.is_queryset_equal_list(
            paper.files, files_without_none
        )
        paper.files.set(files_without_none)
        old_main_file = paper.main_file
        paper.main_file = self.file(libobject.get("mainFile"))
        changed = changed or old_main_file != paper.main_file

        consultation_ids = []
        for consultation in libobject.get("consultation", []):
            self.consultations.append((libobject["id"], consultation))
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
                self.paper_organization_queue.append((paper, org_url))
        changed = changed or not self.is_queryset_equal_list(
            paper.organizations, organizations
        )
        paper.organizations.set(organizations)
        return changed

    def paper_core(self, libobject: Dict[str, Any], paper: Paper) -> None:
        self.logger.info("Processing Paper {}".format(libobject["id"]))
        if libobject.get("paperType"):
            paper_type, _ = PaperType.objects.get_or_create(
                defaults={"paper_type": libobject.get("paperType")}
            )
        else:
            paper_type = None
        paper.legal_date = self.parse_date(libobject.get("date"))
        paper.sort_date = paper.created
        paper.reference_number = libobject.get("reference")
        paper.paper_type = paper_type

        self.call_custom_hook("sanitize_paper", paper)

    def organization(self, libobject: Dict[str, Any]) -> Organization:
        return self.process_object(
            libobject, Organization, self.organization_core, lambda x, y: False
        )

    def organization_without_embedded(self, libobject: Dict[str, Any]) -> Organization:
        return self.process_object(
            libobject, Organization, self.organization_core, lambda x, y: False
        )

    def organization_core(
        self, libobject: Dict[str, Any], organization: Organization
    ) -> None:
        self.logger.info("Processing Organization {}".format(libobject["id"]))
        type_id = self.organization_classification.get(
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
        organization.start = self.parse_date(libobject.get("startDate"))
        organization.end = self.parse_date(libobject.get("endDate"))

        self.call_custom_hook("sanitize_organization", organization)

    def meeting(self, libobject: Dict[str, Any]) -> Meeting:
        return self.process_object(
            libobject, Meeting, self.meeting_core, self.meeting_embedded
        )

    def meeting_embedded(self, libobject: Dict[str, Any], meeting: Meeting) -> bool:
        changed = False
        auxiliary_files = []
        for oparlfile in libobject.get("auxiliaryFile", []):
            djangofile = self.file(oparlfile)
            if djangofile:
                auxiliary_files.append(djangofile)
        changed = changed or not self.is_queryset_equal_list(
            meeting.auxiliary_files, auxiliary_files
        )
        meeting.auxiliary_files.set(auxiliary_files)
        persons = []
        for oparlperson in libobject.get("participant", []):
            djangoperson = Person.by_oparl_id(oparlperson)
            if djangoperson:
                persons.append(djangoperson)
            else:
                self.meeting_person_queue[libobject["id"]].append(oparlperson)
        changed = changed or not self.is_queryset_equal_list(meeting.persons, persons)
        meeting.persons.set(persons)

        agendaitem_ids = []
        for index, oparlitem in enumerate(libobject.get("agendaItem", [])):
            self.agendaitems.append((libobject["id"], index, oparlitem))
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
                self.meeting_organization_queue[meeting].append(organization_url)
        changed = changed or not self.is_queryset_equal_list(
            meeting.organizations, organizations
        )
        meeting.organizations.set(organizations)

        return changed

    def meeting_core(self, libobject: Dict[str, Any], meeting: Meeting) -> None:
        self.logger.info("Processing Meeting {}".format(libobject["id"]))
        meeting.start = self.parse_datetime(libobject.get("start"))
        meeting.end = self.parse_datetime(libobject.get("end"))
        meeting.location = self.location(libobject.get("location"))
        meeting.invitation = self.file(libobject.get("invitation"))
        meeting.verbatim_protocol = self.file(libobject.get("verbatimProtocol"))
        meeting.results_protocol = self.file(libobject.get("resultsProtocol"))
        meeting.cancelled = libobject.get("cancelled", False)

        self.call_custom_hook("sanitize_meeting", meeting)

    def location(self, libobject: Dict[str, Any]) -> Location:
        location, do_update = self.check_for_modification(
            libobject, Location, name_fixup=_("Unknown")
        )
        if not location or not do_update:
            return location

        self.logger.info("Processing Location {}".format(libobject["id"]))

        location.oparl_id = libobject["id"]
        location.description = libobject.get("description")
        location.is_official = self.official_geojson
        location.geometry = libobject.get("geojson", {}).get("geometry")

        location.streetAddress = libobject.get("streetAddress")
        location.room = libobject.get("room")
        location.postalCode = libobject.get("postalCode")
        location.locality = libobject.get("locality")

        # Try to guess a better name for the location
        if libobject.get("room"):
            location.short_description = libobject.get("room")

        if not location.description:
            description = ""
            if libobject.get("room"):
                description += libobject.get("room") + ", "
            if libobject.get("streetAddress"):
                description += libobject.get("streetAddress") + ", "
            if libobject.get("locality"):
                if libobject.get("postalCode"):
                    description += libobject.get("postalCode") + " "
                description += libobject.get("locality")
            location.description = description

        # If a streetAddress is present, we try to find the exact location on the map
        if location.streetAddress:
            search_str = libobject.get("streetAddress") + ", "
            if libobject.get("locality"):
                if libobject.get("postalCode"):
                    search_str += libobject.get("postalCode") + " "
                    search_str += libobject.get("locality")
            else:
                search_str += settings.GEOEXTRACT_DEFAULT_CITY
            search_str += " " + settings.GEOEXTRACT_SEARCH_COUNTRY

            geodata = geocode(search_str)
            if geodata:
                location.geometry = {
                    "type": "Point",
                    "coordinates": [geodata["lng"], geodata["lat"]],
                }

        location.save()

        return location

    def agendaitem(
        self, libobject: Dict[str, Any], index: int, meeting_id: str
    ) -> AgendaItem:
        item, do_update = self.check_for_modification(libobject, AgendaItem)
        if not item or not do_update:
            return item

        item.key = libobject.get("number")
        if not item.key:
            item.key = "-"

        item.oparl_id = libobject["id"]
        item.key = libobject.get("number")
        item.title = libobject.get("name")
        item.position = index
        item.public = libobject.get("public")
        item.result = libobject.get("result")
        item.resolution_text = libobject.get("resolutionText")
        item.start = libobject.get("start")
        item.end = libobject.get("end")
        item.meeting = Meeting.objects_with_deleted.get(oparl_id=meeting_id)

        item = self.call_custom_hook("sanitize_agenda_item", item)

        item.save()

        item.resolution_file = self.file(libobject.get("resolutionFile"))
        if len(libobject.get("auxiliaryFile", [])) > 0:
            item.auxiliary_files = [
                self.file(i) for i in libobject.get("auxiliaryFile", [])
            ]
        item.consultation = Consultation.objects_with_deleted.get(
            oparl_id=libobject.get("consultation")
        )

        item.save()

        return item

    def consultation(self, libobject: Dict[str, Any], paper_id: str) -> Consultation:
        consultation, do_update = self.check_for_modification(libobject, Consultation)
        if not consultation or not do_update:
            return consultation

        consultation.oparl_id = libobject["id"]
        consultation.authoritative = libobject.get("authoritative")
        consultation.role = libobject.get("role")

        consultation = self.call_custom_hook("sanitize_consultation", consultation)

        consultation.save()

        consultation.paper = Paper.objects_with_deleted.get(oparl_id=paper_id)

        if libobject.get("meeting"):
            consultation.meeting = Meeting.objects_with_deleted.get(
                oparl_id=libobject["meeting"]
            )

        orgas = []
        for org_url in libobject.get("organization", []):
            orgas.append(Organization.objects_with_deleted.get(oparl_id=org_url))
        consultation.organizations.set(orgas)

        consultation.save()

        return consultation

    def download_file(
        self, file: File, url: str, libobject: Dict[str, Any]
    ) -> Optional[NamedTemporaryFile]:
        last_modified = self.parse_datetime(libobject.get("modified"))

        if (
            file.filesize
            and file.filesize > 0
            and file.modified
            and last_modified
            and last_modified < file.modified
            and minio_client.has_object(minio_file_bucket, str(file.id))
        ):
            self.logger.info("Skipping cached download: {}".format(url))
            return

        self.logger.info("Downloading {}".format(url))

        response = requests.get(url, allow_redirects=True)

        try:
            response.raise_for_status()
        except HTTPError as e:
            self.logger.exception("Failed to download file {}: {}", file.id, e)
            return

        tmpfile = NamedTemporaryFile()
        content = response.content
        tmpfile.write(content)
        tmpfile.file.seek(0)
        file.filesize = len(content)

        minio_client.put_object(
            minio_file_bucket,
            str(file.id),
            tmpfile.file,
            file.filesize,
            content_type=file.mime_type,
        )
        return tmpfile

    def file(self, libobject: Dict[str, Any]) -> File:
        file, do_update = self.check_for_modification(libobject, File)
        if not file or not do_update:
            return file
        self.logger.info("Processing File {}".format(libobject["id"]))

        if libobject.get("fileName"):
            displayed_filename = libobject.get("fileName")
        elif libobject.get("name"):
            extension = mimetypes.guess_extension("application/pdf") or ""
            length = self.filename_length_cutoff - len(extension)
            displayed_filename = slugify(libobject.get("name"))[:length] + extension
        else:
            access_url = libobject.get("accessUrl")
            displayed_filename = slugify(access_url)[-self.filename_length_cutoff :]

        parsed_text_before = file.parsed_text
        file_name_before = file.name

        file.oparl_id = libobject["id"]
        file.name = libobject.get("name", "")[:200]
        file.displayed_filename = displayed_filename
        file.mime_type = libobject.get("mimeType") or "application/octet-stream"
        file.legal_date = self.parse_date(libobject.get("date"))
        file.sort_date = file.created
        file.oparl_access_url = libobject.get("accessUrl")
        file.oparl_download_url = libobject.get("downloadUrl")
        file.filesize = -1

        file.save_without_historical_record()  # Generates an id which need for downloading the file

        # If no text comes from the API, don't overwrite previously extracted PDF-content with an empty string
        if libobject.get("text"):
            file.parsed_text = libobject.get("text")

        if self.download_files:
            url = libobject.get("downloadUrl") or libobject.get("accessUrl")
            tmpfile = self.download_file(file, url, libobject)
            if tmpfile:
                file.parsed_text = self.extract_text_from_file(file, tmpfile.name)
                tmpfile.close()

        file = self.call_custom_hook("sanitize_file", file)

        if len(file.name) > 200:
            file.name = textwrap.wrap(file.name, 199)[0] + "\u2026"

        if file_name_before != file.name or parsed_text_before != file.parsed_text:
            # These two operations are rather CPU-intensive, so we only perform them if something relevant has changed
            self.logger.info(
                "Extracting locations from PDF for file {} ({})".format(file.id, file)
            )
            file.locations.set(extract_locations(file.parsed_text))
            file.mentioned_persons.set(
                extract_persons(file.name + "\n" + (file.parsed_text or "") + "\n")
            )

        file.save()

        return file

    def person(self, libobject: Dict[str, Any]) -> Paper:
        return self.process_object(
            libobject, Person, self.person_core, self.person_embedded
        )

    def person_embedded(self, libobject: Dict[str, Any], person: Person) -> bool:
        old_location = person.location
        person.location = self.location(libobject.get("location"))

        membership_ids = []
        for membership in libobject.get("membership", []):
            self.memberships.append((libobject["id"], membership))
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
        self.logger.info("Processing Person {}".format(libobject["id"]))
        person.name = libobject.get("name")
        person.given_name = libobject.get("givenName")
        person.family_name = libobject.get("familyName")

        self.call_custom_hook("sanitize_person", person)

    def membership(self, libobject: Dict[str, Any], person_id: str) -> None:
        membership, do_update = self.check_for_modification(
            libobject, OrganizationMembership
        )
        if not membership or not do_update:
            return membership

        role = libobject.get("role")
        if not role:
            role = _("Unknown")

        membership.start = self.parse_date(libobject.get("startDate"))
        membership.end = self.parse_date(libobject.get("endDate"))
        membership.role = role
        membership.person = Person.objects_with_deleted.get(oparl_id=person_id)
        organization_id = libobject["organization"]
        membership.organization = Organization.objects_with_deleted.get(
            oparl_id=organization_id
        )

        membership.save()

        return membership

    def add_embedded_objects(self) -> None:
        self.logger.info("Adding {} consultations".format(len(self.consultations)))
        for paper_id, libobject in self.consultations:
            self.consultation(libobject, paper_id)
        self.logger.info("Adding {} agendaitems".format(len(self.agendaitems)))
        for meeting_id, index, libobject in self.agendaitems:
            self.agendaitem(libobject, index, meeting_id)
        self.logger.info("Adding {} memberships".format(len(self.memberships)))
        for person_id, libobject in self.memberships:
            self.membership(libobject, person_id)

    def add_missing_associations(self) -> None:
        self.logger.info(
            "Adding {} missing meeting <-> persons associations".format(
                len(self.meeting_person_queue.items())
            )
        )
        for meeting_id, person_ids in self.meeting_person_queue.items():
            meeting = Meeting.by_oparl_id(meeting_id)
            meeting.persons = [
                Person.by_oparl_id(person_id) for person_id in person_ids
            ]
            meeting.save()

        self.logger.info(
            "Adding {} missing organizations to papers".format(
                len(self.paper_organization_queue)
            )
        )
        for paper, organization_url in self.paper_organization_queue:
            org = Organization.objects_with_deleted.filter(
                oparl_id=organization_url
            ).first()
            if not org:
                org = self.organization_without_embedded(
                    self.resolve(organization_url).resolved_data
                )
            paper.organizations.add(org)

        length = len(self.meeting_organization_queue)
        self.logger.info("Adding {} missing organizations to meetings".format(length))
        for base_object, associated_urls in self.meeting_organization_queue.items():
            associated = []
            for url in associated_urls:
                org = Organization.objects_with_deleted.filter(oparl_id=url).first()
                if not org:
                    org = self.organization_without_embedded(
                        self.resolve(url).resolved_data
                    )
                    org.save()
                associated.append(org)
            base_object.organizations.set(associated)
            base_object.save()
