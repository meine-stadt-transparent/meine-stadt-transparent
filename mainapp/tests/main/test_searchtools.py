from django.test import TestCase

from mainapp.functions.search import (
    search_string_to_params,
    params_to_search_string,
    MainappSearch,
    MULTI_MATCH_FIELDS,
)

expected_params = {
    "query": {
        "bool": {
            "should": [
                {
                    "multi_match": {
                        "query": "word radius anotherword",
                        "operator": "and",
                        "fields": MULTI_MATCH_FIELDS,
                    }
                },
                {
                    "multi_match": {
                        "query": "word radius anotherword",
                        "operator": "and",
                        "fields": MULTI_MATCH_FIELDS,
                        "fuzziness": "1",
                        "prefix_length": 1,
                    }
                },
            ]
        }
    },
    "post_filter": {"terms": {"_index": ["mst-test-file", "mst-test-committee"]}},
    "indices_boost": [
        {"mst-test-person": 4},
        {"mst-test-organization": 4},
        {"mst-test-paper": 2},
    ],
    "_source": ["id", "name", "legal_date", "reference_number", "display_date"],
    "aggs": {
        "_filter_document_type": {
            "filter": {"match_all": {}},
            "aggs": {"document_type": {"terms": {"field": "_index"}}},
        },
        "_filter_person": {
            "filter": {"terms": {"_index": ["mst-test-file", "mst-test-committee"]}},
            "aggs": {"person": {"terms": {"field": "person_ids"}}},
        },
        "_filter_organization": {
            "filter": {"terms": {"_index": ["mst-test-file", "mst-test-committee"]}},
            "aggs": {"organization": {"terms": {"field": "organization_ids"}}},
        },
    },
    "sort": [{"sort_date": {"order": "desc"}}],
    "highlight": {
        "fields": {
            "*": {"fragment_size": 150, "pre_tags": "<mark>", "post_tags": "</mark>"}
        }
    },
}


class TestSearchtools(TestCase):
    maxDiff = None
    params = {
        "document-type": "file,committee",
        "radius": "50",
        "searchterm": "word radius anotherword",
        "sort": "date_newest",
    }

    def test_search_string_to_params(self):
        instring = search_string_to_params(
            "document-type:file,committee word  radius radius:50 sort:date_newest anotherword"
        )
        self.assertEqual(instring, self.params)

    def test_params_to_query(self):
        main_search = MainappSearch(self.params)
        self.assertEqual(main_search.errors, [])
        self.assertEqual(main_search.build_search().to_dict(), expected_params)

    def test_params_to_search_string(self):
        expected = "document-type:file,committee radius:50 sort:date_newest word radius anotherword"
        search_string = params_to_search_string(self.params)
        self.assertEqual(search_string, expected)
