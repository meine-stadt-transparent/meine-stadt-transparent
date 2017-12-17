from unittest import mock

from django.test import override_settings
from elasticsearch_dsl import Search

from mainapp.tests.live.chromedriver_test_case import ChromeDriverTestCase

template = {
    "id": 0,
    "highlight": "Text <mark>Highlight</mark>",
    "name": "SomeName",
    "type": "file",
    "type_translated": "File",
    "name_escaped": "Name <mark>Title</mark>"
}


def mock_search_to_results(search: Search):
    return [template], 1


class FacettedSearchTest(ChromeDriverTestCase):
    fixtures = ['initdata.json']

    @override_settings(DEBUG=True)
    @override_settings(USE_ELASTICSEARCH=True)
    @mock.patch("mainapp.views.search._search_to_results", side_effect=mock_search_to_results)
    def test_list_year(self, _):
        self.browser.visit('%s%s' % (self.live_server_url, '/search/query/word/'))
        self.browser.screenshot(name="Asdfasdf")
        self.assertTrue(self.browser.is_text_present("Highlight"))
        self.assertTrue(self.browser.is_text_present("Title"))
        self.assertFalse(self.browser.is_text_present("<mark>"))
