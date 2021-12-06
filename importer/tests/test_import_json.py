import contextlib
import inspect
import json
import logging
from datetime import datetime
from pathlib import Path
from unittest import mock

import pytest
import responses
from django.contrib.auth.models import User
from django.core import serializers
from django.test import modify_settings, override_settings
from django.utils import timezone
from django_elasticsearch_dsl.registries import registry
from minio.error import MinioException

from importer.import_json import (
    import_data,
    make_id_map,
    convert_agenda_item,
    incremental_import,
)
from importer.importer import Importer
from importer.json_datatypes import (
    RisData,
    converter,
    Meeting,
    Organization,
    RisMeta,
    Paper,
    AgendaItem,
    Person,
    File,
)
from importer.loader import BaseLoader
from mainapp import models
from mainapp.functions.minio import minio_client, minio_file_bucket
from mainapp.functions.notify_users import NotifyUsers
from mainapp.functions.search import MainappSearch
from mainapp.models import Body, DefaultFields, UserAlert, UserProfile
from mainapp.tests.elasticsearch.test_elasticsearch import is_es_online
from mainapp.tests.utils import ElasticsearchMock, MinioMock

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

sample_paper = Paper(
    "Antrag",
    "Stadtratsantrag",
    "2020/1",
    None,
    datetime.fromisoformat("2020-01-01T00:00:00+01:00"),
    38423,
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


@override_settings(ELASTICSEARCH_ENABLED=is_es_online())
@modify_settings(INSTALLED_APPS={"append": "django_elasticsearch_dsl"})
@mock.patch("mainapp.functions.notify_users.send_mail")
@pytest.mark.django_db
def test_import_json(send_mail_function):
    """This test runs with elasticsearch if available and otherwise uses saved responses"""
    # Create the base state
    old = load_ris_data("importer/test-data/amtzell_old.json")
    body = Body(name=old.meta.name, short_name=old.meta.name, ags=old.meta.ags)
    body.save()

    import_data(body, old)

    actual = make_db_snapshot()
    expected = json.loads(Path("importer/test-data/amtzell_old_db.json").read_text())
    assert expected == actual

    last_notification = timezone.now()

    # Create notification
    user = User(username="JohnDoe", email="john.doe@example.org")
    user.save()
    UserProfile.objects.create(user=user)

    user_alert = UserAlert(
        user=user,
        search_string="Digitalisierungsstrategie",
        created=datetime.fromisoformat("2008-01-01T12:00:00+01:00"),
    )
    user_alert.save()

    # Import the new data
    new = load_ris_data("importer/test-data/amtzell_new.json")
    import_data(body, new)

    actual = make_db_snapshot()
    expected = json.loads(Path("importer/test-data/amtzell_new_db.json").read_text())
    assert expected == actual

    # Check that the notification was sent
    elasticsearch_mock = ElasticsearchMock(
        {
            "importer/test-data/notification_request.json": "importer/test-data/notification_response.json"
        }
    )
    if is_es_online():
        context = contextlib.nullcontext()
    else:
        context = mock.patch(
            "elasticsearch_dsl.search.get_connection",
            new=lambda _alias: elasticsearch_mock,
        )
    with context:
        if is_es_online():
            notifier = NotifyUsers(last_notification)
        else:
            notifier = NotifyUsers(
                datetime.fromisoformat("2020-05-17T12:07:37.887853+00:00")
            )
        notifier.notify_all()

        assert send_mail_function.call_count == 1
        assert send_mail_function.call_args[0][0] == "john.doe@example.org"
        assert "Digitalisierungsstrategie" in send_mail_function.call_args[0][2]
        assert "Digitalisierungsstrategie" in send_mail_function.call_args[0][3]

    # TODO: Check that the deleted file was correctly deleted


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
            start=datetime.fromisoformat("2020-01-01T09:00:00+01:00"),
        ),
        Meeting(
            "City Council",
            "City Council Meeting 2",
            None,
            None,
            2,
            start=datetime.fromisoformat("2020-02-01T09:00:00+01:00"),
        ),
    ]
    meetings_new = [
        Meeting(
            "City Council",
            "City Council Meeting 1",
            None,
            None,
            None,
            start=datetime.fromisoformat("2020-01-01T09:00:10+01:00"),
        ),
        Meeting(
            "City Council",
            "City Council Meeting 2",
            None,
            None,
            2,
            start=datetime.fromisoformat("2020-02-01T09:00:05+01:00"),
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
    """A paper gets created, (spuriously?) deleted, and then undeleted"""
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
    assert not paper.deleted


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


@pytest.mark.django_db
def test_agenda_item_with_id_name_changed():
    organizations = [Organization("City Council", 1, True)]
    meetings = [
        Meeting(
            "City Council",
            "City Council Meeting 1",
            None,
            None,
            1,
            start=datetime.fromisoformat("2020-01-01T09:00:00+01:00"),
        )
    ]

    agenda_items_old = [
        AgendaItem(
            key="1",
            position=0,
            name="Old name",
            meeting_id=1,
            paper_reference=None,
            paper_original_id=None,
            original_id=1,
            result=None,
            voting=None,
            note=None,
        )
    ]
    agenda_items_new = [
        AgendaItem(
            key="1",
            position=0,
            name="New name",
            meeting_id=1,
            paper_reference=None,
            paper_original_id=None,
            original_id=1,
            result=None,
            voting=None,
            note=None,
        )
    ]

    old = RisData(
        sample_city, None, [], organizations, [], [], meetings, [], agenda_items_old, 2
    )
    new = RisData(
        sample_city, None, [], organizations, [], [], meetings, [], agenda_items_new, 2
    )
    body = Body(name=old.meta.name, short_name=old.meta.name, ags=old.meta.ags)
    body.save()
    import_data(body, old)
    import_data(body, new)
    assert models.AgendaItem.objects_with_deleted.count() == 1
    assert models.AgendaItem.objects.count() == 1


@override_settings(ELASTICSEARCH_ENABLED=is_es_online())
@override_settings(ELASTICSEARCH_PREFIX="mst-test")
@modify_settings(INSTALLED_APPS={"append": "django_elasticsearch_dsl"})
@pytest.mark.skipif(not is_es_online(), reason="Elasticsearch is offline")
@pytest.mark.django_db
def test_index_deletion():
    """Check that deleted persons get deleted from the elasticsearch index"""
    for index in registry.get_indices(registry.get_models()):
        index.delete(ignore=404)
    for index in registry.get_indices(registry.get_models()):
        index.create()

    old_persons = [
        Person(name="Frank Underwood", party="Democrats"),
        Person(name="Claire Underwood", party="Democrats"),
    ]
    new_persons = [Person(name="Claire Underwood", party="Democrats")]

    old = RisData(sample_city, None, old_persons, [], [], [], [], [], [], 2)
    new = RisData(sample_city, None, new_persons, [], [], [], [], [], [], 2)
    body = Body(name=old.meta.name, short_name=old.meta.name, ags=old.meta.ags)
    body.save()

    import_data(body, old)
    assert len(MainappSearch({"query": "Underwood"}).execute().hits) == 2
    import_data(body, new)
    assert len(MainappSearch({"query": "Underwood"}).execute().hits) == 1


def make_sample_file(file_id, url):
    sample_file = File(
        name="Bad File",
        original_id=file_id,
        url=url,
        claimed_size=None,
        paper_original_id=sample_paper.original_id,
    )
    data = RisData(
        sample_city, None, [], [], [sample_paper], [sample_file], [], [], [], 2
    )
    body = Body(name=data.meta.name, short_name=data.meta.name, ags=data.meta.ags)
    body.save()
    import_data(body, data)
    return body, data


@mock.patch("mainapp.functions.minio._minio_singleton", new=MinioMock())
@pytest.mark.django_db
def test_manual_deletion(pytestconfig, caplog):
    """Check that after a file has been manually deleted, it can't get re-imported and it's gone from minio"""
    url = "https://example.org/file/1"
    file_id = 1
    body, data = make_sample_file(file_id, url)

    with responses.RequestsMock() as requests_mock:
        requests_mock.add(
            responses.GET,
            url,
            body=pytestconfig.rootpath.joinpath("testdata/media/file.txt").read_bytes(),
            status=200,
            content_type="text/plain",
        )
        importer = Importer(BaseLoader({}), force_singlethread=True)
        [successful, failed] = importer.load_files(sample_city.name)
        assert successful == 1 and failed == 0

    # Ensure that the file is there
    assert minio_client().get_object(minio_file_bucket, str(file_id))
    assert models.File.objects.filter(pk=file_id).first()

    # This is what we test
    models.File.objects.get(pk=file_id).manually_delete()

    with pytest.raises(MinioException):
        minio_client().get_object(minio_file_bucket, str(file_id))

    # Another import, to ensure that manually delete is respected
    import_data(body, data)

    assert not models.File.objects.filter(pk=file_id).first()
    with responses.RequestsMock():
        importer = Importer(BaseLoader({}), force_singlethread=True)
        [successful, failed] = importer.load_files(sample_city.name)
        assert successful == 0 and failed == 0

    with pytest.raises(MinioException):
        minio_client().get_object(minio_file_bucket, str(file_id))

    assert caplog.messages == [
        "File 1 has an unknown mime type: 'text/plain'",
        "File 1: Couldn't get any text",
    ]


@pytest.mark.django_db
def test_file_404(pytestconfig, caplog):
    """Check that after a file has been manually deleted, it can't get re-imported and it's gone from minio"""
    url = "https://example.org/file/1"
    file_id = 1
    make_sample_file(file_id, url)

    with responses.RequestsMock() as requests_mock:
        requests_mock.add(responses.GET, url, status=404, content_type="text/plain")
        importer = Importer(BaseLoader({}), force_singlethread=True)
        [successful, failed] = importer.load_files(sample_city.name, update=True)
        assert successful == 0 and failed == 1

    assert caplog.messages == [
        f"File 1: Failed to download {url}",
        "1 files failed to download",
    ]
