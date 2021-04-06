import pytest
import responses
from requests import HTTPError

from importer.loader import SomacosLoader, BaseLoader
from importer.tests.utils import spurious_500


def test_somacos_encoded_urls():
    with responses.RequestsMock() as requests_mock:
        requests_mock.add(
            requests_mock.GET,
            "https://oparl.wuppertal.de/oparl/bodies/0001/papers?page=2&modified_since=2020-11-26T19:26:34+00:00",
            content_type="text/json; charset=utf-8",
            json={},
        )

        requests_mock.add(
            requests_mock.GET,
            "https://oparl.wuppertal.de/oparl/bodies/0001/papers?page=2&modified_since=2020-11-26T19%3A26%3A34%2B00%3A00",
            content_type="text/html",
            status=404,
        )

        with pytest.raises(HTTPError):
            BaseLoader({}).load(
                "https://oparl.wuppertal.de/oparl/bodies/0001/papers",
                query={"page": "2", "modified_since": "2020-11-26T19:26:34+00:00"},
            )

        loader = SomacosLoader({})
        loader.load(
            "https://oparl.wuppertal.de/oparl/bodies/0001/papers",
            query={"page": "2", "modified_since": "2020-11-26T19:26:34+00:00"},
        )


def test_spurious_500(caplog):
    loader = SomacosLoader({})
    loader.error_sleep_seconds = 0
    spurious_500(loader)
    assert caplog.messages == [
        "Got an 500 for a Somacos request, retrying after sleeping 0s: 500 Server "
        "Error: Internal Server Error for url: "
        "https://ratsinfo.leipzig.de/bi/oparl/1.0/papers.asp?body=2387&p=2"
    ]
