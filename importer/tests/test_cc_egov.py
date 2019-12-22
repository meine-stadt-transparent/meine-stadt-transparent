import json
from pathlib import Path

import responses
from django.test import TestCase

from importer.loader import CCEgovLoader


class TestCCEGov(TestCase):
    """ Tests for the workaround for the bugs in CC e-gov's OParl implementation """

    def test_empty_list_returns_error_test(self):
        with responses.RequestsMock() as requests_mock:
            requests_mock.add(
                requests_mock.GET,
                "https://www.bonn.sitzung-online.de/public/oparl/bodies?id=1",
                content_type="application/json;charset=utf-8",
                json=json.loads(
                    Path("importer/testdata/cc-egov-colon-before.json").read_text()
                ),
            )

            loader = CCEgovLoader({})
            data = loader.load(
                "https://www.bonn.sitzung-online.de/public/oparl/bodies?id=1"
            )

            fixed = json.loads(
                Path("importer/testdata/cc-egov-colon-after.json").read_text()
            )

            assert data == fixed
