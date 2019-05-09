import pytest
import responses
from django.test import TestCase

from requests.exceptions import ConnectionError
from importer.loader import SternbergLoader


class TestSternberg(TestCase):
    def test_empty_list_returns_error(self):
        """
        The exact url might not return an error anymore, but any timestamp in the future will work
        """
        with responses.RequestsMock() as requests_mock:
            requests_mock.add(
                requests_mock.GET,
                "https://ris.krefeld.de/webservice/oparl/v1.0/body/1/paper?modified_since=2019-05-30T22%3A00%3A08.100505%2B00%3A00",
                content_type="text/html",
                status=404,
                body='{"error":"Die angeforderte Ressource wurde nicht gefunden.","code":802,"type":"SD.NET RIM Webservice"}',
            )

            loader = SternbergLoader({})
            data = loader.load(
                "https://ris.krefeld.de/webservice/oparl/v1.0/body/1/paper",
                query={"modified_since": "2019-05-30T22:00:08.100505+00:00"},
            )

            self.assertEqual(data["data"], [])

            with pytest.raises(ConnectionError):
                loader.load("https://ris.krefeld.de/webservice/oparl/v1.0/body/1/paper")
