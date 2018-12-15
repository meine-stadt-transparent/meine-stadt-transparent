import hashlib
import json
import logging
import os
import shutil
import tempfile
from importlib.util import find_spec
from unittest import skipIf

from dateutil.relativedelta import relativedelta
from django.test import TestCase
from django.utils import timezone

from mainapp.models import (
    Body,
    LegislativeTerm,
    Organization,
    Person,
    OrganizationMembership,
    Meeting,
    AgendaItem,
    Paper,
    Consultation,
    Location,
    File,
)

gi_not_available = find_spec("gi") is None
if not gi_not_available:
    # Those two require importing gi
    from importer.oparl_helper import default_options
    from importer.oparl_import import OParlImport
    from importer.oparl_resolve import OParlResolver

logger = logging.getLogger(__name__)


@skipIf(gi_not_available, "gi is not available")
class TestImporter(TestCase):
    dummy_data = "testdata/oparl"
    fake_cache = "testdata/fake_cache"
    base_timestamp = timezone.now().astimezone().replace(microsecond=0)
    new_timestamp = None
    delete = False
    tables = [
        Body,
        LegislativeTerm,
        Organization,
        Person,
        OrganizationMembership,
        Meeting,
        AgendaItem,
        Paper,
        Consultation,
        Location,
    ]
    entrypoint = "https://oparl.example.org/"
    tempdir = None

    resolver = None  # Initializing here will lead to an import error without gi

    fixtures = ["cologne-pois-test"]

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tempdir = tempfile.mkdtemp()
        cls.options = cls.build_options()
        cls.resolver = OParlResolver(cls.entrypoint, cls.fake_cache, True)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tempdir)

    def sha1(self, data):
        return hashlib.sha1(data.encode("utf-8")).hexdigest()

    def load(self, name):
        with open(os.path.join(self.dummy_data, name)) as f:
            return self.manipulate(json.load(f), self.new_timestamp)

    def dump(self, name, obj):
        with open(
            os.path.join(self.fake_cache, self.sha1(self.entrypoint), self.sha1(name)),
            "w",
        ) as f:
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
        system = self.load("System.json")

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
        self.check_basic_import()
        self.check_ignoring_unmodified()
        self.check_update()
        self.check_deletion()

    def test_deletion(self):
        self.check_deletion()

    def test_update(self):
        self.check_update()

    def check_basic_import(self):
        self.new_timestamp = (
            self.base_timestamp + relativedelta(years=-100)
        ).isoformat()
        self.create_fake_cache()
        importer = OParlImport(self.options, self.resolver)
        importer.run_singlethread()
        now = timezone.now()

        for table in self.tables:
            self.assertEqual(table.objects.count(), 1)
            self.assertLess(table.objects.first().modified, now)
        self.assertEqual(File.objects.count(), 2)
        # Test for #56
        self.assertEqual(
            Meeting.by_oparl_id(
                "https://oparl.example.org/meeting/281"
            ).organizations.count(),
            1,
        )

    def check_ignoring_unmodified(self):
        """ Check that not-modified objects are ignored - See #41 """
        tables_with_modified = [
            Body,
            Organization,
            Person,
            Meeting,
            Paper,
            File,
        ]  # must have modified and File for #41
        newer_now = timezone.now()
        importer = OParlImport(self.options, self.resolver)
        importer.run_singlethread()
        for table in tables_with_modified:
            logger.debug(table.__name__)
            self.assertLess(table.objects.first().modified, newer_now)

    def check_update(self):
        now = timezone.now()
        self.new_timestamp = (self.base_timestamp + relativedelta(years=10)).isoformat()
        self.create_fake_cache()
        importer = OParlImport(self.options, self.resolver)
        importer.run_singlethread()
        for table in self.tables:
            self.assertEqual(table.objects.count(), 1)
            self.assertGreater(table.objects.first().modified, now)
        self.assertEqual(File.objects.count(), 2)

    def check_deletion(self):
        self.new_timestamp = (
            self.base_timestamp + relativedelta(years=200)
        ).isoformat()
        self.delete = True
        self.create_fake_cache()
        importer = OParlImport(self.options, self.resolver)
        importer.run_singlethread()
        tables = self.tables[:]
        tables.remove(Body)
        for table in tables:
            self.assertEqual(table.objects.count(), 0)

    @classmethod
    def build_options(cls):
        options = default_options.copy()
        options["cachefolder"] = cls.fake_cache
        options["storagefolder"] = os.path.join(cls.tempdir, "storagefolder")
        shutil.rmtree(options["storagefolder"], ignore_errors=True)
        options["entrypoint"] = cls.entrypoint
        options["batchsize"] = 1
        options["download_files"] = False  # TODO
        return options

    def tearDown(self):
        shutil.rmtree(self.fake_cache, ignore_errors=True)
