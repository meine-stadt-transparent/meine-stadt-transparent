import logging

import responses

from importer.loader import CCEgovLoader
from importer.tests.utils import spurious_500

logger = logging.getLogger(__name__)

meeting_with_auxiliary_file_object = {
    "id": "https://www.bonn.sitzung-online.de/public/oparl/meetings?id=664",
    "type": "https://schema.oparl.org/1.1/Meeting",
    "name": "Sitzung des Projektbeirates Behindertenpolitischer Teilhabeplan",
    "meetingState": "eingeladen",
    "cancelled": False,
    "start": "2021-05-11T17:00:00+02:00",
    "end": "2021-05-12T00:00:00+02:00",
    "organization": [
        "https://www.bonn.sitzung-online.de/public/oparl/organizations?typ=gr&id=334"
    ],
    "invitation": {
        "id": "https://www.bonn.sitzung-online.de/public/oparl/files?id=2026137&dtyp=108",
        "type": "https://schema.oparl.org/1.1/File",
        "name": "Öffentliche Tagesordnung",
        "date": "2021-04-27T21:51:03+02:00",
        "fileName": "37.docx",
        "mimeType": "docx",
        "size": 0,
        "accessUrl": "https://www.bonn.sitzung-online.de/public/doc?DOLFDNR=2026137&DOCTYP=108&OTYP=41",
        "downloadUrl": "",
        "created": "2021-05-01T10:32:32+02:00",
        "modified": "2021-05-01T10:32:32+02:00",
        "deleted": False,
    },
    "auxiliaryFile": {
        "id": "https://www.bonn.sitzung-online.de/public/oparl/files?id=268781&dtyp=134",
        "type": "https://schema.oparl.org/1.1/File",
        "name": "Alle Anlagen öffentlich",
        "date": "2021-04-28T09:02:04+02:00",
        "fileName": "81.pdf",
        "mimeType": "pdf",
        "size": 553767,
        "accessUrl": "https://www.bonn.sitzung-online.de/public/doc?DOLFDNR=268781&DOCTYP=134&OTYP=41",
        "downloadUrl": "",
        "created": "2021-05-01T10:32:32+02:00",
        "modified": "2021-05-01T10:32:32+02:00",
        "deleted": False,
    },
    "agendaItem": [
        {
            "id": "https://www.bonn.sitzung-online.de/public/oparl/agendaItems?id=2002135",
            "type": "https://schema.oparl.org/1.1/AgendaItem",
            "name": "Einführung und Verpflichtung",
            "number": "1",
            "order": 100001,
            "meeting": "https://www.bonn.sitzung-online.de/public/oparl/meetings?id=664",
            "created": "2021-05-01T10:32:33+02:00",
            "modified": "2021-05-01T10:32:33+02:00",
            "deleted": False,
        }
    ],
    "web": "https://www.bonn.sitzung-online.de/public/to010?SILFDNR=664",
    "created": "2021-04-25T22:31:05+02:00",
    "modified": "2021-04-25T22:31:05+02:00",
    "deleted": False,
}


def test_spurious_500(caplog):
    spurious_500(CCEgovLoader({}))
    assert caplog.messages == [
        "Got an 500 for a CC e-gov request, retrying: 500 Server Error: "
        "Internal Server Error for url: https://ratsinfo.leipzig.de/bi/oparl/1.0/papers.asp?body=2387&p=2"
    ]


def test_auxiliary_file_object(caplog):
    loader = CCEgovLoader({})
    with responses.RequestsMock() as requests_mock:
        requests_mock.add(
            requests_mock.GET,
            meeting_with_auxiliary_file_object["id"],
            json=meeting_with_auxiliary_file_object,
        )
        loaded = loader.load(meeting_with_auxiliary_file_object["id"])
        assert isinstance(loaded["auxiliaryFile"], list)
    assert caplog.messages == [
        "auxiliaryFile is supposed to be an array of objects, but is an object (in "
        "https://www.bonn.sitzung-online.de/public/oparl/meetings?id=664)"
    ]


def test_broken_json(pytestconfig, caplog):
    """Broken JSON with control character (U+0000 through U+001F except \n) that is not escaped"""
    loader = CCEgovLoader({})
    with responses.RequestsMock() as requests_mock:
        requests_mock.add(
            requests_mock.GET,
            "https://ratsinfo.braunschweig.de/bi/oparl/1.0/papers.asp?id=1664",
            pytestconfig.rootpath.joinpath(
                "testdata/broken_json.broken_json"
            ).read_text(),
        )
        loaded = loader.load(
            "https://ratsinfo.braunschweig.de/bi/oparl/1.0/papers.asp?id=1664"
        )
        print(loaded["name"])
        assert len(loaded["name"]) == 127
    assert caplog.messages == [
        "The server returned invalid json. "
        "This is a bug in the OParl implementation: "
        "https://ratsinfo.braunschweig.de/bi/oparl/1.0/papers.asp?id=1664"
    ]
