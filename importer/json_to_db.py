import logging
import mimetypes
import re
import textwrap
from typing import List, TypeVar, Type, Optional, Callable

from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext as _
from requests import HTTPError
from slugify.slugify import slugify

from importer import JSON
from importer.functions import externalize, import_order
from importer.loader import BaseLoader
from importer.models import CachedObject
from importer.utils import Utils
from mainapp import models
from mainapp.functions.geo_functions import geocode
from mainapp.models import (
    Body,
    Paper,
    Meeting,
    Person,
    AgendaItem,
    Membership,
    Organization,
    Location,
    LegislativeTerm,
    File,
    DefaultFields,
    Consultation,
    OrganizationType,
    PaperType,
)
from mainapp.models.file import fallback_date
from mainapp.models.helper import ShortableNameFields, DummyInterface

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=DefaultFields)


class JsonToDb:
    """ Converts oparl json to database objects """

    def __init__(
        self,
        loader: BaseLoader,
        utils: Optional[Utils] = None,
        default_body: Optional[Body] = None,
    ):
        self.loader = loader
        self.utils = utils or Utils()
        self.default_body = default_body
        self.warn_missing = True  # Some tests set this to False

        self.ensure_organization_type()

    A = TypeVar("A", bound=DefaultFields)

    def type_to_function(self, type_class: Type[A]) -> Callable[[JSON, A], A]:
        """ Avoiding some metaprogramming by making this explicit """
        mapping = {
            Body: self.body,
            Paper: self.paper,
            Meeting: self.meeting,
            Person: self.person,
            AgendaItem: self.agenda_item,
            Membership: self.membership,
            Organization: self.organization,
            Location: self.location,
            LegislativeTerm: self.legislative_term,
            File: self.file,
            Consultation: self.consultation,
        }

        return mapping[type_class]

    B = TypeVar("B", bound=DefaultFields)

    def type_to_related_function(
        self, type_class: Type[B]
    ) -> Optional[Callable[[JSON, B], B]]:
        """ Avoiding some metaprogramming by making this explicit """
        mapping = {
            Body: self.body_related,
            Paper: self.paper_related,
            Meeting: self.meeting_related,
            AgendaItem: self.agenda_item_related,
        }

        return mapping.get(type_class)

    def ensure_organization_type(self) -> None:
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

    def import_anything(
        self, oparl_id: str, object_type: Optional[Type[T]] = None
    ) -> DefaultFields:
        """ Hacky metaprogramming to import any object based on its id """
        logging.info("Importing single object {}".format(oparl_id))

        to_return = None

        try:
            loaded = self.loader.load(oparl_id)
        except HTTPError as e:
            logger.error(f"Failed to load {oparl_id}: {e}")
            # This is a horrible workaround for broken oparl implementations
            # See test_missing.py
            if object_type and issubclass(object_type, DummyInterface):
                logger.error(f"Using a dummy for {oparl_id}. THIS IS BAD.")
                # noinspection PyTypeChecker
                dummy: T = object_type.dummy(oparl_id)
                dummy.save()
                return dummy
            else:
                raise

        # When a resourced moved, the use specified id might be different from the object's id
        # The loader prints a warning in that case
        oparl_id = loaded["id"]
        externalized = list(externalize(loaded))
        # To avoid endless recursion, we sort the objects so that if A links to B then B gets imported first
        externalized.sort(
            key=lambda key: import_order.index(
                getattr(models, key.data["type"].split("/")[-1])
            )
        )

        for entry in externalized:
            instance = self.import_any_externalized(entry.data)

            defaults = {
                "url": entry.url,
                "data": entry.data,
                "oparl_type": entry.oparl_type,
                "to_import": False,
            }
            CachedObject.objects.update_or_create(url=entry.url, defaults=defaults)

            if entry.url == oparl_id:
                to_return = instance

        assert to_return, "Missing object for {}".format(oparl_id)
        return to_return

    def import_any_externalized(self, data: JSON) -> DefaultFields:
        type_split = data["type"].split("/")[-1]
        type_class = getattr(models, type_split)

        instance = type_class()
        self.init_base(data, instance)
        if not instance.deleted:
            self.type_to_function(type_class)(data, instance)

        # There exists e.g. the case where a consultation needs the paper, which itself imports the consultation,
        # which would cause an integrity error on save
        existing = type_class.objects_with_deleted.filter(oparl_id=data["id"]).first()
        if existing:
            self.init_base(data, existing)
            if not instance.deleted:
                self.type_to_function(type_class)(data, existing)
            existing.save()

            logger.info("Avoided cyclic import for {}".format(data["id"]))
            return existing

        instance.save()
        logger.debug(
            "Saved {} individually as {} {}".format(
                instance.oparl_id, type_class, instance.id
            )
        )

        return instance

    def retrieve(
        self, object_type: Type[T], oparl_id: Optional[str], warn: bool = True
    ) -> Optional[T]:
        if not oparl_id:
            return None

        db_object = object_type.objects_with_deleted.filter(oparl_id=oparl_id).first()
        if db_object:
            return db_object

        entry = CachedObject.objects.filter(url=oparl_id).first()
        if entry:
            return self.import_any_externalized(entry.data)
        else:
            if warn and self.warn_missing and object_type != Location:
                logger.warning(
                    "{} {} was supposed to be a part of the external lists, but isn't".format(
                        object_type, oparl_id
                    )
                )

            try:
                return self.import_anything(oparl_id, object_type)
            except HTTPError:
                logger.exception(
                    "Failed to download the {} {}".format(object_type, oparl_id)
                )
                return None

    def retrieve_many(
        self,
        object_type: Type[DefaultFields],
        oparl_ids: Optional[List[str]],
        debug_id: str,
    ) -> List[int]:
        if not oparl_ids:
            return []

        db_objects = list(
            object_type.objects_with_deleted.filter(oparl_id__in=oparl_ids).all()
        )

        if len(db_objects) != len(oparl_ids):
            found_ids = [db_object.oparl_id for db_object in db_objects]
            missing = sorted((set(oparl_ids) - set(found_ids)))

            if missing:
                for oparl_id in missing:
                    if self.warn_missing:
                        logger.warning(
                            f"The object {oparl_id} linked from {debug_id} was "
                            f"supposed to be a part of the external lists, but was not. "
                            f"This is a bug in the OParl implementation."
                        )

                    db_objects.append(self.import_anything(oparl_id, object_type))

        return db_objects

    E = TypeVar("E", bound=DefaultFields)

    def init_base(
        self, libobject: JSON, base: E, name_fixup: Optional[str] = None
    ) -> E:
        """ Sets common fields """

        if not libobject["id"]:
            raise RuntimeError("id is none: " + str(libobject))
        base.oparl_id = libobject["id"]
        base.deleted = bool(libobject.get("deleted", False))
        if isinstance(base, ShortableNameFields):
            base.name = libobject.get("name") or name_fixup
            base.set_short_name(libobject.get("shortName") or base.name)
        return base

    def location(self, libobject: JSON, location: Location) -> Location:
        location.description = libobject.get("description")
        location.is_official = self.utils.official_geojson
        location.geometry = libobject.get("geojson", {}).get("geometry")

        location.street_address = libobject.get("streetAddress")
        location.room = libobject.get("room")
        location.postal_code = libobject.get("postalCode")
        location.locality = libobject.get("locality")

        if not location.description:
            description = ""
            if location.room:
                description += location.room + ", "
            if location.street_address:
                description += location.street_address + ", "
            if location.locality:
                if location.postal_code:
                    description += location.postal_code + " "
                description += location.locality
            location.description = description

        # If a street_address is present, we try to find the exact location on the map
        if location.street_address and not location.geometry:
            search_str = location.street_address + ", "
            if location.locality:
                if location.postal_code:
                    search_str += location.postal_code + " " + location.locality
            elif self.default_body:
                search_str += self.default_body.short_name
            search_str += " " + settings.GEOEXTRACT_SEARCH_COUNTRY

            location.geometry = geocode(search_str)

        return location

    def legislative_term(
        self, libobject: JSON, term: LegislativeTerm
    ) -> Optional[LegislativeTerm]:

        if not libobject.get("startDate"):
            logger.error("Term has no start date - skipping")
            return None

        term.start = self.utils.parse_date(libobject.get("startDate"))
        if libobject.get("endDate"):
            term.end = self.utils.parse_date(libobject.get("endDate"))

        return term

    def file(self, libobject: JSON, file: File) -> File:
        cutoff = self.utils.filename_length_cutoff
        if libobject.get("fileName"):
            filename = libobject.get("fileName")
        elif libobject.get("name"):
            extension = mimetypes.guess_extension("application/pdf") or ""
            length = cutoff - len(extension)
            filename = slugify(libobject.get("name"))[:length] + extension
        else:
            access_url = libobject["accessUrl"]
            filename = slugify(access_url.split("/")[-1])[-cutoff:]

        file.name = libobject.get("name", "")
        if len(file.name) > 200:
            file.name = textwrap.wrap(file.name, 199)[0] + "\u2026"

        file.filename = filename
        file.mime_type = libobject.get("mimeType") or "application/octet-stream"
        file.legal_date = self.utils.parse_date(libobject.get("date"))
        file.sort_date = (
            self.utils.date_to_datetime(file.legal_date)
            or self.utils.parse_datetime(libobject.get("created"))
            or timezone.now()
        )
        file.oparl_access_url = libobject.get("accessUrl")
        file.oparl_download_url = libobject.get("downloadUrl")
        file.filesize = None
        file.parsed_text = libobject.get("text")
        file.license = libobject.get("fileLicense")

        # We current do not handle locations attached to files due
        # to the lack of data and our own location extraction

        return file

    def consultation(self, libobject: JSON, consultation: Consultation) -> Consultation:
        consultation.authoritative = libobject.get("authoritative")
        consultation.role = libobject.get("role")

        paper_backref = libobject.get("paper") or libobject.get("mst:backref")
        consultation.paper = self.retrieve(Paper, paper_backref)
        consultation.meeting = self.retrieve(Meeting, libobject.get("meeting"))
        consultation.authoritative = libobject.get("authoritative")

        return consultation

    def agenda_item(self, libobject: JSON, item: AgendaItem) -> AgendaItem:
        item.key = libobject.get("number") or "-"
        item.name = libobject.get("name")
        item.public = libobject.get("public")
        item.result = libobject.get("result")
        item.resolution_text = libobject.get("resolutionText")
        item.start = self.utils.parse_datetime(libobject.get("start"))
        item.end = self.utils.parse_datetime(libobject.get("end"))
        meeting_backref = libobject.get("meeting") or libobject.get("mst:backref")
        item.meeting = self.retrieve(Meeting, meeting_backref)
        item.position = libobject.get("mst:backrefPosition")

        item.consultation = self.retrieve(Consultation, libobject.get("consultation"))
        item.resolution_file = self.retrieve(File, libobject.get("resolutionFile"))

        return item

    def agenda_item_related(self, libobject: JSON, item: AgendaItem) -> None:
        item.auxiliary_file.set(
            self.retrieve_many(File, libobject.get("auxiliaryFile"), libobject["id"])
        )

    def membership(self, libobject: JSON, membership: Membership) -> Membership:
        role = libobject.get("role") or _("Unknown")

        membership.start = self.utils.parse_date(libobject.get("startDate"))
        membership.end = self.utils.parse_date(libobject.get("endDate"))
        membership.role = role
        person_backref = libobject.get("person") or libobject.get("mst:backref")
        membership.person = self.retrieve(Person, person_backref)
        membership.organization = self.retrieve(
            Organization, libobject.get("organization")
        )

        return membership

    def body(self, libobject: JSON, body: Body) -> Body:
        body.short_name = self.utils.normalize_body_name(body.short_name)

        body.ags = libobject.get("ags")
        if body.ags:
            body.ags = body.ags.replace(" ", "")
        if len(body.ags or "") > 8:
            # Special case for https://ris.krefeld.de/webservice/oparl/v1/body/1
            if body.ags[8:] == "0" * len(body.ags[8:]):
                body.ags = body.ags[:8]
            else:
                raise RuntimeError(
                    "The Amtliche Gemeindeschlüssel of {} is longer than 8 characters: '{}'".format(
                        body, body.ags
                    )
                )

        # We don't really need the location because we have our own outline
        # importing logic and don't need the city, but we import it for comprehensiveness
        location = self.retrieve(Location, libobject.get("location"))
        if location and location.geometry:
            if location.geometry["type"] == "Point":
                body.center = location
                body.outline = None
            elif location.geometry["type"] == "Polygon":
                logger.warning("Overriding outline of Body with api version")
                body.center = None
                body.outline = location
            else:
                logger.warning(
                    "Location object is of type {}, which is neither 'Point' nor 'Polygon'."
                    "Skipping this location.".format(location.geometry["type"])
                )

        return body

    def body_related(self, libobject: JSON, body: Body) -> None:
        body.legislative_terms.set(
            self.retrieve_many(
                LegislativeTerm, libobject.get("legislativeTerm"), libobject["id"]
            )
        )

    def paper(self, libobject: JSON, paper: Paper) -> Paper:
        if libobject.get("paperType"):
            paper_type, created = PaperType.objects.get_or_create(
                defaults={"paper_type": libobject.get("paperType")}
            )
            paper.paper_type = paper_type
            if created:
                logging.info(
                    "Created new paper type {} through {}".format(
                        paper_type, libobject["id"]
                    )
                )

        paper.reference_number = libobject.get("reference")
        paper.main_file = self.retrieve(File, libobject.get("mainFile"))

        paper.legal_date = self.utils.parse_date(libobject.get("date"))
        # At this point we don't have the agenda items yet. We'll fix up the
        # cases where there are consultations but no legal date later
        paper.display_date = paper.legal_date
        # If we don't have a good date, sort them behind those with a good date
        paper.sort_date = self.utils.date_to_datetime(paper.legal_date) or fallback_date

        return paper

    def paper_related(self, libobject: JSON, paper: Paper) -> None:
        paper.files.set(
            self.retrieve_many(File, libobject.get("auxiliaryFile"), libobject["id"])
        )
        paper.organizations.set(
            self.retrieve_many(
                Organization, libobject.get("underDirectionOf"), libobject["id"]
            )
        )
        paper.persons.set(
            self.retrieve_many(
                Person, libobject.get("originatorPerson"), libobject["id"]
            )
        )

    def organization(self, libobject: JSON, organization: Organization) -> Organization:
        type_name = libobject.get("organizationType")

        # E.g. Leipzig sets organizationType: "Gremium" and classification: "Fraktion" for factions,
        # so we give priority to classification
        if libobject.get("classification") in self.utils.organization_classification:
            type_name = libobject["classification"]

        type_id = self.utils.organization_classification.get(type_name)
        if type_id:
            orgtype = OrganizationType.objects.get(id=type_id)
        else:
            orgtype, _ = OrganizationType.objects.get_or_create(
                name=libobject.get("organizationType")
            )
        organization.organization_type = orgtype
        if libobject.get("body"):
            # If we really have a case with an extra body then this should error because then we need some extra handling
            organization.body = Body.by_oparl_id(libobject["body"])
        else:
            organization.body = self.default_body
        organization.start = self.utils.parse_date(libobject.get("startDate"))
        organization.end = self.utils.parse_date(libobject.get("endDate"))

        organization.location = self.retrieve(Location, libobject.get("location"))

        if organization.name == organization.short_name and type_name:
            pattern = "[- ]?" + re.escape(type_name) + "[ ]?"
            organization.short_name = re.sub(
                pattern, "", organization.short_name, flags=re.I
            )

        return organization

    def meeting(self, libobject: JSON, meeting: Meeting) -> Meeting:
        meeting.start = self.utils.parse_datetime(libobject.get("start"))
        meeting.end = self.utils.parse_datetime(libobject.get("end"))
        meeting.location = self.retrieve(Location, libobject.get("location"))
        meeting.invitation = self.retrieve(File, libobject.get("invitation"))
        meeting.verbatim_protocol = self.retrieve(
            File, libobject.get("verbatimProtocol")
        )
        meeting.results_protocol = self.retrieve(File, libobject.get("resultsProtocol"))
        meeting.cancelled = libobject.get("cancelled", False)

        return meeting

    def meeting_related(self, libobject: JSON, meeting: Meeting) -> None:
        meeting.auxiliary_files.set(
            self.retrieve_many(File, libobject.get("auxiliaryFile"), libobject["id"])
        )
        meeting.persons.set(
            self.retrieve_many(Person, libobject.get("participant"), libobject["id"])
        )
        meeting.organizations.set(
            self.retrieve_many(
                Organization, libobject.get("organization"), libobject["id"]
            )
        )

    def person(self, libobject: JSON, person: Person) -> Person:
        name = libobject.get("name")
        given_name = libobject.get("givenName")
        family_name = libobject.get("familyName")

        if not name:
            if given_name and family_name:
                name = given_name + " " + family_name
            else:
                logger.warning("Person without name: {}".format(libobject["id"]))
                name = _("Unknown")

        if not given_name and not family_name and " " in name:
            given_name = name.split(" ")[-2]
            family_name = name.split(" ")[-1]
            logger.warning("Inferring given and family name from compound name")

        if not given_name:
            logger.warning("Person without given name: {}".format(libobject["id"]))
            given_name = _("Unknown")

        if not family_name:
            logger.warning("Person without family name: {}".format(libobject["id"]))
            family_name = _("Unknown")

        person.name = name
        person.given_name = given_name
        person.family_name = family_name
        person.location = self.retrieve(Location, libobject.get("location"))

        return person
