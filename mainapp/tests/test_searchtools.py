from django.test import TestCase

from mainapp.functions.search_tools import search_string_to_params, params_to_query, params_to_search_string

expected_params = {
    'sort': [
        {
            'sort_date': {"order": "desc"}
        }
    ],
    'query': {
        'bool': {
            'filter': [
                {
                    'terms': {
                        '_type': [
                            'file_document',
                            'committee_document'
                        ]
                    }
                }
            ],
            'must': [
                {
                    'match': {
                        '_all': {
                            'query': 'word radius anotherword',
                            'operator': 'and',
                            'fuzziness': 'AUTO',
                            'prefix_length': 1
                        }
                    }
                }
            ]
        }
    },
    'highlight': {
        'fields': {
            '*': {'fragment_size': 150, 'pre_tags': '<mark>', 'post_tags': '</mark>'}
        },
        'require_field_match': False
    }
}


class TestSearchtools(TestCase):
    params = {"document-type": "file,committee", "radius": "50", "searchterm": "word radius anotherword",
              "sort": "date_newest"}

    def test_search_string_to_params(self):
        instring = search_string_to_params(
            "document-type:file,committee word  radius radius:50 sort:date_newest anotherword")
        self.assertEqual(instring, self.params)

    def test_params_to_query(self):
        options, query, errors = params_to_query(self.params)
        self.assertEqual(errors, [])
        self.assertEqual(query.to_dict(), expected_params)

    def test_params_to_search_string(self):
        expected = "document-type:file,committee radius:50 sort:date_newest word radius anotherword"
        search_string = params_to_search_string(self.params)
        self.assertEqual(search_string, expected)
