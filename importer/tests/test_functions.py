import pytest
from django.test import TestCase

from importer import json_to_db
from importer.functions import externalize
from importer.importer import Importer
from importer.json_to_db import JsonToDb
from importer.tests.utils import MockLoader
from importer.utils import Utils
from mainapp.models import Membership, Person, Organization

test_data_dir = "testdata/oparl2"


class TestFunctions(TestCase):
    def test_externalize(self):
        sample_organization = {
            "id": "https://ratsinfo.leipzig.de/bi/oparl/1.0/organizations.asp?typ=gr&id=2286",
            "type": "https://schema.oparl.org/1.0/Organization",
            "name": "Beirat für Psychiatrie",
            "startDate": "2000-01-01",
            "endDate": "",
            "meeting": "https://ratsinfo.leipzig.de/bi/oparl/1.0/meetings.asp?organization=2286",
            "membership": [
                "https://ratsinfo.leipzig.de/bi/oparl/1.0/memberships.asp?typ=mg&id=1414"
            ],
            "location": {
                "id": "https://ratsinfo.leipzig.de/bi/oparl/1.0/locations.asp?id=32286",
                "type": "https://schema.oparl.org/1.0/Location",
                "description": "Friedrich-Ebert-Str. 19a, 04109 Leipzig",
                "street_address": "Friedrich-Ebert-Str. 19a",
                "postal_code": "04109",
                "subLocality": "",
                "locality": "Leipzig",
            },
            "created": "2000-01-01T12:00:00+01:00",
            "modified": "2018-04-10T12:14:31+02:00",
        }

        [location, organization] = list(externalize(sample_organization))
        self.assertEqual(organization.data["location"], location.data["id"])

    def test_normalize_body_name(self):
        utils = Utils()
        self.assertEqual("Bedburg", utils.normalize_body_name("Stadt  Bedburg"))
        self.assertEqual("Leipzig", utils.normalize_body_name("Leipzig"))
        self.assertEqual(
            "Bad Münstereifel", utils.normalize_body_name("Stadt Bad  Münstereifel ")
        )

    def test_person_only_name(self):
        data = {
            "id": "https://oparl.example.org/person/only-name",
            "type": "https://schema.oparl.org/1.1/Person",
            "name": "Max Mustermann",
            "created": "2011-11-11T11:11:00+01:00",
            "modified": "2012-08-16T14:05:27+02:00",
        }

        converter = JsonToDb(MockLoader())

        with self.assertLogs(json_to_db.__name__, level="WARNING") as cm:
            person = Person()
            converter.person(data, person)
            self.assertEqual(person.name, "Max Mustermann")
            self.assertEqual(person.given_name, "Max")
            self.assertEqual(person.family_name, "Mustermann")

            self.assertEqual(
                cm.output,
                [
                    "WARNING:"
                    + json_to_db.__name__
                    + ":Inferring given and family name from compound name"
                ],
            )

    def test_person_no_name(self):
        data = {
            "id": "https://oparl.example.org/person/no-name",
            "type": "https://schema.oparl.org/1.1/Person",
            "created": "2011-11-11T11:11:00+01:00",
            "modified": "2012-08-16T14:05:27+02:00",
        }

        converter = JsonToDb(MockLoader())

        with self.assertLogs(json_to_db.__name__, level="WARNING") as cm:
            person = Person()
            converter.person(data, person)
            self.assertEqual(
                cm.output,
                [
                    "WARNING:"
                    + json_to_db.__name__
                    + ":Person without name: https://oparl.example.org/person/no-name",
                    "WARNING:"
                    + json_to_db.__name__
                    + ":Person without given name: https://oparl.example.org/person/no-name",
                    "WARNING:"
                    + json_to_db.__name__
                    + ":Person without family name: https://oparl.example.org/person/no-name",
                ],
            )

    def test_membeship_get_or_load(self):
        """Sometimes main objects are not in the external lists.

        Also check that cycles (between Membership and Person are resolved)"""
        membership = {
            "id": "https://oparl.example.org/membership/0",
            "type": "https://schema.oparl.org/1.1/Membership",
            "person": "https://oparl.example.org/person/1",
            "organization": "https://oparl.example.org/organization/1",
            "created": "2011-11-11T11:11:00+01:00",
            "modified": "2012-08-16T14:05:27+02:00",
        }
        data = [
            membership,
            {
                "id": "https://oparl.example.org/body/1",
                "type": "https://schema.oparl.org/1.1/Body",
                "system": "https://oparl.example.org/",
                "shortName": "Köln",
                "name": "Stadt Köln, kreisfreie Stadt",
                "created": "2014-01-08T14:28:31+01:00",
                "modified": "2014-01-08T14:28:31+01:00",
            },
            {
                "id": "https://oparl.example.org/organization/1",
                "type": "https://schema.oparl.org/1.1/Organization",
                "body": "https://oparl.example.org/body/1",
                "name": "Ausschuss für Haushalt und Finanzen",
                "shortName": "Finanzausschuss",
                "membership": ["https://oparl.example.org/membership/1"],
                "created": "2012-07-16T00:00:00+02:00",
                "modified": "2012-08-16T12:34:56+02:00",
            },
            {
                "id": "https://oparl.example.org/person/1",
                "type": "https://schema.oparl.org/1.1/Person",
                "body": "https://oparl.example.org/body/1",
                "name": "Prof. Dr. Max Mustermann",
                "familyName": "Mustermann",
                "givenName": "Max",
                "membership": [
                    {
                        "id": "https://oparl.example.org/membership/1",
                        "type": "https://schema.oparl.org/1.1/Membership",
                        "organization": "https://oparl.example.org/organization/1",
                        "role": "Vorsitzende",
                        "votingRight": True,
                        "startDate": "2013-12-03",
                    }
                ],
                "created": "2011-11-11T11:11:00+01:00",
                "modified": "2012-08-16T14:05:27+02:00",
            },
        ]

        loader = MockLoader()
        for oparl_object in data:
            loader.api_data[oparl_object["id"]] = oparl_object

        importer = Importer(loader)
        importer.converter.warn_missing = False
        # We need to have a body to load an organization
        importer.import_anything("https://oparl.example.org/body/1")
        importer.import_anything("https://oparl.example.org/membership/0")
        self.assertEqual(
            Membership.objects.filter(oparl_id=membership["id"]).count(), 1
        )
        self.assertEqual(Person.objects.count(), 1)
        self.assertEqual(Organization.objects.count(), 1)


@pytest.mark.django_db
def test_fetch_list_update():
    loader = MockLoader()
    loader.api_data["https://oparl.wuppertal.de/oparl/bodies/0001/papers"] = {
        "data": [],
        "links": {},
        "pagination": {},
    }
    importer = Importer(loader)
    importer.fetch_list_initial("https://oparl.wuppertal.de/oparl/bodies/0001/papers")
    importer.fetch_list_update("https://oparl.wuppertal.de/oparl/bodies/0001/papers")


def test_externalize_missing_id(caplog):
    """In http://buergerinfo.ulm.de/oparl/bodies/0001/meetings/11445, the embedded location does not have an id"""
    json_in = {
        "id": "http://buergerinfo.ulm.de/oparl/bodies/0001/meetings/11445",
        "type": "https://schema.oparl.org/1.1/Meeting",
        "name": "Klausurtagung des Gemeinderats",
        "start": "2021-06-12T09:00:00+02:00",
        "end": "2021-06-12T00:00:00+02:00",
        "location": {"description": "Ulm-Messe,"},
        "organization": [
            "http://buergerinfo.ulm.de/oparl/bodies/0001/organizations/gr/1"
        ],
        "created": "2020-11-11T09:47:04+01:00",
        "modified": "2020-11-11T09:48:13+01:00",
    }
    # Check that location has been removed but everything else remained the same
    json_out = json_in.copy()
    del json_out["location"]

    externalized = externalize(json_in)
    assert len(externalized) == 1
    assert externalized[0].data == json_out
    assert caplog.messages == [
        "Embedded object 'location' in "
        "http://buergerinfo.ulm.de/oparl/bodies/0001/meetings/11445 does not have an "
        "id, skipping: {'description': 'Ulm-Messe,'}"
    ]
