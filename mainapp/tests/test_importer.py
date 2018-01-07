import hashlib
import importlib.util
import json
import logging
import os
import shutil
from unittest import skipIf

from django.test import TestCase
from django.utils import timezone

from mainapp.models import Body, LegislativeTerm, Organization, Person, OrganizationMembership, Meeting, AgendaItem, \
    Paper, Consultation, Location, File

gi_not_available = importlib.util.find_spec("gi") is None
if not gi_not_available:
    # Those two require importing gi
    from importer.oparl_helper import default_options
    from importer.oparl_import import OParlImport

logger = logging.getLogger(__name__)


@skipIf(gi_not_available, "gi is not available")
class TestImporter(TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.new_timestamp = None
        self.delete = False
        self.dummy_data = "testdata/oparl"
        self.fake_cache = "testdata/fake_cache"
        self.entrypoint = None

    def sha1(self, data):
        return hashlib.sha1(data.encode("utf-8")).hexdigest()

    def load(self, name):
        with open(os.path.join(self.dummy_data, name)) as f:
            return self.manipulate(json.load(f), self.new_timestamp)

    def dump(self, name, obj):
        with open(os.path.join(self.fake_cache, self.sha1(self.entrypoint), self.sha1(name)), 'w') as f:
            json.dump(obj, f, indent=4, sort_keys=True)

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

    def create_fake_cache(self):
        """ Fakes an oparl server by a creating a prefilled cache. """
        # Load the entrypoint first, we need the id for the remaining setup
        system = self.load("System.json")
        self.entrypoint = system["id"]

        # Discard old data
        shutil.rmtree(self.fake_cache, ignore_errors=True)
        os.makedirs(os.path.join(self.fake_cache, self.sha1(self.entrypoint)))

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

    def test_importer(self):
        self.new_timestamp = "2000-01-01T00:00:00+01:00"
        self.create_fake_cache()
        options = self.build_options()
        importer = OParlImport(options)
        importer.run_singlethread()

        now = timezone.now()

        tables = [Body, LegislativeTerm, Organization, Person, OrganizationMembership, Meeting, AgendaItem, Paper,
                  Consultation, Location]

        for table in tables:
            self.assertEqual(table.objects.count(), 1)
            self.assertLess(table.objects.first().modified, now)

        self.assertEqual(File.objects.count(), 2)

        # Check that not-modified objects are ignored - See #41
        tables_with_modified = [Body, Organization, Person, Meeting, Paper, File]  # must have modified and File for #41

        newer_now = timezone.now()
        importer = OParlImport(options)
        importer.run_singlethread()

        for table in tables_with_modified:
            logger.debug(table.__name__)
            self.assertLess(table.objects.first().modified, newer_now)

        self.new_timestamp = "2020-01-01T00:00:00+01:00"  # Fixme: Not futureproof
        self.create_fake_cache()
        importer = OParlImport(options)
        importer.run_singlethread()

        for table in tables:
            self.assertEqual(table.objects.count(), 1)
            self.assertGreater(table.objects.first().modified, now)

        self.assertEqual(File.objects.count(), 2)

        self.new_timestamp = "2030-01-01T00:00:00+01:00"
        self.delete = True
        self.create_fake_cache()
        importer = OParlImport(options)
        importer.run_singlethread()

        tables.remove(Body)

        for table in tables:
            self.assertEqual(table.objects.count(), 0)

    def build_options(self):
        options = default_options.copy()
        options["cachefolder"] = self.fake_cache
        options["storagefolder"] = "/tmp/meine_stadt_transparent/storagefolder"
        shutil.rmtree(options["storagefolder"], ignore_errors=True)
        options["entrypoint"] = self.entrypoint
        options["batchsize"] = 1
        options["download_files"] = False  # TODO
        return options

    def tearDown(self):
        shutil.rmtree(self.fake_cache, ignore_errors=True)
