from django.test import TestCase

from mainapp.functions.search_tools import search_string_to_params, params_to_query


class TestSearchtools(TestCase):
    params = {"body": "0", "radius": "50", "searchterm": "word radius anotherword"}

    def test_search_string_to_params(self):
        instring = search_string_to_params("body:0 word  radius radius:50 anotherword")
        self.assertEqual(instring, self.params)

    def test_params_to_query(self):
        expected = {'query': {'query_string': {'query': 'word radius anotherword'}}}
        options, query = params_to_query(self.params)
        self.assertEqual(query.to_dict(), expected)
