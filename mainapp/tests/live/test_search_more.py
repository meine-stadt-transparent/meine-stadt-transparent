from unittest import mock

from django.test import override_settings, TestCase

from mainapp.tests.utils import ElasticsearchMock


class FacettedSearchTest(TestCase):
    fixtures = ["initdata"]
    elasticsearch_mock = ElasticsearchMock(
        {
            "testdata/elasticsearch/empty_word_query.json": "testdata/elasticsearch/more_than_10000_hits.json"
        }
    )

    @override_settings(ELASTICSEARCH_ENABLED=True)
    @mock.patch(
        "elasticsearch_dsl.search.get_connection",
        new=lambda _alias: FacettedSearchTest.elasticsearch_mock,
    )
    def test_over_10000_results(self):
        """When there >10000 results, elasticsearch 7+ only tells us that there are 10000+ results,
        which we need to handle in the UI"""
        response = self.client.get("/search/query//").content.decode()

        assert "Over 10000" in response
