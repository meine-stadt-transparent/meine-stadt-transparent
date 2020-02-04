import json
from pathlib import Path
from unittest import mock

from django.test import override_settings, TestCase


class MockedElasticsearch:
    def __init__(self, _alias: str = "_default"):
        self.empty_word_query = json.loads(
            Path("testdata/elasticsearch/empty_word_query.json").read_text()
        )
        self.response = json.loads(
            Path("testdata/elasticsearch/more_than_10000_hits.json").read_text()
        )

    def search(self, *_args, **query):
        assert query == self.empty_word_query
        return self.response


class FacettedSearchTest(TestCase):
    fixtures = ["initdata"]

    @override_settings(ELASTICSEARCH_ENABLED=True)
    @mock.patch("elasticsearch_dsl.search.get_connection", new=MockedElasticsearch)
    def test_over_10000_results(self):
        """ When there >10000 results, elasticsearch 7+ only tells us that there are 10000+ results,
        which we need to handle in the UI
        """
        response = self.client.get("/search/query//").content.decode()

        assert "Over 10000" in response
