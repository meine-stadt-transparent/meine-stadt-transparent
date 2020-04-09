import datetime
import json
import logging
from pathlib import Path
from typing import Dict, Type, Any, Tuple, List, Callable, Iterable, TypeVar

import django.db.models
from dateutil import tz
from django.conf import settings
from django.core.exceptions import MultipleObjectsReturned
from django.core.management import (
    BaseCommand,
    CommandParser,
    CommandError,
    call_command,
)
from django.core.management.color import no_style
from django.db import connection, transaction

from importer import json_datatypes
from importer.functions import fix_sort_date
from importer.importer import Importer
from importer.json_datatypes import RisData, converter, format_version
from importer.loader import BaseLoader
from mainapp import models
from mainapp.functions.city_to_ags import city_to_ags
from mainapp.functions.citytools import import_outline, import_streets
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
# Assumption: This is older than the oldest data
fallback_date = datetime.datetime(1997, 1, 1, 0, 0, 0, tzinfo=tz.tzlocal())

field_lists: Dict[Type, List[str]] = {
    models.AgendaItem: [
        "key",
        "position",
        "name",
        "consultation_id",
        "meeting_id",
        "public",
        "result",
        "oparl_id",
    ],
    models.Consultation: ["meeting_id", "paper_id", "oparl_id"],
    models.Meeting: [
        "name",
        "short_name",
        "start",
        "end",
        "location_id",
        "oparl_id",
        "cancelled",
    ],
    models.Meeting.organizations.through: ["meeting_id", "organization_id"],
    models.Membership: ["person_id", "start", "end", "role", "organization_id"],
    models.Organization: [
        "name",
        "short_name",
        "body",
        "organization_type",
        "oparl_id",
    ],
    models.Paper: ["short_name", "name", "reference_number", "oparl_id", "paper_type"],
    models.Paper.files.through: ["paper_id", "file_id"],
    models.Person: ["name", "given_name", "family_name"],
}

unique_field_dict: Dict[Type, List[str]] = {
    models.AgendaItem: ["meeting_id", "name"],
    models.Consultation: ["meeting_id", "paper_id"],
    models.File: ["oparl_id"],
    models.Meeting: ["oparl_id"],
    models.Meeting.organizations.through: ["meeting_id", "organization_id"],
    models.Membership: ["person_id", "organization_id"],
    models.Organization: ["oparl_id"],
    models.Paper: ["oparl_id"],
    models.Paper.files.through: ["paper_id", "file_id"],
    models.Person: ["name"],
}


def get_from_db(current_model: Type[django.db.models.Model]) -> Tuple[dict, dict]:
    db_value_list = current_model.objects.values_list("id", *field_lists[current_model])
    db_ids = dict()
    db_map = dict()
    for db_entry in db_value_list:
        field_dict = dict(zip(field_lists[current_model], db_entry[1:]))
        tuple_id = tuple(field_dict[i] for i in unique_field_dict[current_model])
        db_ids[tuple_id] = db_entry[0]
        db_map[tuple_id] = db_entry[1:]
    return db_ids, db_map


T = TypeVar("T")


def incremental_import(
    current_model: Type[django.db.models.Model],
    json_objects: Iterable[Dict[str, Any]],
    soft_delete: bool = True,
):
    """ Compared the objects in the database with the json data for a given objects and
    creates, updates and (soft-)deletes the appropriate records. """

    json_map = dict()
    for json_dict in json_objects:
        key = tuple(json_dict[j] for j in unique_field_dict[current_model])
        json_map[key] = json_dict

    db_ids, db_map = get_from_db(current_model)

    common = set(json_map.keys()) & set(db_map.keys())
    to_be_created = set(json_map.keys()) - common
    to_be_deleted = set(db_map.keys()) - common
    to_be_updated = []
    for existing in common:
        if json_map[existing] != db_map[existing]:
            to_be_updated.append((json_map[existing], db_ids[existing]))

    to_be_created = [current_model(**json_map[i1]) for i1 in to_be_created]

    # TODO: Don't use bulk create here which makes the initial import much
    #       slower but also allows us to skip the search index recreation?
    #       Or can we retrieve the renewed entries and reindex only them in elasticsearch?
    logger.info(f"Creating {len(to_be_created)} {current_model.__name__}")
    current_model.objects.bulk_create(to_be_created)

    logger.info(f"Updating {len(to_be_updated)} {current_model.__name__}")
    with transaction.atomic():
        for json_object, pk in to_be_updated:
            current_model.objects.filter(pk=pk).update(**json_object)

    deletion_ids = [db_ids[i1] for i1 in to_be_deleted]
    if soft_delete:
        current_model.objects.filter(id__in=deletion_ids).update(deleted=True)
    else:
        current_model.objects.filter(id__in=deletion_ids).delete()
    # TODO: Delete files


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


def convert_agenda_item(
    json_agenda_item: json_datatypes.AgendaItem,
    consultation_map: Dict[Tuple[int, int], int],
    meeting_id_map: Dict[int, int],
    paper_id_map: Dict[int, int],
) -> Dict[str, Any]:
    if json_agenda_item.result and json_agenda_item.voting:
        result = json_agenda_item.result + ", " + json_agenda_item.voting
    else:
        result = json_agenda_item.result
    consultation = consultation_map.get(
        (
            meeting_id_map[json_agenda_item.meeting_id],
            paper_id_map.get(json_agenda_item.paper_original_id),
        )
    )
    return {
        "key": json_agenda_item.key[:20],  # TODO: Better normalization
        "position": json_agenda_item.position,
        "name": json_agenda_item.name,
        "consultation_id": consultation,
        "meeting_id": meeting_id_map[json_agenda_item.meeting_id],
        "public": True,
        "result": result,
        "oparl_id": str(json_agenda_item.original_id),
    }


def convert_consultation(
    json_agenda_item: json_datatypes.AgendaItem,
    meeting_id_map: Dict[int, int],
    paper_id_map: Dict[int, int],
) -> Dict[str, Any]:
    # TODO: authoritative and role (this information exists at least on the
    # consultations page of the paper in some ris
    return {
        "meeting_id": meeting_id_map[json_agenda_item.meeting_id],
        "paper_id": paper_id_map[json_agenda_item.paper_original_id],
        "oparl_id": json_agenda_item.original_id,
    }


def convert_person(args: Tuple[str, str, str]) -> Dict[str, Any]:
    family_name, given_names, name = args
    return {"name": name, "given_name": given_names, "family_name": family_name}


def convert_location(json_meeting: json_datatypes.Meeting) -> models.Location:
    # TODO: Try to normalize the locations
    #   and geocode after everything else has been done
    return models.Location(
        description=json_meeting.location,
        is_official=True,  # TODO: Is this true after geocoding?
    )


def convert_meeting(
    json_meeting: json_datatypes.Meeting, locations: Dict[str, int]
) -> Dict[str, Any]:
    location_id = locations[json_meeting.location] if json_meeting.location else None
    return {
        "name": json_meeting.name,
        "short_name": json_meeting.name[:50],  # TODO: Better normalization,
        "start": json_meeting.start,
        "end": json_meeting.end,
        "location_id": location_id,
        "oparl_id": str(json_meeting.original_id),
        "cancelled": False,
    }


def convert_paper(json_paper: json_datatypes.Paper) -> Dict[str, Any]:
    db_paper = {
        "short_name": json_paper.short_name[:50],  # TODO: Better normalization
        "name": json_paper.name,
        "reference_number": json_paper.reference,
        "oparl_id": str(json_paper.original_id),
    }
    if json_paper.paper_type:
        paper_type, created = models.PaperType.objects.get_or_create(
            paper_type=json_paper.paper_type
        )
        db_paper["paper_type"] = paper_type
    return db_paper


def convert_organization(
    body: models.Body,
    committee_type: models.OrganizationType,
    json_organization: json_datatypes.Organization,
) -> Dict[str, Any]:
    if json_organization.original_id:
        oparl_id = str(json_organization.original_id)
    else:
        oparl_id = None
    return {
        "name": json_organization.name,
        "short_name": json_organization.name[:50],  # TODO: Better normalization
        "body": body,
        "organization_type": committee_type,
        "oparl_id": oparl_id,
    }


def convert_file_to_paper(json_file, file_id_map, paper_id_map) -> Dict[str, Any]:
    return {
        "paper_id": paper_id_map[json_file.paper_original_id],
        "file_id": file_id_map[json_file.original_id],
    }


def convert_file(json_file):
    assert json_file.paper_original_id is not None
    return models.File(
        name=json_file.name[:200],  # TODO: Better normalization
        oparl_download_url=json_file.url,
        oparl_access_url=json_file.url,
        oparl_id=json_file.original_id,
    )


def handle_counts(ris_data: RisData, allow_shrinkage: bool):
    """ Prints the old and new counts and makes sure we don't accidentally delete entries """
    existing_counts = {
        "Paper": models.Paper.objects.count(),
        "File": models.File.objects.count(),
        "Person": models.Person.objects.count(),
        "Meeting": models.Meeting.objects.count(),
        "Organization": models.Organization.objects.count(),
        "Membership": models.Membership.objects.count(),
        "Agenda Item": models.AgendaItem.objects.count(),
    }
    new_counts = ris_data.get_counts()
    formatter = lambda x: " | ".join(f"{key_} {value_}" for key_, value_ in x.items())
    logger.info(f"Existing: {formatter(existing_counts)}")
    logger.info(f"New: {formatter(new_counts)}")
    if not allow_shrinkage:
        for key, value in existing_counts.items():
            # TODO: This check currently doesn't work because there's a fixup creating persons in the membership part
            if key == "Person":
                continue
            # The -3 is to allow some deletion or some failed page
            if new_counts[key] < value - 3:
                raise RuntimeError(
                    f"There are {value} {key} in the database, but only {new_counts[key]} in "
                    f"the imported dataset. This indicates a scraper failure. "
                    f"Use `--allow-shrinkage` to override."
                )


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
        parser.add_argument(
            "--allow-shrinkage",
            action="store_true",
            dest="allow_shrinkage",
            default=False,
            help="Don't fail when trying to import a smaller dataset over a bigger existing one",
        )

    def handle(self, *args, **options):
        input_file: Path = options["input"]

        logger.info("Loading the data")
        with input_file.open() as fp:
            json_data = json.load(fp)
            if json_data["format_version"] != format_version:
                raise CommandError(
                    f"This version of {settings.PRODUCT_NAME} can only import json format version {format_version}, "
                    f"but the json file you provided is version {json_data['format_version']}"
                )
            ris_data: RisData = converter.structure(json_data, RisData)

        body = models.Body.objects.filter(name=ris_data.meta.name).first()
        if not body:
            logger.info("Building the body")

            if options["ags"] or ris_data.meta.ags:
                ags = options["ags"] or ris_data.meta.ags
            else:
                ags = city_to_ags(ris_data.meta.name, False)
                if not ags:
                    raise RuntimeError(
                        f"Failed to determine the Amtliche Gemeindeschlüssel for '{ris_data.meta.name}'. "
                        f"Please look it up yourself and specify it with `--ags`"
                    )
                logger.info(f"The Amtliche Gemeindeschlüssel is {ags}")
            body = models.Body(
                name=ris_data.meta.name, short_name=ris_data.meta.name, ags=ags
            )
            body.save()
            if not options["skip_body_extra"]:
                import_outline(body)
                import_streets(body)
        else:
            logging.info("Using existing body")

        # TODO: Reenable this after some more thorough testing
        # handle_counts(ris_data, options["allow_shrinkage"])

        self.import_data(body, ris_data)

        fix_sort_date(fallback_date, datetime.datetime.now(tz=tz.tzlocal()))

        # With the current bulk indexing we need to do this manually
        call_command("search_index", action="populate")

        if not options["skip_download"]:
            Importer(BaseLoader(dict()), force_singlethread=True).load_files(
                fallback_city=body.short_name
            )

    def import_data(self, body: models.Body, ris_data: RisData):
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
        # flush_model(models.AgendaItem) # It's incremental!
        self.import_agenda_items(
            ris_data, consultation_map, meeting_id_map, paper_id_map
        )
        self.import_memberships(ris_data)

    def import_memberships(self, ris_data: RisData):
        logger.info(f"Importing {len(ris_data.memberships)} memberships")
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
        for json_membership in ris_data.memberships:
            family_name, given_names, name = normalize_name(json_membership.person_name)
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

        def convert_function(membership):
            person_id = person_name_map[normalize_name(membership.person_name)[2]]
            organization = organization_id_map[membership.organization_original_id]

            return {
                "person_id": person_id,
                "start": membership.start_date,
                "end": membership.end_date,
                "role": json_membership.role,
                "organization_id": organization,
            }

        incremental_import(
            models.Membership, [convert_function(i) for i in ris_data.memberships]
        )

    def import_agenda_items(
        self,
        ris_data: RisData,
        consultation_map: Dict[Tuple[int, int], int],
        meeting_id_map: Dict[int, int],
        paper_id_map: Dict[int, int],
    ):
        logger.info(f"Processing {len(ris_data.agenda_items)} agenda items")

        def convert_function(x):
            return convert_agenda_item(
                x, consultation_map, meeting_id_map, paper_id_map
            )

        incremental_import(
            models.AgendaItem, [convert_function(i) for i in ris_data.agenda_items]
        )

    def import_consultations(
        self,
        ris_data: RisData,
        meeting_id_map: Dict[int, int],
        paper_id_map: Dict[int, int],
    ):
        logger.info(f"Importing {len(ris_data.agenda_items)} consultations")

        agenda_items_filtered = []
        for json_agenda_item in ris_data.agenda_items:
            if json_agenda_item.paper_original_id:
                agenda_items_filtered.append(json_agenda_item)

        def convert_function(json_agenda_item_):
            return convert_consultation(json_agenda_item_, meeting_id_map, paper_id_map)

        incremental_import(
            models.Consultation, [convert_function(i) for i in agenda_items_filtered]
        )

    def import_persons(self, ris_data: RisData):
        logger.info(f"Importing {len(ris_data.persons)} persons")
        persons = [normalize_name(json_person.name) for json_person in ris_data.persons]
        incremental_import(models.Person, [convert_person(i) for i in persons])

    def import_meeting_organization(
        self, meeting_id_map, organization_name_id_map, ris_data
    ):
        logger.info("Processing the meeting-organization-associations")
        json_meetings = []
        for json_meeting in ris_data.meetings:
            associated_organization_id = organization_name_id_map.get(
                json_meeting.organization_name
            )

            if associated_organization_id:
                json_meetings.append(json_meeting)

        def convert_function(meeting):
            if meeting.original_id:
                associated_meeting_id = meeting_id_map[meeting.original_id]
            else:
                try:
                    associated_meeting_id = models.Meeting.objects.get(
                        name=meeting.name, start=meeting.start
                    ).id
                except MultipleObjectsReturned:
                    meetings_found = [
                        (i.name, i.start)
                        for i in models.Meeting.objects.filter(
                            name=meeting.name, start=meeting.start
                        ).all()
                    ]
                    logger.error(f"Multiple meetings found: {meetings_found}")
                    raise

            return {
                "meeting_id": associated_meeting_id,
                "organization_id": associated_organization_id,
            }

        incremental_import(
            models.Meeting.organizations.through,
            [convert_function(i) for i in json_meetings],
            soft_delete=False,
        )

    def import_meeting_locations(self, ris_data: RisData):
        logger.info(f"Importing {len(ris_data.meetings)} meeting locations")
        existing_locations = set(
            models.Location.objects.values_list("description", flat=True)
        )
        db_locations: Dict[str, models.Location] = dict()
        for json_meeting in ris_data.meetings:
            if not json_meeting.location or json_meeting.location in db_locations:
                continue

            if json_meeting.location in existing_locations:
                continue

            db_location = convert_location(json_meeting)
            db_locations[json_meeting.location] = db_location
        logger.info(f"Saving {len(db_locations)} new meeting locations")
        models.Location.objects.bulk_create(db_locations.values(), batch_size=100)

    def import_meetings(self, ris_data: RisData, locations: Dict[str, int]):
        logger.info(f"Importing {len(ris_data.meetings)} meetings")

        def convert_function(x: json_datatypes.Meeting):
            return convert_meeting(x, locations)

        incremental_import(
            models.Meeting, [convert_function(i) for i in ris_data.meetings]
        )

    def import_organizations(self, body: models.Body, ris_data: RisData):
        logger.info(f"Importing {len(ris_data.organizations)} organizations")
        committee = settings.COMMITTEE_TYPE
        committee_type, _ = models.OrganizationType.objects.get_or_create(
            id=committee[0], defaults={"name": committee[1]}
        )

        def convert_function(json_organization: json_datatypes.Organization):
            return convert_organization(body, committee_type, json_organization)

        incremental_import(
            models.Organization, [convert_function(i) for i in ris_data.organizations]
        )

    def import_paper_files(
        self,
        ris_data: RisData,
        paper_id_map: Dict[int, int],
        file_id_map: Dict[int, int],
    ):
        logger.info("Processing the file-paper-associations")

        def convert_function(json_file):
            return convert_file_to_paper(json_file, file_id_map, paper_id_map)

        incremental_import(
            models.Paper.files.through,
            [convert_function(i) for i in ris_data.files],
            soft_delete=False,
        )

    def import_papers(self, ris_data: RisData):
        logger.info(f"Importing {len(ris_data.papers)} paper")
        incremental_import(models.Paper, [convert_paper(i) for i in ris_data.papers])

    def import_files(self, ris_data: RisData):
        logger.info(f"Importing {len(ris_data.files)} files")
        existing_file_ids = make_id_map(models.File.objects)
        new_files = []
        for json_file in ris_data.files:
            if json_file.original_id in existing_file_ids:
                continue
            new_files.append(convert_file(json_file))
        logger.info(f"Saving {len(new_files)} new files")
        models.File.objects.bulk_create(new_files, batch_size=100)
