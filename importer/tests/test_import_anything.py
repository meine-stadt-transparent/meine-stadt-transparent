import json

import responses
from django.core.management import call_command
from django.test import TestCase

from importer.loader import BaseLoader
from importer.management.commands import import_anything
from mainapp.models import File


class TestImportAnything(TestCase):
    fixtures = ["import-anything"]

    def test_import_anything(self):
        with open("testdata/oparl/File.json") as fp:
            file = json.load(fp)

        with open("testdata/oparl/System.json") as fp:
            system = json.load(fp)

        # Import a previously not existing object
        file["name"] = "Old"
        with responses.RequestsMock() as requests_mock:
            requests_mock.add(requests_mock.GET, system["id"], json=system)
            requests_mock.add(requests_mock.GET, file["id"], json=file)
            call_command(import_anything.Command(), file["id"])

        self.assertEqual(File.objects.get(oparl_id=file["id"]).name, "Old")

        # Update an existing object
        file["name"] = "New"
        with responses.RequestsMock() as requests_mock:
            requests_mock.add(requests_mock.GET, system["id"], json=system)
            requests_mock.add(requests_mock.GET, file["id"], json=file)
            call_command(import_anything.Command(), file["id"])

        self.assertEqual(File.objects.get(oparl_id=file["id"]).name, "New")

    def test_warn_import_mismatch_url_id(self):
        with open("testdata/oparl/File.json") as fp:
            file = json.load(fp)

        with open("testdata/oparl/System.json") as fp:
            system = json.load(fp)

        alias_url = "https://ris.krefeld.de/webservice/oparl/v1/body/1/file/2-6766"

        # Typeshed is wrong for assertLogs
        # noinspection PyTypeChecker
        with self.assertLogs(BaseLoader.__module__, level="WARNING") as cm:
            with responses.RequestsMock() as requests_mock:
                requests_mock.add(requests_mock.GET, system["id"], json=system)
                requests_mock.add(requests_mock.GET, alias_url, json=file)
                call_command(import_anything.Command(), alias_url)

            self.assertEqual(
                cm.output,
                [
                    "WARNING:{}:Mismatch between url and id. url: {} id: {}".format(
                        BaseLoader.__module__, alias_url, file["id"]
                    )
                ],
            )
