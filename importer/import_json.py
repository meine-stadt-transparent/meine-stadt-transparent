import logging
from datetime import datetime
from typing import Dict, Type, List, Tuple, TypeVar, Iterable, Any, Optional

import django.db.models
from django.conf import settings
from django.core.exceptions import MultipleObjectsReturned
from django.db import transaction
from django.utils import timezone
from django_elasticsearch_dsl.registries import registry
from tqdm import tqdm

from importer import json_datatypes
from importer.json_datatypes import RisData
from mainapp import models
from mainapp.functions.search import search_bulk_index
from mainapp.models import DefaultFields
from mainapp.models.file import fallback_date
from mainapp.models.helper import SoftDeleteModelManager

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
    models.File: ["name", "oparl_download_url", "oparl_access_url", "oparl_id"],
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
        "body_id",
        "organization_type_id",
        "oparl_id",
    ],
    models.Paper: [
        "short_name",
        "name",
        "reference_number",
        "oparl_id",
        "paper_type_id",
        "sort_date",
        "display_date",
    ],
    models.Paper.files.through: ["paper_id", "file_id"],
    models.Person: ["name", "given_name", "family_name"],
}
unique_field_dict: Dict[Type, List[str]] = {
    models.AgendaItem: ["meeting_id", "name"],
    models.Consultation: ["meeting_id", "paper_id"],
    models.File: ["oparl_id"],
    models.Meeting: ["oparl_id", "name", "start"],
    models.Meeting.organizations.through: ["meeting_id", "organization_id"],
    models.Membership: ["person_id", "organization_id"],
    models.Organization: ["oparl_id"],
    models.Paper: ["oparl_id"],
    models.Paper.files.through: ["paper_id", "file_id"],
    models.Person: ["name"],
}


def str_or_none(value: Any) -> Optional[str]:
    if value is not None:
        return str(value)
    else:
        return None


def get_from_db(current_model: Type[django.db.models.Model]) -> Tuple[dict, dict]:
    db_value_list = current_model.objects.values_list("id", *field_lists[current_model])
    db_ids = dict()
    db_map = dict()

    for db_entry in db_value_list:
        field_dict = dict(zip(field_lists[current_model], db_entry[1:]))
        tuple_id = tuple(field_dict[i] for i in unique_field_dict[current_model])
        db_ids[tuple_id] = db_entry[0]
        db_map[tuple_id] = dict(zip(field_lists[current_model], db_entry[1:]))

    return db_ids, db_map


T = TypeVar("T")


def incremental_import(
    current_model: Type[django.db.models.Model],
    json_objects: Iterable[Dict[str, Any]],
    soft_delete: bool = True,
):
    """Compared the objects in the database with the json data for a given objects and
    creates, updates and (soft-)deletes the appropriate records."""

    json_map = dict()
    for json_dict in json_objects:
        key = tuple(json_dict[j] for j in unique_field_dict[current_model])
        json_map[key] = json_dict

    # Remove manually deleted files
    if current_model == models.File:
        # noinspection PyUnresolvedReferences
        manually_deleted = current_model.objects_with_deleted.filter(
            manually_deleted=True
        ).values_list("oparl_id", flat=True)
        for i in manually_deleted:
            if (i,) in json_map:
                del json_map[(i,)]

    # Handle undeleted objects, e.g. papers that disappeared and reappeared
    if issubclass(current_model, DefaultFields):
        deleted = current_model.objects_with_deleted.filter(
            deleted=True, oparl_id__isnull=False
        ).values_list("oparl_id", flat=True)
        oparls_ids = [i.get("oparl_id") for i in json_objects]
        to_undelete = set(deleted) & set(oparls_ids)
        if to_undelete:
            logger.info(f"{current_model.__name__}: Undeleting {len(to_undelete)}")
            current_model.objects_with_deleted.filter(oparl_id__in=to_undelete).update(
                deleted=False
            )

    db_ids, db_map = get_from_db(current_model)

    common = set(json_map.keys()) & set(db_map.keys())
    to_be_created = set(json_map.keys()) - common
    to_be_deleted = set(db_map.keys()) - common
    to_be_updated = []
    for existing in common:
        if json_map[existing] != db_map[existing]:
            to_be_updated.append((json_map[existing], db_ids[existing]))

    # We need to delete first and then create to avoid conflicts e.g. when the start of a meeting with an oparl_id
    # changed
    deletion_ids = [db_ids[i1] for i1 in to_be_deleted]
    logger.info(
        f"{current_model.__name__}: "
        f"Deleting {len(to_be_deleted)}, "
        f"Creating {len(to_be_created)} and "
        f"Updating {len(to_be_updated)}"
    )

    # Since we don't get the bulk created object ids back from django (yet?),
    # we just do this by timestamp - indexing more that necessary isn't wrong anyway
    before_bulk_create = timezone.now()

    if soft_delete:
        deleted_rows = current_model.objects.filter(id__in=deletion_ids).update(
            deleted=True, modified=timezone.now()
        )
    else:
        current_model.objects.filter(id__in=deletion_ids).delete()
        deleted_rows = 0
    # TODO: Delete files

    to_be_created = [current_model(**json_map[i1]) for i1 in to_be_created]
    current_model.objects.bulk_create(to_be_created, batch_size=100)

    # Bulk create doesn't update the search index, so we do this manually
    if settings.ELASTICSEARCH_ENABLED and current_model in registry.get_models():
        # Changed/Created
        qs = current_model.objects.filter(modified__gte=before_bulk_create)
        qs_count = qs.count()

        assert qs_count >= len(
            to_be_created
        ), f"Only {qs_count} {current_model.__name__} were found for indexing, while at least {len(to_be_created)} were expected"

        logger.info(f"Indexing {qs_count} {current_model.__name__} new objects")
        search_bulk_index(current_model, qs)

        # Deleted
        qs = current_model.objects_with_deleted.filter(
            deleted=True, modified__gte=before_bulk_create
        )
        qs_count = qs.count()

        assert (
            qs_count >= deleted_rows
        ), f"Only {qs_count} {current_model.__name__} for deletion, while at least {deleted_rows} were expected"

        logger.info(f"Deleting {qs_count} {current_model.__name__} from elasticsearch")
        search_bulk_index(current_model, qs, action="delete")

    with transaction.atomic():
        for json_object, pk in tqdm(
            to_be_updated,
            disable=not to_be_updated,
            desc=f"Update or create for {current_model.__name__}",
        ):
            current_model.objects_with_deleted.update_or_create(
                pk=pk, defaults=json_object
            )


def make_id_map(cls: Type[SoftDeleteModelManager]) -> Dict[int, int]:
    return {int(i): j for i, j in cls.values_list("oparl_id", "id")}


def normalize_name(name: str) -> Tuple[str, str, str]:
    """Tries to extract given and family name from a string that might contain titles/form of address."""
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
        "oparl_id": str_or_none(json_agenda_item.original_id),
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
        "oparl_id": str_or_none(json_agenda_item.original_id),
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
        "oparl_id": str_or_none(json_meeting.original_id),
        "cancelled": False,
    }


def convert_paper(
    json_paper: json_datatypes.Paper, consultations: Dict[int, datetime]
) -> Dict[str, Any]:
    db_paper = {
        "short_name": json_paper.short_name[:50],  # TODO: Better normalization
        "name": json_paper.name,
        "reference_number": json_paper.reference,
        "oparl_id": str_or_none(json_paper.original_id),
        "sort_date": consultations.get(json_paper.original_id) or fallback_date,
        "display_date": (
            consultations.get(json_paper.original_id) or fallback_date
        ).date(),
    }
    if json_paper.paper_type:
        paper_type, created = models.PaperType.objects.get_or_create(
            paper_type=json_paper.paper_type
        )
        db_paper["paper_type_id"] = paper_type.id
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
        "body_id": body.id,
        "organization_type_id": committee_type.id,
        "oparl_id": str_or_none(oparl_id),
    }


def convert_file_to_paper(json_file, file_id_map, paper_id_map) -> Dict[str, Any]:
    return {
        "paper_id": paper_id_map[json_file.paper_original_id],
        "file_id": file_id_map[json_file.original_id],
    }


def convert_file(json_file) -> Dict[str, Any]:
    assert json_file.paper_original_id is not None
    return {
        "name": json_file.name[:200],  # TODO: Better normalization
        "oparl_download_url": json_file.url,
        "oparl_access_url": json_file.url,
        "oparl_id": str_or_none(json_file.original_id),
    }


def handle_counts(ris_data: RisData, allow_shrinkage: bool):
    """Prints the old and new counts and makes sure we don't accidentally delete entries"""

    def formatter(x):
        return " | ".join(f"{key_} {value_}" for key_, value_ in x.items())

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


def import_data(body: models.Body, ris_data: RisData):
    import_papers(ris_data)
    import_files(ris_data)
    paper_id_map = make_id_map(models.Paper.objects)
    file_id_map = make_id_map(models.File.objects)
    import_paper_files(ris_data, paper_id_map, file_id_map)
    import_organizations(body, ris_data)
    import_meeting_locations(ris_data)
    locations = dict(models.Location.objects.values_list("description", "id"))
    import_meetings(ris_data, locations)
    meeting_id_map = make_id_map(models.Meeting.objects.filter(oparl_id__isnull=False))
    organization_name_id_map = dict(
        models.Organization.objects.values_list("name", "id")
    )
    import_meeting_organization(meeting_id_map, organization_name_id_map, ris_data)
    import_persons(ris_data)
    import_consultations(ris_data, meeting_id_map, paper_id_map)
    # We don't have original ids for all agenda items (yet?),
    # so we just assume meeting x paper is unique
    consultation_map = {
        (a, b): c
        for a, b, c in models.Consultation.objects.values_list(
            "meeting_id", "paper_id", "id"
        )
    }
    # flush_model(models.AgendaItem) # It's incremental!
    import_agenda_items(ris_data, consultation_map, meeting_id_map, paper_id_map)
    import_memberships(ris_data)


def import_memberships(ris_data: RisData):
    logger.info(f"Importing {len(ris_data.memberships)} memberships")
    # TODO: Currently, the persons list is incomplete. This patches it up until that's solved
    #   properly by a rewrite of the relevant scraper part
    #   Use https://buergerinfo.ulm.de/kp0043.php?__swords=%22%22&__sgo=Suchen instead to get all persons and memberships
    #   at once and then use some custom id scheme where no original id exists
    person_name_map = {
        name: person_id
        for name, person_id in models.Person.objects.values_list("name", "id")
    }
    persons_fixup_done = set()
    for json_membership in ris_data.memberships:
        family_name, given_names, name = normalize_name(json_membership.person_name)
        if name not in person_name_map and name not in persons_fixup_done:
            models.Person(
                given_name=given_names, family_name=family_name, name=name
            ).save()
            persons_fixup_done.add(name)
    person_name_map = {
        name: person_id
        for name, person_id in models.Person.objects.values_list("name", "id")
    }
    # Assumption: Organizations that don't have an id in the overview page aren't linked anywhere
    organization_id_map = make_id_map(
        models.Organization.objects.filter(oparl_id__isnull=False)
    )

    objects = []
    for i in ris_data.memberships:
        person_id = person_name_map[normalize_name(i.person_name)[2]]
        organization = organization_id_map[i.organization_original_id]

        objects.append(
            {
                "person_id": person_id,
                "start": i.start_date,
                "end": i.end_date,
                "role": i.role,
                "organization_id": organization,
            }
        )
    incremental_import(models.Membership, objects)


def import_agenda_items(
    ris_data: RisData,
    consultation_map: Dict[Tuple[int, int], int],
    meeting_id_map: Dict[int, int],
    paper_id_map: Dict[int, int],
):
    logger.info(f"Processing {len(ris_data.agenda_items)} agenda items")

    objects = []
    for i in ris_data.agenda_items:
        objects.append(
            convert_agenda_item(i, consultation_map, meeting_id_map, paper_id_map)
        )

    # Handle the case where the start or name of a meeting with an id changed.
    db_data = models.AgendaItem.objects_with_deleted.filter(
        oparl_id__isnull=False
    ).values_list("oparl_id", "name")

    # We can ignore the None case
    oparl_id_to_name = {
        agenda_item["oparl_id"]: agenda_item["name"] for agenda_item in objects
    }
    for oparl_id, name in db_data:
        if oparl_id in oparl_id_to_name:
            if name != oparl_id_to_name[oparl_id]:
                models.AgendaItem.objects_with_deleted.filter(oparl_id=oparl_id).update(
                    name=oparl_id_to_name[oparl_id]
                )

    incremental_import(models.AgendaItem, objects)


def import_consultations(
    ris_data: RisData, meeting_id_map: Dict[int, int], paper_id_map: Dict[int, int]
):
    logger.info(f"Importing {len(ris_data.agenda_items)} consultations")

    objects = []
    for json_agenda_item in ris_data.agenda_items:
        if not json_agenda_item.paper_original_id:
            continue

        objects.append(
            convert_consultation(json_agenda_item, meeting_id_map, paper_id_map)
        )

    incremental_import(models.Consultation, objects)


def import_persons(ris_data: RisData):
    logger.info(f"Importing {len(ris_data.persons)} persons")

    persons = [normalize_name(json_person.name) for json_person in ris_data.persons]
    objects = [convert_person(i) for i in persons]

    incremental_import(models.Person, objects)


def import_meeting_organization(meeting_id_map, organization_name_id_map, ris_data):
    logger.info("Processing the meeting-organization-associations")
    objects = []
    for meeting in ris_data.meetings:
        associated_organization_id = organization_name_id_map.get(
            meeting.organization_name
        )

        if not associated_organization_id:
            continue

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

        objects.append(
            {
                "meeting_id": associated_meeting_id,
                "organization_id": associated_organization_id,
            }
        )
    incremental_import(models.Meeting.organizations.through, objects, soft_delete=False)


def import_meeting_locations(ris_data: RisData):
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
        db_location.save()
        db_locations[json_meeting.location] = db_location
    logger.info(f"Saving {len(db_locations)} new meeting locations")


def import_meetings(ris_data: RisData, locations: Dict[str, int]):
    logger.info(f"Importing {len(ris_data.meetings)} meetings")

    objects = []
    for i in ris_data.meetings:
        objects.append(convert_meeting(i, locations))

    # Handle the case where the start or name of a meeting with an id changed.
    db_data = models.Meeting.objects_with_deleted.filter(
        oparl_id__isnull=False
    ).values_list("start", "name", "oparl_id")

    # We can ignore the None case
    oparl_id_to_object = {meeting["oparl_id"]: meeting for meeting in objects}
    for start, name, oparl_id in db_data:
        if oparl_id in oparl_id_to_object:
            meeting_dict = oparl_id_to_object[oparl_id]
            if start != meeting_dict["start"] or name != meeting_dict["name"]:
                models.Meeting.objects_with_deleted.filter(oparl_id=oparl_id).update(
                    start=meeting_dict["start"], name=meeting_dict["name"]
                )

    incremental_import(models.Meeting, objects)


def import_organizations(body: models.Body, ris_data: RisData):
    logger.info(f"Importing {len(ris_data.organizations)} organizations")
    committee = settings.COMMITTEE_TYPE
    committee_type, _ = models.OrganizationType.objects.get_or_create(
        id=committee[0], defaults={"name": committee[1]}
    )

    # FIXME: Why does removing this check break the tests?
    if settings.ELASTICSEARCH_ENABLED:
        # We want to make the main organization - if known - to get the id 1 so that
        # the user doesn't need additional config
        if ris_data.main_organization and not models.Organization.objects.first():
            models.Organization(
                id=1,
                **convert_organization(
                    body, committee_type, ris_data.main_organization
                ),
            ).save()

    objects = []
    for i in ris_data.organizations:
        objects.append(convert_organization(body, committee_type, i))

    incremental_import(models.Organization, objects)


def import_paper_files(
    ris_data: RisData, paper_id_map: Dict[int, int], file_id_map: Dict[int, int]
):
    logger.info("Processing the file-paper-associations")

    # Remove manually deleted files
    manually_deleted = models.File.objects_with_deleted.filter(
        manually_deleted=True
    ).values_list("oparl_id", flat=True)

    objects = []
    for i in ris_data.files:
        if str(i.original_id) not in manually_deleted:
            objects.append(convert_file_to_paper(i, file_id_map, paper_id_map))

    incremental_import(models.Paper.files.through, objects, soft_delete=False)


def import_papers(ris_data: RisData):
    logger.info(f"Importing {len(ris_data.papers)} paper")

    # Heuristic to determine the sort date:
    # If there are consultations, use the date of the first consultation,
    # otherwise fall back to the year and month from the scraper (which
    # uses the date from the search)
    meetings = {meeting.original_id: meeting for meeting in ris_data.meetings}
    consultations = dict()
    for agenda_item in ris_data.agenda_items:
        paper_id = agenda_item.paper_original_id
        if paper_id in consultations:
            # We want the first consultation
            consultations[paper_id] = min(
                consultations[paper_id], meetings[agenda_item.meeting_id].start
            )
        else:
            consultations[paper_id] = meetings[agenda_item.meeting_id].start

    incremental_import(
        models.Paper, [convert_paper(i, consultations) for i in ris_data.papers]
    )


def import_files(ris_data: RisData):
    logger.info(f"Importing {len(ris_data.files)} files")

    incremental_import(models.File, [convert_file(i) for i in ris_data.files])
    # TODO: Move deleted files to a deleted bucket
