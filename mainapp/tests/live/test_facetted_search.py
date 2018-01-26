import time
from datetime import date
from unittest import mock
from urllib import parse

from django.test import override_settings
from elasticsearch_dsl import AttrDict, AttrList
from elasticsearch_dsl.response import AggResponse, Hit
from selenium.webdriver.common.keys import Keys

from mainapp.functions.search_tools import MainappSearch
from mainapp.models import Person
from mainapp.tests.live.chromedriver_test_case import ChromeDriverTestCase
from meine_stadt_transparent import settings

template = {
    "id": 0,
    "highlight": "Text <mark>Highlight</mark>",
    "name": "SomeName",
    "type": "file",
    "type_translated": "File",
    "name_escaped": "Name <mark>Title</mark>",
    "meta": {"doc_type": "file_document"}
}


def get_aggregations():
    # Fakes aggregation results that are sufficient for testing
    aggs = {
        "document_type": [
            ("file", 42, False),
            ("meeting", 42, False),
            ("person", 42, False)
        ],
        "person": [],
        "organization": []
    }

    for i in range(10):
        aggs["person"].append((str(i), 42, False))
        aggs["organization"].append((str(i), 42, False))

    return AggResponse({}, {}, aggs)


class MockMainappSearch(MainappSearch):
    """ The execute method is injected in the test methods """
    def execute(self):
        hits = AttrList(Hit(template))
        hits.__setattr__("total", 1)
        return AttrDict({"hits": hits, "facets": get_aggregations()})


class MockMainappSearchEndlessScroll(MainappSearch):
    """ The execute method is injected in the test for the endless scroll"""
    def execute(self):
        out = []
        for position in range(self._s.to_dict()["from"], self._s.to_dict()["from"] + self._s.to_dict()["size"]):
            result = template.copy()
            result["name"] = position
            result["name_escaped"] = position
            result["id"] = position
            out.append(result)
        hits = AttrList(Hit(out))
        hits.__setattr__("total", len(out) * 2)
        return AttrDict({"hits": hits, "facets": get_aggregations()})


class FacettedSearchTest(ChromeDriverTestCase):
    fixtures = ['initdata.json']

    def get_search_string_from_url(self):
        return parse.unquote(self.browser.url.split("/")[-2])

    def assert_query_equals(self):
        return parse.unquote(self.browser.url.split("/")[-2])

    @override_settings(USE_ELASTICSEARCH=True)
    @mock.patch("mainapp.functions.search_tools.MainappSearch.execute", new=MockMainappSearch.execute)
    def test_landing_page_redirect(self):
        """ There was a case where the redirect would lead to the wrong page """
        self.visit('/')
        self.browser.fill("search-query", "word")
        self.browser.find_by_name("search-query").first._element.send_keys(Keys.ENTER)
        self.assertEqual("word", self.get_search_string_from_url())

    @override_settings(USE_ELASTICSEARCH=True)
    @mock.patch("mainapp.functions.search_tools.MainappSearch.execute", new=MockMainappSearch.execute)
    def test_word(self):
        self.visit('/search/query/word/')
        self.assertTrue(self.browser.is_text_present("Highlight"))
        self.assertTrue(self.browser.is_text_present("Title"))
        self.assertFalse(self.browser.is_text_present("<mark>"))

    @override_settings(USE_ELASTICSEARCH=True)
    @mock.patch("mainapp.functions.search_tools.MainappSearch.execute", new=MockMainappSearch.execute)
    def test_document_type(self):
        self.visit('/search/query/word/')
        print(self.live_server_url)
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
    @mock.patch("mainapp.functions.search_tools.MainappSearch.execute", new=MockMainappSearch.execute)
    def test_time_range(self):
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
    @mock.patch("mainapp.functions.search_tools.MainappSearch.execute", new=MockMainappSearch.execute)
    def test_person_filter(self):
        self.visit('/search/query/word/')
        self.click_by_id("personButton")
        self.click_by_text("Frank Underwood")

        self.assertEqual("person:1 word", self.get_search_string_from_url())

        self.click_by_id("personButton")
        self.browser.find_by_css(".show .remove-filter > a").first.click()

        self.assertEqual("word", self.get_search_string_from_url())

    @override_settings(USE_ELASTICSEARCH=True)
    @mock.patch("mainapp.functions.search_tools.MainappSearch.execute", new=MockMainappSearch.execute)
    def test_sorting(self):
        self.visit('/search/query/word/')
        self.click_by_id("btnSortDropdown")
        self.click_by_text("Newest first")

        self.assertEqual("sort:date_newest word", self.get_search_string_from_url())

        self.click_by_id("btnSortDropdown")
        self.click_by_text("Relevance")

        self.assertEqual("word", self.get_search_string_from_url())

    @override_settings(USE_ELASTICSEARCH=True)
    @mock.patch("mainapp.functions.search_tools.MainappSearch.execute", new=MockMainappSearch.execute)
    def test_dropdown_filter(self):
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
    @mock.patch("mainapp.functions.search_tools.MainappSearch.execute", new=MockMainappSearchEndlessScroll.execute)
    def test_endless_scroll(self):
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
