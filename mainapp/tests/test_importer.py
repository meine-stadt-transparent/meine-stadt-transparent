import hashlib
import json
import os
import shutil

from django.test import TestCase

from importer.oparl_helper import default_options
from importer.oparl_import import OParlImport


def sha1(data):
    return hashlib.sha1(data.encode("utf-8")).hexdigest()


class TestImporter(TestCase):
    dummy_data = "testdata/oparl"
    fake_cache = "testdata/fake_cache"
    entrypoint = None

    def load(self, name):
        with open(os.path.join(self.dummy_data, name)) as f:
            return json.load(f)

    def dump(self, name, obj):
        with open(os.path.join(self.fake_cache, sha1(self.entrypoint), name), 'w') as f:
            json.dump(obj, f, indent=4)

    def external_list(self, obj):
        return {"data": [obj], "links": {}, "pagination": {}}

    def setUp(self):
        """ Fakes an oparl server by a creating a prefilled cache. """
        # Load the entrypoint first, we need the id for the remaining setup
        system = self.load("System.json")
        self.entrypoint = system["id"]

        # Discard old data
        if os.path.isdir(self.fake_cache):
            shutil.rmtree(self.fake_cache)
        os.makedirs(os.path.join(self.fake_cache, sha1(self.entrypoint)))

        self.dump(sha1(system["id"]), system)
        body = self.load("Body.json")
        self.dump(sha1(system["body"]), self.external_list(body))
        self.dump(sha1(body["id"]), body)

        organization = self.load("Organization.json")
        self.dump(sha1(body["organization"]), self.external_list(organization))
        person = self.load("Person.json")
        self.dump(sha1(body["person"]), self.external_list(person))
        meeting = self.load("Meeting.json")
        self.dump(sha1(body["meeting"]), self.external_list(meeting))
        paper = self.load("Paper.json")
        self.dump(sha1(body["paper"]), self.external_list(paper))

        self.dump(sha1(meeting["id"]), meeting)
        self.dump(sha1(person["id"]), person)

        consultation = paper["consultation"][0]
        self.dump(sha1(consultation["id"]), consultation)

        item = meeting["agendaItem"][0]
        self.dump(sha1(item["id"]), item)

        membership = person["membership"][0].copy()
        membership["person"] = person["id"]
        self.dump(sha1(membership["id"]), membership)

    def test_importer(self):
        options = default_options.copy()
        options["cachefolder"] = self.fake_cache
        options["storagefolder"] = "/tmp/meine_stadt_transparent/storagefolder"
        if os.path.isdir(options["storagefolder"]):
            shutil.rmtree(options["storagefolder"])
        options["entrypoint"] = self.entrypoint
        options["batchsize"] = 1
        importer = OParlImport(options)
        importer.run_singlethread()

        self.assertEqual(18, 18)
