import json
import logging
import os
from datetime import date
from unittest import mock

import pytest
from django.test import TestCase

from importer.functions import externalize
from importer.json_to_db import JsonToDb
from importer.tests.utils import MockLoader, geocode
from importer.utils import Utils
from mainapp.models import (
    Paper,
    Location,
    LegislativeTerm,
    File,
    Consultation,
    AgendaItem,
    Membership,
    Body,
    Organization,
    Meeting,
    Person,
)

logger = logging.getLogger(__name__)


class TestImporter(TestCase):
    dummy_data = "testdata/oparl"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.api_data = {}
        cls.loader = MockLoader()
        cls.loader.api_data = cls.api_data
        for file in os.listdir(cls.dummy_data):
            if not file.endswith(".json"):
                continue

            with open(os.path.join(cls.dummy_data, file)) as fp:
                data = json.load(fp)
                cls.api_data[data["id"]] = data
                for entry in externalize(data):
                    if entry.data["id"] not in cls.api_data:
                        cls.api_data[entry.data["id"]] = entry.data

        # Used by test_location_default_body
        body = Body()
        body.short_name = "München"
        cls.converter = JsonToDb(cls.loader, default_body=body)
        cls.converter.warn_missing = False
        cls.utils = Utils()

    def test_init_base(self):
        data = {
            "id": "https://oparl.example.org/paper/0",
            "type": "https://schema.oparl.org/1.1/Paper",
            "name": "Rindfleischetikettierungsüberwachungsaufgabenübertragungsgesetz",
            "shortName": "RflEttÜAÜG",
            "deleted": True,
        }
        paper = Paper()
        self.converter.init_base(data, paper)
        self.assertEqual(paper.oparl_id, data["id"])
        self.assertEqual(
            paper.name,
            "Rindfleischetikettierungsüberwachungsaufgabenübertragungsgesetz",
        )
        self.assertEqual(paper.short_name, "RflEttÜAÜG")
        self.assertTrue(paper.deleted)

    @mock.patch("mainapp.functions.document_parsing.geocode", new=geocode)
    def test_location(self):
        location = Location()
        libobject = self.api_data["https://oparl.example.org/location/0"]
        self.converter.location(libobject, location)
        self.assertEqual(
            location.description,
            "Deutscher Bundestag, Platz der Republik 1, 11011 Berlin",
        )

        self.assertEqual(location.street_address, "Platz der Republik 1")
        self.assertEqual(location.postal_code, "11011")
        self.assertEqual(location.locality, "Berlin")
        self.assertEqual(location.room, "Plenarsaal")

        self.assertTrue(location.is_official)
        self.assertAlmostEqual(location.coordinates()["lat"], 52.518855)
        self.assertAlmostEqual(location.coordinates()["lon"], 13.376198)

    def test_location_default_body(self):
        """Test that the default body is used when locality isn't given"""
        city_center = {"coordinates": [48.1375, 11.575833], "type": "Point"}

        def geocode_city_center(search_str: str) -> dict:
            if search_str == "Marienplatz 1, München Deutschland":
                return city_center
            else:
                raise AssertionError(search_str)

        with mock.patch("importer.json_to_db.geocode", new=geocode_city_center):
            location = Location()
            libobject = {"streetAddress": "Marienplatz 1"}
            self.converter.location(libobject, location)
            self.assertEqual(location.geometry, city_center)

    def test_legislative_term(self):
        term = LegislativeTerm()
        data = self.api_data["https://oparl.example.org/term/21"]
        self.converter.legislative_term(data, term)
        self.assertEqual(term.start, date(year=2010, month=12, day=3))
        self.assertEqual(term.end, date(year=2013, month=12, day=3))

    def test_file(self):
        file = File()
        data = self.api_data["https://oparl.example.org/files/0"]
        self.converter.file(data, file)
        self.assertEqual(file.filename, "anlage_1_zur_anfrage.pdf")
        self.assertEqual(file.mime_type, "application/pdf")
        legal_date = date(year=2013, month=1, day=4)
        self.assertEqual(file.legal_date, legal_date)
        self.assertEqual(file.sort_date, self.utils.date_to_datetime(legal_date))
        self.assertEqual(file.filesize, None)
        self.assertEqual(file.page_count, None)
        self.assertEqual(file.parsed_text, None)
        self.assertEqual(file.license, "http://www.opendefinition.org/licenses/cc-by")
        self.assertEqual(file.oparl_access_url, "https://oparl.example.org/files/0.pdf")
        self.assertEqual(
            file.oparl_download_url,
            "https://oparl.example.org/files/download/57737.pdf",
        )

        data["text"] = "Lorem ipsum"
        self.converter.file(data, file)
        self.assertEqual(file.mime_type, "application/pdf")
        self.assertEqual(file.parsed_text, "Lorem ipsum")

    def test_consultation(self):
        consultation = Consultation()
        data = self.api_data["https://oparl.example.org/consultation/47594"]
        self.converter.consultation(data, consultation)
        self.assertEqual(consultation.meeting.name, "4. Sitzung des Finanzausschusses")
        self.assertEqual(consultation.paper.name, "Antwort auf Anfrage 1200/2014")
        self.assertTrue(consultation.authoritative)
        self.assertEqual(consultation.role, "Beschlussfassung")

    def test_agenda_item(self):
        item = AgendaItem()
        data = self.api_data["https://oparl.example.org/agendaitem/3271"]
        self.converter.agenda_item(data, item)
        self.assertEqual(item.key, "10.1")
        self.assertEqual(item.name, "Satzungsänderung für Ausschreibungen")
        self.assertEqual(item.meeting.name, "4. Sitzung des Finanzausschusses")
        self.assertEqual(item.consultation.role, "Beschlussfassung")
        self.assertEqual(item.position, 0)
        self.assertEqual(item.public, True)
        self.assertEqual(item.result, "Geändert beschlossen")
        self.assertEqual(
            item.resolution_text, "Der Beschluss weicht wie folgt vom Antrag ab: ..."
        )
        self.assertEqual(item.resolution_file.name, "Anlage 1 zur Anfrage")
        self.assertEqual(item.start, None)
        self.assertEqual(item.end, None)

    def test_membership(self):
        # Those were dropped between the tests
        self.converter.ensure_organization_type()
        # Body is mandatory for organization
        self.converter.import_anything("https://oparl.example.org/body/1")

        membership = Membership()
        data = self.api_data["https://oparl.example.org/membership/34"]
        self.converter.membership(data, membership)
        self.assertEqual(membership.person.name, "Prof. Dr. Max Mustermann")
        self.assertEqual(membership.start, date(2013, 12, 3))
        self.assertEqual(membership.end, None)
        self.assertEqual(membership.role, "Vorsitzende")
        self.assertEqual(membership.organization.short_name, "Finanzausschuss")

    def test_body(self):
        body = Body()
        data = self.api_data["https://oparl.example.org/body/1"]
        self.converter.body(data, body)
        self.assertEqual(body.outline, None)
        self.assertNotEqual(body.center, None)
        self.assertEqual(body.ags, "05315000")
        body.save()
        self.converter.body_related(data, body)
        self.assertEqual(body.legislative_terms.count(), 1)

    def test_paper(self):
        # Body is mandatory for organization
        self.converter.import_anything("https://oparl.example.org/body/1")
        self.converter.ensure_organization_type()

        paper = Paper()
        data = self.api_data["https://oparl.example.org/paper/749"]
        self.converter.paper(data, paper)
        self.assertEqual(paper.reference_number, "1234/2014")
        self.assertEqual(paper.change_request_of, None)
        self.assertEqual(paper.legal_date, date(2014, 4, 4))
        self.assertEqual(paper.sort_date, self.utils.date_to_datetime(date(2014, 4, 4)))
        self.assertEqual(paper.main_file.name, "Anlage 1 zur Anfrage")
        self.assertEqual(paper.paper_type.paper_type, "Beantwortung einer Anfrage")

        paper.save()
        self.converter.paper_related(data, paper)
        self.assertEqual(paper.files.first().name, "Anlage 2 zur Anfrage")
        self.assertEqual(paper.persons.count(), 1)

    def test_organization(self):
        # Body is mandatory for organization
        self.converter.import_anything("https://oparl.example.org/body/1")
        self.converter.ensure_organization_type()

        organization = Organization()
        data = self.api_data["https://oparl.example.org/organization/34"]
        self.converter.organization(data, organization)
        self.assertEqual(organization.start, date(2012, 7, 17))
        self.assertEqual(organization.end, None)
        self.assertEqual(organization.body.short_name, "Köln")
        self.assertTrue(organization.location.description.startswith("Rathaus"))
        self.assertEqual(organization.color, None)
        self.assertEqual(organization.logo, None)
        self.assertEqual(organization.organization_type.name, "committee")

    def test_organization_normalization(self):
        """Test for the normalization which was mainly built for cc-egov"""
        # Body is mandatory for organization
        self.converter.import_anything("https://oparl.example.org/body/1")
        self.converter.ensure_organization_type()

        organization = Organization()
        data = {
            "id": "https://oparl.example.org/organization/34",
            "type": "https://schema.oparl.org/1.1/Organization",
            "body": "https://oparl.example.org/body/1",
            "name": "Freibier-Fraktion",
            "organizationType": "Gremium",
            "classification": "Fraktion",
        }
        self.converter.init_base(data, organization)
        self.converter.organization(data, organization)
        self.assertEqual(organization.name, "Freibier-Fraktion")
        self.assertEqual(organization.short_name, "Freibier")
        self.assertEqual(organization.organization_type_id, 1)

    def test_meeting(self):
        # Body is mandatory for organization
        self.converter.import_anything("https://oparl.example.org/body/1")
        self.converter.ensure_organization_type()

        meeting = Meeting()
        data = self.api_data["https://oparl.example.org/meeting/281"]
        self.converter.meeting(data, meeting)
        self.assertEqual(meeting.cancelled, False)
        self.assertEqual(
            meeting.start, self.utils.parse_datetime("2013-01-04T08:00:00+01:00")
        )
        self.assertEqual(
            meeting.end, self.utils.parse_datetime("2013-01-04T12:00:00+01:00")
        )
        self.assertEqual(meeting.location.locality, "Berlin")
        self.assertEqual(meeting.invitation.filename, "einladung.pdf")
        self.assertEqual(meeting.results_protocol.filename, "protokoll.pdf")
        self.assertEqual(meeting.verbatim_protocol.filename, "wortprotokoll.pdf")
        self.assertEqual(meeting.public, 0)

        meeting.save()
        self.converter.meeting_related(data, meeting)
        self.assertEqual(meeting.organizations.count(), 1)
        self.assertEqual(meeting.persons.count(), 0)
        self.assertEqual(meeting.auxiliary_files.count(), 1)

    def test_person(self):
        # Body is mandatory for organization
        self.converter.import_anything("https://oparl.example.org/body/1")
        self.converter.ensure_organization_type()

        person = Person()
        data = self.api_data["https://oparl.example.org/person/29"]
        self.converter.person(data, person)
        self.assertEqual(person.name, "Prof. Dr. Max Mustermann")
        self.assertEqual(person.given_name, "Max")
        self.assertEqual(person.family_name, "Mustermann")
        self.assertEqual(person.location, None)


@pytest.mark.django_db
def test_json_to_db_missing_object(caplog):
    url = "https://lahr.ratsinfomanagement.net/webservice/oparl/v1.1/body/1/consultation/5999"
    loader = MockLoader(api_data={url: None})
    converter = JsonToDb(loader, default_body=Body(), ensure_organization_type=False)
    with pytest.raises(
        RuntimeError,
        match=rf"The object {url} is missing and the object type was not specified",
    ):
        converter.import_anything(url)
    converter.import_anything(url, Consultation)
    assert Consultation.objects.filter(oparl_id=url).count() == 1
    assert caplog.messages == [
        f"JSON loaded from {url} is not a dict/object. Using a dummy instead. THIS IS BAD",
        f"JSON loaded from {url} is not a dict/object. Using a dummy instead. THIS IS BAD",
    ]


@pytest.mark.django_db
def test_json_to_db_empty_object(caplog):
    url = "https://lahr.ratsinfomanagement.net/webservice/oparl/v1.1/body/1/consultation/5999"
    loader = MockLoader(api_data={url: {}})
    converter = JsonToDb(loader, default_body=Body(), ensure_organization_type=False)
    with pytest.raises(
        RuntimeError,
        match=f"The object {url} has not type field and object_type wasn't given",
    ):
        converter.import_anything(url)
    converter.import_anything(url, Consultation)
    assert Consultation.objects.filter(oparl_id=url).count() == 1
    assert caplog.messages == [
        f"Object loaded from {url} has no type field, inferred to https://schema.oparl.org/1.0/Consultation",
        f"Object loaded from {url} has no id field, setting id to url",
    ]
