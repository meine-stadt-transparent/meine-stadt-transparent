"""Tests for the workaround for the bugs in Sterberg's OParl implementation

The exact urls might not return an error anymore, but any timestamp in the future will work
"""

import pytest
import responses
from requests.exceptions import ConnectionError

from importer.loader import SternbergLoader


def test_empty_list_returns_error():
    with responses.RequestsMock() as requests_mock:
        requests_mock.add(
            requests_mock.GET,
            "https://ris.krefeld.de/webservice/oparl/v1.0/body/1/paper?modified_since=2019-05-30T22%3A00%3A08%2B00%3A00",
            content_type="text/html",
            status=404,
            body='{"error":"Die angeforderte Ressource wurde nicht gefunden.","code":802,"type":"SD.NET RIM Webservice"}',
        )

        loader = SternbergLoader({})
        data = loader.load(
            "https://ris.krefeld.de/webservice/oparl/v1.0/body/1/paper",
            query={"modified_since": "2019-05-30T22:00:08+00:00"},
        )

        assert data["data"] == []

        with pytest.raises(ConnectionError):
            loader.load("https://ris.krefeld.de/webservice/oparl/v1.0/body/1/paper")


def test_empty_list_should_have_been_object():
    with responses.RequestsMock() as requests_mock:
        requests_mock.add(
            requests_mock.GET,
            "https://ris.krefeld.de/webservice/oparl/v1.0/body/1/meeting?modified_since=2019-05-09T20%3A51%3A54%2B00%3A00",
            json=[],
        )

        loader = SternbergLoader({})
        data = loader.load(
            "https://ris.krefeld.de/webservice/oparl/v1.0/body/1/meeting",
            query={"modified_since": "2019-05-09T20:51:54+00:00"},
        )

        assert "data" in data
        assert data["data"] == []

        with pytest.raises(ConnectionError):
            loader.load("https://ris.krefeld.de/webservice/oparl/v1.0/body/1/meeting")


def test_deleted_missing_type():
    data = {
        "id": "https://ris.krefeld.de/webservice/oparl/v1.0/body/1/file/2-19309",
        "created": "2019-03-19T09:59:05+01:00",
        "modified": "2019-04-16T09:02:31+02:00",
        "deleted": True,
    }

    with responses.RequestsMock() as requests_mock:
        requests_mock.add(requests_mock.GET, data["id"], json=data)

        loader = SternbergLoader({})
        data = loader.load(data["id"])

        assert data["type"] == "https://schema.oparl.org/1.0/File"


def test_mixed_up_extensions():
    url_wrong = "https://oparl.example.org/download/file.eml.eml"
    url_correct = "https://oparl.example.org/download/file.eml.pdf"

    with responses.RequestsMock() as requests_mock:
        requests_mock.add(requests_mock.GET, url_wrong, status=404)
        requests_mock.add(requests_mock.GET, url_correct, body=b"OK")

        loader = SternbergLoader({})
        content, content_type = loader.load_file(url_wrong)
        assert content == b"OK"


def test_object_instead_of_list():
    body = {
        "id": "https://ris.krefeld.de/webservice/oparl/v1.0/body/1",
        "type": "https://schema.oparl.org/1.0/Body",
        "system": "https://ris.krefeld.de/webservice/oparl/v1.0/system",
        "name": "Stadt Krefeld",
        "website": "https://www.krefeld.de",
        "ags": "051140000",
        "rgs": "051140000000",
        "contactEmail": "ratundehrenamt@krefeld.de",
        "contactName": "Karsten Sch\u00fcller",
        "organization": "https://ris.krefeld.de/webservice/oparl/v1.0/body/1/organization",
        "person": "https://ris.krefeld.de/webservice/oparl/v1.0/body/1/person",
        "meeting": "https://ris.krefeld.de/webservice/oparl/v1.0/body/1/meeting",
        "paper": "https://ris.krefeld.de/webservice/oparl/v1.0/body/1/paper",
        "location": {
            "id": "https://ris.krefeld.de/webservice/oparl/v1.0/body/1/location/0-1",
            "type": "https://schema.oparl.org/1.0/Location",
        },
    }

    with responses.RequestsMock() as requests_mock:
        requests_mock.add(
            requests_mock.GET,
            "https://ris.krefeld.de/webservice/oparl/v1.0/body",
            json=body,
        )

        loader = SternbergLoader({})
        data = loader.load("https://ris.krefeld.de/webservice/oparl/v1.0/body")

        assert "data" in data
        assert "id" not in data
