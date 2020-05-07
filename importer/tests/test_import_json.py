import inspect
import json
import logging
from pathlib import Path

import dateutil.parser
import pytest
from django.core import serializers

from importer.import_json import (
    import_data,
    make_id_map,
    convert_agenda_item,
    incremental_import,
)
from importer.json_datatypes import (
    RisData,
    converter,
    Meeting,
    Organization,
    RisMeta,
    Paper,
)
from mainapp import models
from mainapp.models import Body, DefaultFields

logger = logging.getLogger(__name__)

sample_city = RisMeta(
    name="Sample City",
    vendor="",
    url="https://example.org/ris/info.php",
    version=None,
    population=0,
    wikidata_item="",
    website="",
    ags="",
)


def load_ris_data(path: str) -> RisData:
    return converter.structure(json.loads(Path(path).read_text()), RisData)


def make_db_snapshot():
    snapshot = dict()
    for name, obj in inspect.getmembers(models):
        if (
            not inspect.isclass(obj)
            or not issubclass(obj, DefaultFields)
            or obj == DefaultFields
        ):
            continue
        snapshot[name] = sorted(
            list(i) for i in obj.objects_with_deleted.values_list("oparl_id", "deleted")
        )
    return snapshot


@pytest.mark.django_db
def test_import_json():
    old = load_ris_data("importer/test-data/amtzell_old.json")
    new = load_ris_data("importer/test-data/amtzell_new.json")

    body = Body(name=old.meta.name, short_name=old.meta.name, ags=old.meta.ags)
    body.save()

    import_data(body, old)

    actual = make_db_snapshot()
    expected = json.loads(Path("importer/test-data/amtzell_old_db.json").read_text())
    assert expected == actual

    import_data(body, new)

    actual = make_db_snapshot()
    expected = json.loads(Path("importer/test-data/amtzell_new_db.json").read_text())
    assert expected == actual

    # TODO: Check that the deleted file was correctly deleted
    # TODO: Run notifier and check that notifications were sent


@pytest.mark.django_db
def test_incremental_agenda_items():
    old = load_ris_data("importer/test-data/amtzell_old.json")
    new = load_ris_data("importer/test-data/amtzell_new.json")

    body = Body(name=old.meta.name, short_name=old.meta.name, ags=old.meta.ags)
    body.save()

    import_data(body, old)
    models.AgendaItem.objects_with_deleted.all().delete()

    # We don't have original ids for all agenda items (yet?),
    # so we just assume meeting x paper is unique
    consultation_map = {
        (a, b): c
        for a, b, c in models.Consultation.objects.values_list(
            "meeting_id", "paper_id", "id"
        )
    }

    meeting_id_map = make_id_map(models.Meeting.objects.filter(oparl_id__isnull=False))
    paper_id_map = make_id_map(models.Paper.objects)

    def convert_function(x):
        return convert_agenda_item(x, consultation_map, meeting_id_map, paper_id_map)

    incremental_import(
        models.AgendaItem, [convert_function(i) for i in old.agenda_items]
    )

    agenda_items = sorted(models.AgendaItem.objects.values_list("oparl_id", flat=True))
    agenda_items_with_deleted = sorted(
        models.AgendaItem.objects_with_deleted.values_list("oparl_id", flat=True)
    )
    assert agenda_items == ["1302", "1880"]
    assert agenda_items_with_deleted == ["1302", "1880"]

    incremental_import(
        models.AgendaItem, [convert_function(i) for i in new.agenda_items]
    )

    agenda_items = sorted(models.AgendaItem.objects.values_list("oparl_id", flat=True))
    agenda_items_with_deleted = sorted(
        models.AgendaItem.objects_with_deleted.values_list("oparl_id", flat=True)
    )
    assert agenda_items == ["1267", "1302"]
    assert agenda_items_with_deleted == ["1267", "1302", "1880"]


@pytest.mark.django_db
def test_meeting_start_change():
    """
    As there are meetings without an associated id, we can't use oparl_id as unique_id.
    But since name+start are unique in the db and the start of a meeting can be updated
    to the actual start after the meeting happened, we need to hard delete old meetings
    or the import will crash with a failed unque constraint
    """
    organizations = [Organization("City Council", 1, True)]
    meetings_old = [
        Meeting(
            "City Council",
            "City Council Meeting 1",
            None,
            None,
            None,
            start=dateutil.parser.parse("2020-01-01T09:00:00+01:00"),
        ),
        Meeting(
            "City Council",
            "City Council Meeting 2",
            None,
            None,
            2,
            start=dateutil.parser.parse("2020-02-01T09:00:00+01:00"),
        ),
    ]
    meetings_new = [
        Meeting(
            "City Council",
            "City Council Meeting 1",
            None,
            None,
            None,
            start=dateutil.parser.parse("2020-01-01T09:00:10+01:00"),
        ),
        Meeting(
            "City Council",
            "City Council Meeting 2",
            None,
            None,
            2,
            start=dateutil.parser.parse("2020-02-01T09:00:05+01:00"),
        ),
    ]
    old = RisData(sample_city, None, [], organizations, [], [], meetings_old, [], [], 2)
    new = RisData(sample_city, None, [], organizations, [], [], meetings_new, [], [], 2)
    body = Body(name=old.meta.name, short_name=old.meta.name, ags=old.meta.ags)
    body.save()

    import_data(body, old)
    import_data(body, new)

    assert models.Meeting.objects.count() == 2
    # The old meeting without id should have been deleted
    assert models.Meeting.objects_with_deleted.count() == 3


@pytest.mark.django_db
def test_undelete():
    """ A paper gets created, (spuriously?) deleted, and then undeleted """
    sample_paper = Paper("Antrag", "Stadtratsantrag", "2020/1", None, 38423)
    with_paper = RisData(sample_city, None, [], [], [sample_paper], [], [], [], [], 2)
    without_paper = RisData(sample_city, None, [], [], [], [], [], [], [], 2)
    body = Body(
        name=with_paper.meta.name,
        short_name=with_paper.meta.name,
        ags=with_paper.meta.ags,
    )
    body.save()

    import_data(body, with_paper)
    import_data(body, without_paper)
    import_data(body, with_paper)

    [paper] = models.Paper.objects_with_deleted.all()
    assert paper.deleted == False


@pytest.mark.parametrize(
    "fixture,target_number,target_number_with_deleted",
    [
        ("importer/fixtures/duplicate_meetings_with_id.json", 1, 2),
        ("importer/fixtures/duplicate_meetings_some_id.json", 1, 2),
    ],
)
@pytest.mark.django_db
def test_duplicate_meetings_with_id(fixture, target_number, target_number_with_deleted):
    """
    There are two meetings with the same name/start, and
        a) different ids,
        b) with and without id,
        c) without ids.
    Inspired by https://ris.wuppertal.de/si0057.php?__ksinr=18329 and
    https://ris.wuppertal.de/si0057.php?__ksinr=18837
    """

    for meeting in serializers.deserialize("json", Path(fixture).read_text()):
        meeting.save()

    new_meeting = converter.structure(
        {
            "organization_name": "BV Uellendahl-Katernberg",
            "name": "BV Uellendahl-Katernberg",
            "location": "Rathaus Barmen, Ratssaal, Johannes-Rau-Platz 1, 42275 Wuppertal",
            "note": None,
            "original_id": 18329,
            "start": "2020-04-23T18:30:00+02:00",
            "end": "2020-04-23T19:20:00+02:00",
            "cancelled": False,
        },
        Meeting,
    )

    with_paper = RisData(sample_city, None, [], [], [], [], [new_meeting], [], [], 2)
    body = Body(
        name=with_paper.meta.name,
        short_name=with_paper.meta.name,
        ags=with_paper.meta.ags,
    )
    body.save()

    import_data(body, with_paper)
    assert models.Meeting.objects.count() == target_number, list(
        models.Meeting.objects.values_list("oparl_id", "name", "start")
    )
    assert models.Meeting.objects_with_deleted.count() == target_number_with_deleted
