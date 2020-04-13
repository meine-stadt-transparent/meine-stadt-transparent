import inspect
import json
import logging
from pathlib import Path

import pytest

from importer.import_json import (
    import_data,
    make_id_map,
    convert_agenda_item,
    incremental_import,
)
from importer.json_datatypes import RisData, converter
from mainapp import models
from mainapp.models import Body, DefaultFields

logger = logging.getLogger(__name__)


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