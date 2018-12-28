import logging
import mimetypes
import textwrap
from collections import defaultdict
from typing import Dict, Any, List, Tuple
from typing import Optional

from django.conf import settings
from django.utils.translation import ugettext as _
from slugify.slugify import slugify

from importer.oparl_utils import OParlUtils
from mainapp.functions.document_parsing import extract_locations, extract_persons
from mainapp.functions.geo_functions import geocode
from mainapp.models import LegislativeTerm, Location, File
from mainapp.models import (
    Paper,
    Meeting,
    Person,
    AgendaItem,
    OrganizationMembership,
    Organization,
)
from mainapp.models.consultation import Consultation

logger = logging.getLogger(__name__)


class OParlEmbedded:
    def __init__(self, helper: OParlUtils):
        self.utils = helper

        # mappings that could not be resolved because the target object
        # hasn't been imported yet
        self.meeting_person_queue = defaultdict(list)
        self.meeting_organization_queue = defaultdict(list)
        self.paper_organization_queue = []

        # Inner objects need to be defered until all the Main objects are parsed
        self.memberships = []  # type: List[Tuple[str, Dict[str, Any]]]
        self.consultations = []  # type: List[Tuple[str, Dict[str, Any]]]
        self.agendaitems = []  # type: List[Tuple[str, int, Dict[str, Any]]]

    def location(self, libobject: Dict[str, Any]) -> Location:
        location, do_update = self.utils.check_for_modification(
            libobject, Location, name_fixup=_("Unknown")
        )
        if not location or not do_update:
            return location

        logger.info("Processing Location {}".format(libobject["id"]))

        location.oparl_id = libobject["id"]
        location.description = libobject.get("description")
        location.is_official = self.utils.official_geojson
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

    def term(self, libobject: Dict[str, Any]) -> Optional[LegislativeTerm]:
        if not libobject.get("startDate") or not libobject.get("endDate"):
            logger.error("Term has no start or end date - skipping")
            return

        term, do_update = self.utils.check_for_modification(libobject, LegislativeTerm)
        if not term or not do_update:
            return term

        logger.info("Processing {}".format(libobject.get("name")))

        term.start = self.utils.parse_date(libobject.get("startDate"))
        term.end = self.utils.parse_date(libobject.get("endDate"))

        term.save()

        return term

    def file(self, libobject: Dict[str, Any]) -> File:
        file, do_update = self.utils.check_for_modification(libobject, File)
        if not file or not do_update:
            return file
        logger.info("Processing File {}".format(libobject["id"]))

        if libobject.get("fileName"):
            displayed_filename = libobject.get("fileName")
        elif libobject.get("name"):
            extension = mimetypes.guess_extension("application/pdf") or ""
            length = self.utils.filename_length_cutoff - len(extension)
            displayed_filename = slugify(libobject.get("name"))[:length] + extension
        else:
            access_url = libobject.get("accessUrl")
            displayed_filename = slugify(access_url)[
                -self.utils.filename_length_cutoff :
            ]

        parsed_text_before = file.parsed_text
        file_name_before = file.name

        file.oparl_id = libobject["id"]
        file.name = libobject.get("name", "")[:200]
        file.displayed_filename = displayed_filename
        file.mime_type = libobject.get("mimeType") or "application/octet-stream"
        file.legal_date = self.utils.parse_date(libobject.get("date"))
        file.sort_date = file.created
        file.oparl_access_url = libobject.get("accessUrl")
        file.oparl_download_url = libobject.get("downloadUrl")
        file.filesize = -1

        file.save_without_historical_record()  # Generates an id which need for downloading the file

        # If no text comes from the API, don't overwrite previously extracted PDF-content with an empty string
        if libobject.get("text"):
            file.parsed_text = libobject.get("text")

        if self.utils.download_files:
            url = libobject.get("downloadUrl") or libobject.get("accessUrl")
            tmpfile = self.utils.download_file(file, url, libobject)
            if tmpfile:
                file.parsed_text = self.utils.extract_text_from_file(file, tmpfile.name)
                tmpfile.close()

        file = self.utils.call_custom_hook("sanitize_file", file)

        if len(file.name) > 200:
            file.name = textwrap.wrap(file.name, 199)[0] + "\u2026"

        if file_name_before != file.name or parsed_text_before != file.parsed_text:
            # These two operations are rather CPU-intensive, so we only perform them if something relevant has changed
            logger.info(
                "Extracting locations from PDF for file {} ({})".format(file.id, file)
            )
            file.locations.set(extract_locations(file.parsed_text))
            file.mentioned_persons.set(
                extract_persons(file.name + "\n" + (file.parsed_text or "") + "\n")
            )

        file.save()

        return file

    def consultation(self, libobject: Dict[str, Any], paper_id: str) -> Consultation:
        consultation, do_update = self.utils.check_for_modification(
            libobject, Consultation
        )
        if not consultation or not do_update:
            return consultation

        consultation.oparl_id = libobject["id"]
        consultation.authoritative = libobject.get("authoritative")
        consultation.role = libobject.get("role")

        consultation = self.utils.call_custom_hook(
            "sanitize_consultation", consultation
        )

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

    def add_embedded_objects(self) -> None:
        logger.info("Adding {} consultations".format(len(self.consultations)))
        for paper_id, libobject in self.consultations:
            self.consultation(libobject, paper_id)
        logger.info("Adding {} agendaitems".format(len(self.agendaitems)))
        for meeting_id, index, libobject in self.agendaitems:
            self.agendaitem(libobject, index, meeting_id)
        logger.info("Adding {} memberships".format(len(self.memberships)))
        for person_id, libobject in self.memberships:
            self.membership(libobject, person_id)

    def agendaitem(
        self, libobject: Dict[str, Any], index: int, meeting_id: str
    ) -> AgendaItem:
        item, do_update = self.utils.check_for_modification(libobject, AgendaItem)
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

        item = self.utils.call_custom_hook("sanitize_agenda_item", item)

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

    def membership(self, libobject: Dict[str, Any], person_id: str) -> None:
        membership, do_update = self.utils.check_for_modification(
            libobject, OrganizationMembership
        )
        if not membership or not do_update:
            return membership

        role = libobject.get("role")
        if not role:
            role = _("Unknown")

        membership.start = self.utils.parse_date(libobject.get("startDate"))
        membership.end = self.utils.parse_date(libobject.get("endDate"))
        membership.role = role
        membership.person = Person.objects_with_deleted.get(oparl_id=person_id)
        organization_id = libobject["organization"]
        membership.organization = Organization.objects_with_deleted.get(
            oparl_id=organization_id
        )

        membership.save()

        return membership

    def add_missing_associations(self) -> None:
        logger.info(
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

        logger.info(
            "Adding {} missing organizations to papers".format(
                len(self.paper_organization_queue)
            )
        )
        for paper, organization_url in self.paper_organization_queue:
            org = Organization.objects_with_deleted.get(oparl_id=organization_url)
            paper.organizations.add(org)

        length = len(self.meeting_organization_queue)
        logger.info("Adding {} missing organizations to meetings".format(length))
        for base_object, associated_urls in self.meeting_organization_queue.items():
            associated = []
            for url in associated_urls:
                org = Organization.objects_with_deleted.get(oparl_id=url)
                associated.append(org)
            base_object.organizations.set(associated)
            base_object.save()
