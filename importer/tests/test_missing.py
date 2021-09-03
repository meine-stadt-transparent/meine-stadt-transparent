"""
As of today (2020) most OParl apis are broken by missing objects. We try to
patch those up with dummies.
"""

import json

import pytest
from responses import RequestsMock

from importer.importer import Importer
from importer.loader import BaseLoader
from mainapp.models import Organization, Person

empty_page = {"data": [], "links": {}, "pagination": {}}


# noinspection HttpUrlsUsage
@pytest.mark.django_db
def test_missing_organization(pytestconfig, caplog):
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
                    json.loads(
                        pytestconfig.rootpath.joinpath(
                            "testdata/oparl-missing/body.json"
                        ).read_text()
                    )
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
                    json.loads(
                        pytestconfig.rootpath.joinpath(
                            "testdata/oparl-missing/meeting.json"
                        ).read_text()
                    )
                ],
                "links": {},
                "pagination": {},
            },
        )
        requests_mock.add(
            requests_mock.GET,
            "http://oparl.wuppertal.de/oparl/bodies/0001/people/292",
            status=404,
        )

        body_id = "http://oparl.wuppertal.de/oparl/bodies/0001"
        importer = Importer(
            BaseLoader(
                json.loads(
                    pytestconfig.rootpath.joinpath(
                        "testdata/oparl-missing/system.json"
                    ).read_text()
                )
            ),
            force_singlethread=True,
        )
        [body_data] = importer.load_bodies(body_id)
        [body] = importer.import_bodies()
        importer.converter.default_body = body
        body.ags = "05124000"
        importer.fetch_lists_initial([body_data.data])
        importer.import_objects()

        assert {i.oparl_id for i in Organization.objects.all()} == {
            "http://oparl.wuppertal.de/oparl/bodies/0001/organizations/gr/230",
            "http://oparl.wuppertal.de/oparl/bodies/0001/organizations/gr/231",
        }

        assert list(i.short_name for i in Organization.objects.all()) == [
            "Missing",
            "Missing",
        ]

    assert Person.objects.first().name == "Missing Person"
    assert caplog.messages == [
        "The Person http://oparl.wuppertal.de/oparl/bodies/0001/people/292 linked "
        "from http://oparl.wuppertal.de/oparl/bodies/0001/meetings/19160 was supposed "
        "to be a part of the external lists, but was not. This is a bug in the OParl "
        "implementation.",
        "Failed to load http://oparl.wuppertal.de/oparl/bodies/0001/people/292. Using "
        "a dummy instead. THIS IS BAD: 404 Client Error: Not Found for url: "
        "http://oparl.wuppertal.de/oparl/bodies/0001/people/292",
        "The Organization "
        "http://oparl.wuppertal.de/oparl/bodies/0001/organizations/gr/230 linked from "
        "http://oparl.wuppertal.de/oparl/bodies/0001/meetings/19160 was supposed to "
        "be a part of the external lists, but was not. This is a bug in the OParl "
        "implementation.",
        "Failed to load "
        "http://oparl.wuppertal.de/oparl/bodies/0001/organizations/gr/230. Using a "
        "dummy instead. THIS IS BAD: 404 Client Error: Not Found for url: "
        "http://oparl.wuppertal.de/oparl/bodies/0001/organizations/gr/230",
        "The Organization "
        "http://oparl.wuppertal.de/oparl/bodies/0001/organizations/gr/231 linked from "
        "http://oparl.wuppertal.de/oparl/bodies/0001/meetings/19160 was supposed to "
        "be a part of the external lists, but was not. This is a bug in the OParl "
        "implementation.",
        "Failed to load "
        "http://oparl.wuppertal.de/oparl/bodies/0001/organizations/gr/231. Using a "
        "dummy instead. THIS IS BAD: 404 Client Error: Not Found for url: "
        "http://oparl.wuppertal.de/oparl/bodies/0001/organizations/gr/231",
    ]
