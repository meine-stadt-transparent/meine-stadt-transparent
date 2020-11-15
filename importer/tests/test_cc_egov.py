import logging

import responses

from importer.loader import CCEgovLoader

logger = logging.getLogger(__name__)


def test_spurious_500(caplog):
    with responses.RequestsMock() as requests_mock:
        requests_mock.add(
            responses.GET,
            "https://ratsinfo.leipzig.de/bi/oparl/1.0/papers.asp?body=2387&p=2",
            json={"error": "spurious error"},
            status=500,
        )

        requests_mock.add(
            requests_mock.GET,
            "https://ratsinfo.leipzig.de/bi/oparl/1.0/papers.asp?body=2387&p=2",
            json={
                "data": [
                    {
                        "id": "https://ratsinfo.leipzig.de/bi/oparl/1.0/papers.asp?id=1000030",
                        "type": "https://schema.oparl.org/1.0/Paper",
                        "body": "https://ratsinfo.leipzig.de/bi/oparl/1.0/bodies.asp?id=2387",
                        "name": "Konzept der Stadt Leipzig zur fairen und nachhaltigen Beschaffung\r\n(eRis: DS V/3966)",
                        "reference": "DS-00029/14",
                        "paperType": "Informationsvorlage",
                        "date": "2014-09-09",
                        "mainFile": {
                            "id": "https://ratsinfo.leipzig.de/bi/oparl/1.0/files.asp?dtyp=130&id=1000487",
                            "type": "https://schema.oparl.org/1.0/File",
                            "name": "Vorlage-Sammeldokument",
                            "fileName": "1000487.pdf",
                            "mimeType": "application/pdf",
                            "modified": "2018-12-05T19:23:53+01:00",
                            "size": 211644,
                            "accessUrl": "https://ratsinfo.leipzig.de/bi/oparl/1.0/download.asp?dtyp=130&id=1000487",
                        },
                        "web": "N/Avo020.asp?VOLFDNR=1000030",
                        "created": "2014-07-23T12:00:00+02:00",
                        "modified": "2014-09-09T10:03:49+02:00",
                    },
                ],
                "pagination": {"elementsPerPage": 20},
                "links": {
                    "first": "https://ratsinfo.leipzig.de/bi/oparl/1.0/papers.asp?body=2387",
                    "prev": "https://ratsinfo.leipzig.de/bi/oparl/1.0/papers.asp?body=2387&p=1",
                    "next": "https://ratsinfo.leipzig.de/bi/oparl/1.0/papers.asp?body=2387&p=3",
                },
            },
        )

        loader = CCEgovLoader({})
        data = loader.load(
            "https://ratsinfo.leipzig.de/bi/oparl/1.0/papers.asp?body=2387&p=2",
        )

        assert len(data["data"]) == 1
        assert caplog.messages == [
            "Got an 500 for a CC e-gov request, retrying: 500 Server Error: "
            "Internal Server Error for url: https://ratsinfo.leipzig.de/bi/oparl/1.0/papers.asp?body=2387&p=2"
        ]
