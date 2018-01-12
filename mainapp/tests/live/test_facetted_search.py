import time
from datetime import date
from typing import Any, List
from unittest import mock
from urllib import parse

from django.test import override_settings
from elasticsearch_dsl import Search
from elasticsearch_dsl.response import AggResponse
from selenium.webdriver.common.keys import Keys

from mainapp.models import Person
from mainapp.tests.live.chromedriver_test_case import ChromeDriverTestCase
from meine_stadt_transparent import settings

template = {
    "id": 0,
    "highlight": "Text <mark>Highlight</mark>",
    "name": "SomeName",
    "type": "file",
    "type_translated": "File",
    "name_escaped": "Name <mark>Title</mark>"
}


def get_aggregations():
    # Fakes aggregation results that are sufficient for testing
    aggs = {
        "document_type": [
            {"key": "file", "doc_count": 42},
            {"key": "meeting", "doc_count": 42},
            {"key": "person", "doc_count": 42}
        ],
        "person": [],
        "organization": []
    }

    for i in range(10):
        aggs["person"].append({"key": i, "doc_count": 42})
        aggs["organization"].append({"key": i, "doc_count": 42})

    return AggResponse({}, {}, aggs)


def mock_search_to_results(_) -> (List[Any], int):
    return [template], 1, get_aggregations()


def mock_search_for_endless_scroll(search: Search) -> (List[Any], int):
    out = []
    for position in range(search.to_dict()["from"], search.to_dict()["from"] + search.to_dict()["size"]):
        result = template.copy()
        result["name"] = position
        result["name_escaped"] = position
        result["id"] = position
        out.append(result)
    return out, len(out) * 2, get_aggregations()


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
        self.visit('/')
        self.browser.fill("search-query", "word")
        self.browser.find_by_name("search-query").first._element.send_keys(Keys.ENTER)
        self.assertEqual("word", self.get_search_string_from_url())

    @override_settings(USE_ELASTICSEARCH=True)
    @mock.patch("mainapp.views.search._search_to_results", side_effect=mock_search_to_results)
    def test_word(self, _):
        self.visit('/search/query/word/')
        self.assertTrue(self.browser.is_text_present("Highlight"))
        self.assertTrue(self.browser.is_text_present("Title"))
        self.assertFalse(self.browser.is_text_present("<mark>"))

    @override_settings(USE_ELASTICSEARCH=True)
    @mock.patch("mainapp.views.search._search_to_results", side_effect=mock_search_to_results)
    def test_document_type(self, _):
        self.visit('/search/query/word/')
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
        self.visit('/search/query/word/')
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
        self.visit('/search/query/word/')
        self.click_by_id("personButton")
        self.click_by_text("Frank Underwood")

        self.assertEqual("person:1 word", self.get_search_string_from_url())

        self.click_by_id("personButton")
        self.browser.find_by_css(".show .remove-filter > a").first.click()

        self.assertEqual("word", self.get_search_string_from_url())

    @override_settings(USE_ELASTICSEARCH=True)
    @mock.patch("mainapp.views.search._search_to_results", side_effect=mock_search_to_results)
    def test_sorting(self, _):
        self.visit('/search/query/word/')
        self.click_by_id("btnSortDropdown")
        self.click_by_text("Newest first")

        self.assertEqual("sort:date_newest word", self.get_search_string_from_url())

        self.click_by_id("btnSortDropdown")
        self.click_by_text("Relevance")

        self.assertEqual("word", self.get_search_string_from_url())

    @override_settings(USE_ELASTICSEARCH=True)
    @mock.patch("mainapp.views.search._search_to_results", side_effect=mock_search_to_results)
    def test_dropdown_filter(self, _):
        self.visit('/search/query/word/')
        self.click_by_id("personButton")
        count = len(self.browser.find_by_css("[data-filter-key='person'] .filter-item"))
        org = settings.SITE_DEFAULT_ORGANIZATION
        persons = Person.objects.filter(organizationmembership__organization=org).distinct().count()
        self.assertEqual(count, persons)
        self.browser.fill("filter-person", "Frank")
        count = len(self.browser.find_by_css("[data-filter-key='person'] .filter-item"))
        self.assertEqual(count, 1)

    @override_settings(USE_ELASTICSEARCH=True)
    @mock.patch("mainapp.views.search._search_to_results", side_effect=mock_search_for_endless_scroll)
    def test_endless_scroll(self, _):
        self.visit('/search/query/word/')

        single_length = settings.SEARCH_PAGINATION_LENGTH
        self.assertEqual(single_length, len(self.browser.find_by_css(".results-list > li")))
        numbers = [int(i.text) for i in self.browser.find_by_css(".results-list > li .result-title")]
        numbers.sort()
        self.assertEqual(numbers, list(range(0, single_length)))

        self.click_by_id("start-endless-scroll")

        # semi-busy waiting
        # (it does work without wating on my machine, but I won't risk having any timing based test failures)
        while single_length == len(self.browser.find_by_css(".results-list > li")):
            time.sleep(0.01)

        self.assertEqual(single_length * 2, len(self.browser.find_by_css(".results-list > li")))
        numbers = [int(i.text) for i in self.browser.find_by_css(".results-list > li .result-title")]
        numbers.sort()
        self.assertEqual(numbers, list(range(0, single_length * 2)))
