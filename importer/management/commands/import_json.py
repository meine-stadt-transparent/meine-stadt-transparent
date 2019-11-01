import json
import logging
from pathlib import Path
from typing import Type, Dict, Tuple

from django.conf import settings
from django.core.exceptions import MultipleObjectsReturned
from django.core.management import BaseCommand, CommandParser

from importer.importer import Importer
from importer.loader import BaseLoader
from importer.json_datatypes import RisData, converter
from mainapp import models
from mainapp.functions.city_to_ags import city_to_ags
from mainapp.functions.citytools import import_outline, import_streets
from mainapp.models import Body, OrganizationType
from mainapp.models.default_fields import SoftDeleteModelManager

logger = logging.getLogger(__name__)

office_replaces = {
    "Stadträtin": "",
    "Stadtrat": "",
    "Bürgermeisterin": "",
    "Bürgermeister": "",
    "Erster": "",
    "Oberbürgermeisterin": "",
    "Oberbürgermeister": "",
}
honors_replaces = {"Dr.": "", "Pfarrerin": "", "Pfarrer": ""}


def make_id_map(cls: Type[SoftDeleteModelManager]) -> Dict[int, int]:
    return dict((int(i), j) for i, j in cls.values_list("oparl_id", "id"))


def normalize_name(name: str) -> Tuple[str, str, str]:
    """ Tries to extract given and family name from a string that might contain titles/form of address. """
    for old, new in office_replaces.items():
        name = name.replace(old, new)
    name = name.strip()
    unhonored = name
    for old, new in honors_replaces.items():
        unhonored = unhonored.replace(old, new)
    unhonored = unhonored.strip()
    given_names = unhonored[: unhonored.rfind(" ")]
    family_name = unhonored[unhonored.rfind(" ") + 1 :]
    return family_name, given_names, name


class Command(BaseCommand):
    help = "Imports a municipality from a json file"

    def add_arguments(self, parser: CommandParser):
        # noinspection PyTypeChecker
        parser.add_argument("input", type=Path, help="Path to the json file")
        parser.add_argument("--ags", help="The Amtliche Gemeindeschlüssel")
        parser.add_argument(
            "--skip-download",
            action="store_true",
            dest="skip_download",
            default=False,
            help="Do not download and parse the files",
        )
        parser.add_argument(
            "--skip-body-extra",
            action="store_true",
            dest="skip_body_extra",
            default=False,
            help="Do not download streets and shape of the body",
        )

    def handle(self, *args, **options):
        input_file: Path = options["input"]

        logger.info("Loading the data")
        with input_file.open() as fp:
            ris_data: RisData = converter.structure(json.load(fp), RisData)

        body = Body.objects.filter(name=ris_data.name).first()
        if not body:
            logger.info("Building the body")

            if options["ags"]:
                ags = options["ags"]
            else:
                ags = city_to_ags(ris_data.name, False)
                if not ags:
                    raise RuntimeError(
                        f"Failed to determine the Amtliche Gemeindeschlüssel for '{ris_data.name}'. Please look it up yourself and specify it with `--ags`"
                    )
                logger.info(f"The Amtliche Gemeindeschlüssel is {ags}")
            body = Body(name=ris_data.name, short_name=ris_data.name, ags=ags)
            body.save()
            if not options["skip_body_extra"]:
                import_outline(body)
                import_streets(body)
        else:
            logging.info("Using existing body")

        self.import_papers(ris_data)
        self.import_files(ris_data)
        paper_id_map = make_id_map(models.Paper.objects)
        file_id_map = make_id_map(models.File.objects)
        self.import_paper_files(ris_data, paper_id_map, file_id_map)
        self.import_organizations(body, ris_data)
        self.import_meeting_locations(ris_data)
        locations = dict(models.Location.objects.values_list("description", "id"))
        self.import_meetings(ris_data, locations)
        meeting_id_map = make_id_map(
            models.Meeting.objects.filter(oparl_id__isnull=False)
        )
        organization_name_id_map = dict(
            models.Organization.objects.values_list("name", "id")
        )
        self.import_meeting_organization(
            meeting_id_map, organization_name_id_map, ris_data
        )

        self.import_persons(ris_data)
        self.import_consultations(ris_data, meeting_id_map, paper_id_map)

        # We don't have original ids for all agenda items (yet?),
        # so we just assume meeting x paper is unique
        consultation_map = {
            (a, b): c
            for a, b, c in models.Consultation.objects.values_list(
                "meeting_id", "paper_id", "id"
            )
        }

        self.import_agenda_items(
            ris_data, consultation_map, meeting_id_map, paper_id_map
        )
        self.import_memberships(ris_data)

        if not options["skip_download"]:
            logger.info("Downloading and parsing the files")
            Importer(BaseLoader(dict()), force_singlethread=True).load_files(
                fallback_city=body.short_name
            )

    def import_memberships(self, ris_data: RisData):
        logger.info("Processing the memberships")
        # TODO: Currently, the persons list is incomplete. This patches it up until that's solved
        #   properly by a rewrite of the relevant scraper part
        #   Use https://buergerinfo.ulm.de/kp0043.php?__swords=%22%22&__sgo=Suchen instead to get all persons and memberships
        #   at once and then use some custom id scheme where no original id exists
        person_name_map = {
            name: person_id
            for name, person_id in models.Person.objects.values_list("name", "id")
        }
        db_persons_fixup = []
        persons_fixup_done = set()
        for csv_membership in ris_data.memberships:
            family_name, given_names, name = normalize_name(csv_membership.person_name)
            if not name in person_name_map and name not in persons_fixup_done:
                db_persons_fixup.append(
                    models.Person(
                        given_name=given_names, family_name=family_name, name=name
                    )
                )
                persons_fixup_done.add(name)
        models.Person.objects.bulk_create(db_persons_fixup, 100)
        person_name_map = {
            name: person_id
            for name, person_id in models.Person.objects.values_list("name", "id")
        }
        # Assumption: Organizations that don't have an id in the overview page aren't linked anywhere
        organization_id_map = make_id_map(
            models.Organization.objects.filter(oparl_id__isnull=False)
        )
        db_memberships = []
        for csv_membership in ris_data.memberships:
            person_id = person_name_map[normalize_name(csv_membership.person_name)[2]]
            organization = organization_id_map[csv_membership.organization_original_id]

            db_memberships.append(
                models.Membership(
                    person_id=person_id,
                    start=csv_membership.start_date,
                    end=csv_membership.end_date,
                    role=csv_membership.role,
                    organization_id=organization,
                )
            )
        models.Membership.objects.bulk_create(db_memberships, 100)

    def import_agenda_items(
        self,
        ris_data: RisData,
        consultation_map: Dict[Tuple[int, int], int],
        meeting_id_map: Dict[int, int],
        paper_id_map: Dict[int, int],
    ):
        logger.info("Processing the agenda items")
        db_agenda_items = []
        for csv_agenda_item in ris_data.agenda_items:
            if csv_agenda_item.result and csv_agenda_item.voting:
                result = csv_agenda_item.result + ", " + csv_agenda_item.voting
            else:
                result = csv_agenda_item.result
            consultation = consultation_map.get(
                (
                    meeting_id_map[csv_agenda_item.meeting_id],
                    paper_id_map.get(csv_agenda_item.paper_original_id),
                )
            )
            db_agenda_items.append(
                models.AgendaItem(
                    key=csv_agenda_item.key[:20],  # TODO: Better normalization
                    position=csv_agenda_item.position,
                    name=csv_agenda_item.title,
                    consultation_id=consultation,
                    meeting_id=meeting_id_map[csv_agenda_item.meeting_id],
                    public=True,
                    result=result,
                    oparl_id=csv_agenda_item.original_id,
                )
            )
        models.AgendaItem.objects.bulk_create(db_agenda_items, 100)

    def import_consultations(
        self,
        ris_data: RisData,
        meeting_id_map: Dict[int, int],
        paper_id_map: Dict[int, int],
    ):
        logger.info("Processing the consultations")
        db_consultations = []
        for csv_agenda_item in ris_data.agenda_items:
            if csv_agenda_item.paper_original_id:
                db_consultations.append(
                    # TODO: authoritative and role (this information exists at least on the
                    # consultations page of the paper in some ris
                    models.Consultation(
                        meeting_id=meeting_id_map[csv_agenda_item.meeting_id],
                        paper_id=paper_id_map[csv_agenda_item.paper_original_id],
                        oparl_id=csv_agenda_item.original_id,
                    )
                )
        models.Consultation.objects.bulk_create(db_consultations, 100)

    def import_persons(self, ris_data: RisData):
        logger.info("Processing the persons")
        db_persons = []
        for csv_person in ris_data.persons:
            family_name, given_names, name = normalize_name(csv_person.name)
            logger.debug(
                f"Normalizing {csv_person.name}: '{name}', '{given_names}', '{family_name}'"
            )
            db_persons.append(
                models.Person(
                    name=name, given_name=given_names, family_name=family_name
                )
            )
        models.Person.objects.bulk_create(db_persons, 100)

    def import_meeting_organization(
        self, meeting_id_map, organization_name_id_map, ris_data
    ):
        logger.info("Processing the meeting-organization-associations")
        db_meeting_to_organization = []
        for csv_meeting in ris_data.meetings:
            if csv_meeting.original_id:
                associated_meeting_id = meeting_id_map[csv_meeting.original_id]
            else:
                try:
                    associated_meeting_id = models.Meeting.objects.get(
                        name=csv_meeting.title, start=csv_meeting.start
                    ).id
                except MultipleObjectsReturned:
                    meetings_found = [
                        (i.name, i.start)
                        for i in models.Meeting.objects.filter(
                            name=csv_meeting.title, start=csv_meeting.start
                        ).all()
                    ]
                    logger.error(f"Multiple meetings found: {meetings_found}")
                    raise
            associated_organization_id = organization_name_id_map.get(
                csv_meeting.organization_name
            )

            if associated_organization_id:
                db_meeting_to_organization.append(
                    models.Meeting.organizations.through(
                        meeting_id=associated_meeting_id,
                        organization_id=associated_organization_id,
                    )
                )
        models.Meeting.organizations.through.objects.bulk_create(
            db_meeting_to_organization, batch_size=100
        )

    def import_meeting_locations(self, ris_data: RisData):
        logger.info("Processing the meeting locations")
        db_locations: Dict[str, models.Location] = dict()
        for csv_meeting in ris_data.meetings:
            if not csv_meeting.location or csv_meeting.location in db_locations:
                continue

            # TODO: Try to normalize the locations
            #   and geocode after everything else has been done
            db_location = models.Location(
                description=csv_meeting.location,
                is_official=True,  # TODO: Is this true after geocoding?
            )
            db_locations[csv_meeting.location] = db_location
        models.Location.objects.bulk_create(db_locations.values(), batch_size=100)

    def import_meetings(self, ris_data: RisData, locations: Dict[str, int]):
        logger.info("Processing the meetings")
        db_meetings = []
        for csv_meeting in ris_data.meetings:
            location_id = (
                locations[csv_meeting.location] if csv_meeting.location else None
            )
            db_meeting = models.Meeting(
                name=csv_meeting.title,
                short_name=csv_meeting.title[:50],  # TODO: Better normalization,
                start=csv_meeting.start,
                end=csv_meeting.end,
                location_id=location_id,
                oparl_id=csv_meeting.original_id,
                cancelled=False,
            )
            db_meetings.append(db_meeting)
        models.Meeting.objects.bulk_create(db_meetings, batch_size=100)

    def import_organizations(self, body: models.Body, ris_data: RisData):
        logger.info("Processing the organizations")
        committee = settings.COMMITTEE_TYPE
        committee_type, _ = OrganizationType.objects.get_or_create(
            id=committee[0], defaults={"name": committee[1]}
        )
        db_organizations = []
        for csv_organization in ris_data.organizations:
            if csv_organization.original_id:
                oparl_id = str(csv_organization.original_id)
            else:
                oparl_id = None
            db_organization = models.Organization(
                name=csv_organization.name,
                short_name=csv_organization.name[:50],  # TODO: Better normalization
                body=body,
                organization_type=committee_type,
                oparl_id=oparl_id,
            )
            db_organizations.append(db_organization)
        models.Organization.objects.bulk_create(db_organizations, batch_size=100)

    def import_paper_files(
        self,
        ris_data: RisData,
        paper_id_map: Dict[int, int],
        file_id_map: Dict[int, int],
    ):
        logger.info("Processing the file-paper-associations")
        db_file_to_paper = []
        for csv_file in ris_data.files:
            db_file_to_paper.append(
                models.Paper.files.through(
                    paper_id=paper_id_map[csv_file.paper_original_id],
                    file_id=file_id_map[csv_file.original_id],
                )
            )
        models.Paper.files.through.objects.bulk_create(db_file_to_paper, batch_size=100)

    def import_papers(self, ris_data: RisData):
        logger.info("Processing the paper")

        db_paper_all = []
        for csv_paper in ris_data.papers:
            db_paper = models.Paper(
                short_name=csv_paper.short_title[:50],  # TODO: Better normalization
                name=csv_paper.title,
                reference_number=csv_paper.reference_number,
                oparl_id=csv_paper.original_id,
            )

            if csv_paper.paper_type:
                paper_type, created = models.PaperType.objects.get_or_create(
                    paper_type=csv_paper.paper_type
                )
                db_paper.paper_type = paper_type
            db_paper_all.append(db_paper)
        models.Paper.objects.bulk_create(db_paper_all, batch_size=100)

    def import_files(self, ris_data: RisData):
        logger.info("Processing the files")
        db_files = []
        for csv_file in ris_data.files:
            assert csv_file.paper_original_id is not None
            db_file = models.File(
                name=csv_file.title[:200],  # TODO: Better normalization
                oparl_download_url=csv_file.url,
                oparl_access_url=csv_file.url,
                oparl_id=csv_file.original_id,
            )
            db_files.append(db_file)
        models.File.objects.bulk_create(db_files, batch_size=100)
