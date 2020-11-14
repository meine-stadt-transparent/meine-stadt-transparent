"""
As of today (2020) most OParl apis are broken by missing objects. We try to
patch those up with dummies.
"""

import json
from pathlib import Path

import pytest
from responses import RequestsMock

from importer.importer import Importer
from importer.loader import BaseLoader
from mainapp.models import Organization

empty_page = {"data": [], "links": {}, "pagination": {}}

# TODO: Also handle and test missing persons
person_292 = {
    "id": "http://oparl.wuppertal.de/oparl/bodies/0001/people/292",
    "type": "https://schema.oparl.org/1.0/Person",
    "body": "http://oparl.wuppertal.de/oparl/bodies/0001",
    "name": "Tobias Wierzba",
    "familyName": "Wierzba",
    "givenName": "Tobias",
    "formOfAdress": "Herr",
    "gender": "männlich",
    "membership": [],
    "created": "2017-12-21T08:21:05+01:00",
    "modified": "2020-11-09T11:23:31+01:00",
    "web": "",
}


@pytest.mark.django_db
def test_missing_organization():
    with RequestsMock() as requests_mock:
        requests_mock.add(
            requests_mock.GET,
            "http://oparl.wuppertal.de/oparl/bodies/0001/organizations/gr/230",
            json={"error": "not found"},
            status=404,
        )
        # Add another one to test for uniqueness constraints
        requests_mock.add(
            requests_mock.GET,
            "http://oparl.wuppertal.de/oparl/bodies/0001/organizations/gr/231",
            json={"error": "not found"},
            status=404,
        )

        requests_mock.add(
            requests_mock.GET,
            "http://oparl.wuppertal.de/oparl/bodies",
            json={
                "data": [
                    json.loads(Path("testdata/oparl-missing/body.json").read_text())
                ],
                "links": {},
                "pagination": {},
            },
        )
        requests_mock.add(
            requests_mock.GET,
            "http://oparl.wuppertal.de/oparl/bodies/0001/organizations",
            json=empty_page,
        )
        requests_mock.add(
            requests_mock.GET,
            "http://oparl.wuppertal.de/oparl/bodies/0001/people",
            json=empty_page,
        )
        requests_mock.add(
            requests_mock.GET,
            "http://oparl.wuppertal.de/oparl/bodies/0001/papers",
            json=empty_page,
        )
        requests_mock.add(
            requests_mock.GET,
            "http://oparl.wuppertal.de/oparl/bodies/0001/meetings",
            json={
                "data": [
                    json.loads(Path("testdata/oparl-missing/meeting.json").read_text())
                ],
                "links": {},
                "pagination": {},
            },
        )
        requests_mock.add(
            requests_mock.GET,
            "http://oparl.wuppertal.de/oparl/bodies/0001/people/292",
            json=person_292,
        )

        body_id = "http://oparl.wuppertal.de/oparl/bodies/0001"
        importer = Importer(
            BaseLoader(
                json.loads(Path("testdata/oparl-missing/system.json").read_text())
            ),
            force_singlethread=True,
        )
        [body_data] = importer.load_bodies(body_id)
        [body] = importer.import_bodies()
        importer.converter.default_body = body
        body.ags = "05124000"
        importer.fetch_lists_initial([body_data.data])
        importer.import_objects()

        assert set(i.oparl_id for i in Organization.objects.all()) == {
            "http://oparl.wuppertal.de/oparl/bodies/0001/organizations/gr/230",
            "http://oparl.wuppertal.de/oparl/bodies/0001/organizations/gr/231",
        }

        assert list(i.short_name for i in Organization.objects.all()) == [
            "Missing",
            "Missing",
        ]
