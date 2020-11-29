from typing import Optional, Dict, Any, Tuple, List

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
    """ Loads responses from a predefined dict """

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
        """ Ignores the query fragment to make mocking easy when filters are used """
        return self.api_data[url]

    def load_file(self, url: str) -> Tuple[bytes, str]:
        return self.files[url]


def geocode(search_str: str) -> Optional[Dict[str, Any]]:
    """ Makes sure we don't accidentally call the geocoder in the tests """
    raise AssertionError(search_str)


def make_list(data: List[JSON]) -> JSON:
    return {"data": data, "pagination": {}, "links": {}}


def make_file(file_id: int) -> JSON:
    return {
        "id": "https://oparl.example.org/files/{}".format(file_id),
        "type": "https://schema.oparl.org/1.1/File",
        "accessUrl": "https://oparl.example.org/files/{}.pdf".format(file_id),
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
