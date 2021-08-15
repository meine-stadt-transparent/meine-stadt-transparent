from typing import Optional, Dict, Any, Tuple, List

import responses

from importer import JSON
from importer.loader import BaseLoader

old_date = "1997-07-31T18:00:00+01:00"


def make_system() -> JSON:
    return {
        "id": "https://oparl.example.org/",
        "type": "https://schema.oparl.org/1.0/System",
        "oparlVersion": "https://schema.oparl.org/1.0/",
        "body": "https://oparl.example.org/bodies",
        "name": "Beispiel-System",
        "created": old_date,
        "modified": old_date,
    }


def make_body() -> JSON:
    return {
        "id": "https://oparl.example.org/body/1",
        "type": "https://schema.oparl.org/1.0/Body",
        "oparlVersion": "https://schema.oparl.org/1.0/",
        "paper": "https://oparl.example.org/paper",
        "person": "https://oparl.example.org/person",
        "organization": "https://oparl.example.org/organization",
        "meeting": "https://oparl.example.org/meeting",
        "name": "Beispiel-Body",
        "created": old_date,
        "modified": old_date,
    }


class MockLoader(BaseLoader):
    """Loads responses from a predefined dict"""

    api_data: Dict[str, JSON]
    files: Dict[str, Tuple[bytes, str]]

    def __init__(
        self, system: Optional[JSON] = None, api_data: Optional[Dict[str, JSON]] = None
    ):
        super().__init__(system)
        if api_data is None:
            self.api_data = {}
        else:
            self.api_data = api_data
        self.files = {}
        self.system = system

    def load(self, url: str, query: Optional[dict] = None) -> JSON:
        """Ignores the query fragment to make mocking easy when filters are used"""
        return self.api_data[url]

    def load_file(self, url: str) -> Tuple[bytes, str]:
        return self.files[url]


def geocode(search_str: str) -> Optional[Dict[str, Any]]:
    """Makes sure we don't accidentally call the geocoder in the tests"""
    raise AssertionError(search_str)


def make_list(data: List[JSON]) -> JSON:
    return {"data": data, "pagination": {}, "links": {}}


def make_file(file_id: int) -> JSON:
    return {
        "id": f"https://oparl.example.org/files/{file_id}",
        "type": "https://schema.oparl.org/1.1/File",
        "accessUrl": f"https://oparl.example.org/files/{file_id}.pdf",
        "name": "default",
        "created": old_date,
        "modified": old_date,
    }


def make_paper(files: List[JSON], paper_id: int = 0) -> JSON:
    return {
        "id": "https://oparl.example.org/paper/" + str(paper_id),
        "type": "https://schema.oparl.org/1.1/Paper",
        "name": "Antwort auf Anfrage 1234/2001",
        "reference": "12/34",
        "auxiliaryFile": files,
        "created": old_date,
        "modified": old_date,
    }


def spurious_500(loader: BaseLoader):
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
                    }
                ],
                "pagination": {"elementsPerPage": 20},
                "links": {
                    "first": "https://ratsinfo.leipzig.de/bi/oparl/1.0/papers.asp?body=2387",
                    "prev": "https://ratsinfo.leipzig.de/bi/oparl/1.0/papers.asp?body=2387&p=1",
                    "next": "https://ratsinfo.leipzig.de/bi/oparl/1.0/papers.asp?body=2387&p=3",
                },
            },
        )

        data = loader.load(
            "https://ratsinfo.leipzig.de/bi/oparl/1.0/papers.asp?body=2387&p=2"
        )

        assert len(data["data"]) == 1
