import json
import logging
import os

from dateutil.relativedelta import relativedelta
from django.test import TestCase
from django.utils import timezone

from importer.importer import Importer
from importer.tests.utils import MockLoader
from mainapp.models import (
    Body,
    LegislativeTerm,
    Organization,
    Person,
    Membership,
    Meeting,
    AgendaItem,
    Paper,
    Consultation,
    Location,
    File,
)

logger = logging.getLogger(__name__)


class TestDataset(TestCase):
    dummy_data = "testdata/oparl"
    base_timestamp = timezone.now().astimezone().replace(microsecond=0)
    new_timestamp = None
    minio_mock = None
    delete = False
    tables = {
        Body: 1,
        LegislativeTerm: 1,
        Organization: 1,
        Person: 1,
        Membership: 1,
        Meeting: 1,
        AgendaItem: 1,
        Paper: 1,
        Consultation: 1,
        Location: 2,
    }
    body_id = "https://oparl.example.org/body/1"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.loader = MockLoader()

    def load(self, name):
        with open(os.path.join(self.dummy_data, name)) as f:
            return self.manipulate(json.load(f), self.new_timestamp)

    def dump(self, name, obj):
        self.loader.api_data[name] = obj

    def external_list(self, obj):
        return {"data": [obj], "links": {}, "pagination": {}}

    def manipulate(self, obj, new_value: str):
        if self.delete:
            obj["deleted"] = True

        for key, value in obj.items():
            if key == "modified" or key == "created":
                obj[key] = new_value
            if isinstance(value, list):
                for i in value:
                    if isinstance(i, dict):
                        self.manipulate(i, new_value)
            if isinstance(value, dict):
                self.manipulate(value, new_value)
        return obj

    def init_mock_loader(self):
        """Fakes an oparl server by a creating a prefilled cache."""
        system = self.load("System.json")
        self.loader.system = system

        self.dump(system["id"], system)
        body = self.load("Body.json")
        # If we deleted the body, the other objects won't be imported
        body["deleted"] = False
        self.dump(system["body"], self.external_list(body))
        self.dump(body["id"], body)

        organization = self.load("Organization.json")
        self.dump(body["organization"], self.external_list(organization))
        person = self.load("Person.json")
        self.dump(body["person"], self.external_list(person))
        meeting = self.load("Meeting.json")
        self.dump(body["meeting"], self.external_list(meeting))
        paper = self.load("Paper.json")
        self.dump(body["paper"], self.external_list(paper))

        self.dump(meeting["id"], meeting)
        self.dump(person["id"], person)

        consultation = paper["consultation"][0]
        self.dump(consultation["id"], consultation)

        item = meeting["agendaItem"][0]
        self.dump(item["id"], item)

        membership = person["membership"][0].copy()
        membership["person"] = person["id"]
        self.dump(membership["id"], membership)

        location = meeting["location"]
        self.dump(location["id"], location)

    def test_importer(self):
        self.check_basic_import()
        self.check_ignoring_unmodified()
        self.check_update()
        self.check_deletion()

    def test_deletion(self):
        self.check_basic_import()
        self.check_deletion()

    def check_basic_import(self):
        self.new_timestamp = (
            self.base_timestamp + relativedelta(years=-100)
        ).isoformat()
        self.init_mock_loader()
        importer = Importer(self.loader, force_singlethread=True)
        importer.run(self.body_id)
        now = timezone.now()

        for table, count in self.tables.items():
            self.assertEqual(
                table.objects.count(),
                count,
                f"{table}: {count} vs. {table.objects.all()}",
            )
            self.assertLess(table.objects.first().modified, now)
        self.assertEqual(File.objects.count(), 6)
        # Test for #56
        self.assertEqual(
            Meeting.by_oparl_id(
                "https://oparl.example.org/meeting/281"
            ).organizations.count(),
            1,
        )

    def check_ignoring_unmodified(self):
        """Check that not-modified objects are ignored"""
        tables_with_modified = [
            Body,
            Organization,
            Person,
            Meeting,
            Paper,
            File,
        ]  # must have modified and File for #41
        newer_now = timezone.now()
        importer = Importer(self.loader, force_singlethread=True)
        importer.update(self.body_id)
        for table in tables_with_modified:
            logger.debug(table.__name__)
            self.assertLess(table.objects.first().modified, newer_now)

    def check_update(self):
        self.new_timestamp = (self.base_timestamp + relativedelta(years=10)).isoformat()
        self.init_mock_loader()
        importer = Importer(self.loader, force_singlethread=True)
        importer.update(self.body_id)
        for table, count in self.tables.items():
            self.assertEqual(
                table.objects.count(),
                count,
                f"{table}: {count} vs. {table.objects.all()}",
            )
        self.assertEqual(File.objects.count(), 6)

    def check_deletion(self):
        self.new_timestamp = (
            self.base_timestamp + relativedelta(years=200)
        ).isoformat()
        self.delete = True
        self.init_mock_loader()
        importer = Importer(self.loader, force_singlethread=True)
        importer.update(self.body_id)
        for table, count in self.tables.items():
            # It doesn't make sense if our Body was deleted
            if table == Body:
                continue

            # We use minus one because we only deleted the top level objects
            self.assertEqual(
                table.objects.count(), count - 1, f"{table} {table.objects.all()}"
            )
