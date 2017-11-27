from django.test import TestCase

from mainapp.functions.search_tools import search_string_to_params, params_to_query, params_to_search_string

expected_params = {
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
                    'query_string': {
                        'query': 'word radius anotherword'
                    }
                }
            ]
        }
    }
}


class TestSearchtools(TestCase):
    params = {"document-type": "file,committee", "radius": "50", "searchterm": "word radius anotherword"}

    def test_search_string_to_params(self):
        instring = search_string_to_params("document-type:file,committee word  radius radius:50 anotherword")
        self.assertEqual(instring, self.params)

    def test_params_to_query(self):
        options, query, errors = params_to_query(self.params)
        self.assertEqual(errors, [])
        self.assertEqual(query.to_dict(), expected_params)

    def test_params_to_search_string(self):
        expected = "document-type:file,committee radius:50 word radius anotherword"
        search_string = params_to_search_string(self.params)
        self.assertEqual(search_string, expected)
