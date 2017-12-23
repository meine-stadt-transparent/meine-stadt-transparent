from datetime import date
from typing import Any, List
from unittest import mock
from urllib import parse

from django.test import override_settings
from elasticsearch_dsl import Search
from selenium.webdriver.common.keys import Keys

from mainapp.tests.live.chromedriver_test_case import ChromeDriverTestCase

template = {
    "id": 0,
    "highlight": "Text <mark>Highlight</mark>",
    "name": "SomeName",
    "type": "file",
    "type_translated": "File",
    "name_escaped": "Name <mark>Title</mark>"
}


def mock_search_to_results(search: Search) -> (List[Any], int):
    return [template], 1


def mock_search_for_endless_scroll(search: Search) -> (List[Any], int):
    out = []
    for position in range(0, 30):
        result = template.copy()
        result["name"] = position
        out.append(result)


class FacettedSearchTest(ChromeDriverTestCase):
    fixtures = ['initdata.json']

    def get_search_string_from_url(self):
        return parse.unquote(self.browser.url.split("/")[-2])

    def assert_query_equals(self):
        return parse.unquote(self.browser.url.split("/")[-2])

    @override_settings(USE_ELASTICSEARCH=True)
    @mock.patch("mainapp.views.search._search_to_results", side_effect=mock_search_to_results)
    def test_landing_page_redirect(self, _):
        """ There was a case where the redirect would lead to the wrong page """
        self.browser.visit('%s%s' % (self.live_server_url, '/'))
        self.browser.fill("search-query", "word")
        self.browser.find_by_name("search-query").first._element.send_keys(Keys.ENTER)
        self.assertEqual("word", self.get_search_string_from_url())

    @override_settings(USE_ELASTICSEARCH=True)
    @mock.patch("mainapp.views.search._search_to_results", side_effect=mock_search_to_results)
    def test_word(self, _):
        self.browser.visit('%s%s' % (self.live_server_url, '/search/query/word/'))
        self.assertTrue(self.browser.is_text_present("Highlight"))
        self.assertTrue(self.browser.is_text_present("Title"))
        self.assertFalse(self.browser.is_text_present("<mark>"))

    @override_settings(USE_ELASTICSEARCH=True)
    @mock.patch("mainapp.views.search._search_to_results", side_effect=mock_search_to_results)
    def test_document_type(self, _):
        self.browser.visit('%s%s' % (self.live_server_url, '/search/query/word/'))
        self.assertTextIsPresent("Document Type")
        self.assertTextIsNotPresent("Meeting")
        self.browser.click_link_by_id("documentTypeButton")
        self.assertTextIsPresent("Meeting")
        self.browser.check("document-type[person]")
        self.browser.check("document-type[file]")
        self.browser.check("document-type[meeting]")
        self.assertEqual("document-type:file,meeting,person word", self.get_search_string_from_url())
        self.browser.uncheck("document-type[meeting]")
        self.assertEqual("document-type:file,person word", self.get_search_string_from_url())
        self.browser.click_link_by_partial_text("Cancel Selection")
        self.assertEqual("word", self.get_search_string_from_url())

    @override_settings(USE_ELASTICSEARCH=True)
    @mock.patch("mainapp.views.search._search_to_results", side_effect=mock_search_to_results)
    def test_time_range(self, _):
        self.browser.visit('%s%s' % (self.live_server_url, '/search/query/word/'))
        self.click_by_id("timeRangeButton")
        self.click_by_text("This year")

        first_day = date(date.today().year, 1, 1)
        last_day = date(date.today().year, 12, 31)
        self.assertEqual("after:{} before:{} word".format(first_day, last_day), self.get_search_string_from_url())

        self.click_by_id("timeRangeButton")
        self.click_by_text("Cancel Selection")
        self.assertEqual("word", self.get_search_string_from_url())

    @override_settings(USE_ELASTICSEARCH=True)
    @mock.patch("mainapp.views.search._search_to_results", side_effect=mock_search_to_results)
    def test_person_filter(self, _):
        self.browser.visit('%s%s' % (self.live_server_url, '/search/query/word/'))
        self.click_by_id("personButton")
        self.click_by_text("Frank Underwood")

        self.assertEqual("person:1 word", self.get_search_string_from_url())

        self.click_by_id("personButton")
        self.click_by_text("Cancel Selection")

        self.assertEqual("word", self.get_search_string_from_url())

    @override_settings(USE_ELASTICSEARCH=True)
    @mock.patch("mainapp.views.search._search_to_results", side_effect=mock_search_to_results)
    def test_sorting(self, _):
        self.browser.visit('%s%s' % (self.live_server_url, '/search/query/word/'))
        self.click_by_id("btnSortDropdown")
        self.click_by_text("Newest first")

        self.assertEqual("sort:date_newest word", self.get_search_string_from_url())

        self.click_by_id("btnSortDropdown")
        self.click_by_text("Relevance")

        self.assertEqual("word", self.get_search_string_from_url())

    @override_settings(USE_ELASTICSEARCH=True)
    @mock.patch("mainapp.views.search._search_to_results", side_effect=mock_search_for_endless_scroll)
    def test_endless_scroll(self, _):
        self.browser.visit('%s%s' % (self.live_server_url, '/search/query/word/'))
        pass
