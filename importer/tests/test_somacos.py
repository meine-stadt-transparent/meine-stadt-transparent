import pytest
import responses
from requests import HTTPError

from importer.loader import SomacosLoader, BaseLoader


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
