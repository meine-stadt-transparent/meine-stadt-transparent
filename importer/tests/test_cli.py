import json
import urllib.parse
from typing import Tuple

import responses
from django.test import SimpleTestCase
from requests import PreparedRequest

from importer.cli import Cli
from mainapp.models import Body


class TestCli(SimpleTestCase):
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

    oparl_mirror = {"data": [], "links": {}}

    def request_callback(self, request: PreparedRequest) -> Tuple[int, dict, str]:
        payload = urllib.parse.parse_qs(urllib.parse.urlparse(request.url).query)
        if '"Bedburg"' in payload["query"][0]:
            return 200, {}, json.dumps(self.bedburg)

        return 200, {}, json.dumps(self.empty)

    def test_city_to_ags(self):
        with responses.RequestsMock() as requests_mock:
            requests_mock.add(
                requests_mock.GET,
                "https://mirror.oparl.org/bodies",
                json=self.oparl_mirror,
            )
            requests_mock.add_callback(
                requests_mock.GET,
                "https://query.wikidata.org/sparql",
                callback=self.request_callback,
                content_type="application/json",
            )

            body = Body()
            # Example: https://www.lwl-pch.sitzung-online.de/oi/oparl/1.0/bodies.asp?id=2
            body.short_name = "KT"
            body.name = "Unknown"

            cli = Cli()
            with self.assertRaisesMessage(
                RuntimeError, "Could not determine the Amtliche Gemeindeschlüssel"
            ):
                cli.get_ags(body, "Unknown")
            ags = cli.get_ags(body, "Bedburg")
            self.assertEqual(ags, "05362004")
            body.name = "Bedburg"
            ags = cli.get_ags(body, "Unknown")
            self.assertEqual(ags, "05362004")
