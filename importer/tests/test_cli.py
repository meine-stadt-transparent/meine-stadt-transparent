import json
import os
import urllib.parse
from typing import Tuple

import responses
from django.test import SimpleTestCase
from django.utils.http import urlencode
from requests import PreparedRequest

from importer.cli import Cli
from importer.utils import Utils
from mainapp.models import Body


class TestCli(SimpleTestCase):
    def test_warning_body_url_mismatch(self):
        body = {
            "id": "http://ratsinfo-online.net/landkreis-mol-bi/oparl/1.0/bodies.asp?id=1",
            "type": "https://schema.oparl.org/1.0/Body",
            "system": "http://ratsinfo-online.net/landkreis-mol-bi/oparl/1.0/system.asp",
            "name": "Landkreis Märkisch-Oderland",
            "shortName": "KT",
            "organization": "http://ratsinfo-online.net/landkreis-mol-bi/oparl/1.0/organizations.asp?body=1",
            "person": "http://ratsinfo-online.net/landkreis-mol-bi/oparl/1.0/persons.asp?body=1",
            "meeting": "http://ratsinfo-online.net/landkreis-mol-bi/oparl/1.0/meetings.asp?body=1",
            "paper": "http://ratsinfo-online.net/landkreis-mol-bi/oparl/1.0/papers.asp?body=1",
            "legislativeTerm": [],
            "created": "2008-01-01T12:00:00+01:00",
            "modified": "2019-02-12T15:04:33+01:00",
        }

        with responses.RequestsMock() as requests_mock:
            body_url = (
                "https://ratsinfo-online.net/landkreis-mol-bi/oparl/1.0/bodies.asp?id=1"
            )
            requests_mock.add(requests_mock.GET, body_url, json=body)

            cli = Cli()
            # Typeshed is wrong for assertLogs
            # noinspection PyTypeChecker
            with self.assertLogs(cli.__module__, level="WARNING") as cm:
                endpoint_system, endpoint_id = cli.get_endpoint_from_body_url(body_url)
                self.assertEqual(endpoint_system, body["system"])
                self.assertEqual(endpoint_id, body["id"])
                self.assertEqual(
                    cm.output,
                    [
                        "WARNING:{}:The body's url '{}' doesn't match the body's id '{}'".format(
                            cli.__module__, body_url, body["id"]
                        )
                    ],
                )

    def request_callback(self, request: PreparedRequest) -> Tuple[int, dict, str]:
        bedburg = {
            "head": {"vars": ["city", "cityLabel", "ags"]},
            "results": {
                "bindings": [
                    {
                        "city": {
                            "type": "uri",
                            "value": "http://www.wikidata.org/entity/Q245292",
                        },
                        "ags": {"type": "literal", "value": "05362004"},
                        "cityLabel": {
                            "xml:lang": "de",
                            "type": "literal",
                            "value": "Bedburg",
                        },
                    }
                ]
            },
        }

        empty = {
            "head": {"vars": ["city", "cityLabel", "ags"]},
            "results": {"bindings": []},
        }

        payload = urllib.parse.parse_qs(urllib.parse.urlparse(request.url).query)
        if '"Bedburg"' in payload["query"][0]:
            return 200, {}, json.dumps(bedburg)

        return 200, {}, json.dumps(empty)

    def test_city_to_ags(self):
        with responses.RequestsMock() as requests_mock:
            requests_mock.add_callback(
                requests_mock.GET,
                "https://query.wikidata.org/sparql",
                callback=self.request_callback,
                content_type="application/json",
            )

            expected = ("05362004", "Bedburg")

            body = Body()
            # Example: https://www.lwl-pch.sitzung-online.de/oi/oparl/1.0/bodies.asp?id=2
            body.short_name = "KT"
            body.name = "Unknown"

            cli = Cli()
            with self.assertRaisesMessage(
                RuntimeError, "Could not determine the Amtliche Gemeindeschlüssel"
            ):
                cli.get_ags(body, {}, "Unknown")

            # System name
            ags = cli.get_ags(body, {"name": "Stadt Bedburg"}, "Unknown")
            self.assertEqual(ags, expected)

            # Userinput
            ags = cli.get_ags(body, {}, "Bedburg")
            self.assertEqual(ags, expected)

            # Body name
            body.name = "Bedburg"
            ags = cli.get_ags(body, {}, "Unknown")
            self.assertEqual(ags, expected)

    def test_ags_and_short_name(self):
        with open("testdata/body_to_ags.json") as fp:
            expected = json.load(fp)

        actual = {}

        with responses.RequestsMock() as requests_mock:
            # Prerecorded responses from wikidata
            with open("testdata/wikidata_sparql_responses.json") as fp:
                saved_responses = json.load(fp)
            for saved_response in saved_responses:
                requests_mock.add(
                    requests_mock.GET,
                    "https://query.wikidata.org/sparql?"
                    + urlencode(saved_response["params"]),
                    json=saved_response["response"],
                )

            cli = Cli()
            for file in sorted(os.listdir("testdata/bodies")):
                with open(os.path.join("testdata/bodies", file)) as fp:
                    data = json.load(fp)
                with open(os.path.join("testdata/systems", file)) as fp:
                    system = json.load(fp)
                body = Body()
                body.ags = data.get("ags")
                body.name = data["name"]
                body.short_name = data.get("shortName") or data["name"]
                body.short_name = Utils().normalize_body_name(body.short_name)

                if body.ags:
                    if len(body.ags) == 7:
                        body.ags = "0" + body.ags
                else:
                    ags, match_name = cli.get_ags(body, system, data["id"])
                    body.ags = ags
                    # Sometimes there's a bad short name (e.g. "Rat" for Erkelenz),
                    # so we use the name that's in wikidata instead
                    body.short_name = match_name

                actual[file] = {"ags": body.ags, "short_name": body.short_name}
            self.assertEqual(expected, actual)
