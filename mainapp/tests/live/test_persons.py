import time

from mainapp.tests.live.chromedriver_test_case import ChromeDriverTestCase


class PersonsTest(ChromeDriverTestCase):
    fixtures = ["initdata"]

    def _get_pos_by_name(self, name: str):
        # The position is identified by the tabindex
        js = (
            f'Array.from(document.querySelectorAll(".shuffle-item--visible"))'
            f'.find(x => x.dataset.name == "{name}")?'
            f'.querySelector("a").tabIndex'
        )
        pos = self.browser.evaluate_script(js)
        return pos

    def test_filter(self):
        self.visit("/persons/")

        # Both are visible
        pos_peter = self._get_pos_by_name("Peter Russo")
        pos_hector = self._get_pos_by_name("Hector Mendoza")
        self.assertIsNotNone(pos_peter)
        self.assertIsNotNone(pos_hector)

        # Filter for democrats
        self.browser.find_by_css(".filter-organizations .organization-6").first.click()
        time.sleep(0.1)
        pos_peter = self._get_pos_by_name("Peter Russo")
        pos_hector = self._get_pos_by_name("Hector Mendoza")
        self.assertIsNotNone(pos_peter)
        self.assertIsNone(pos_hector)

        # Filter for republicans
        self.browser.find_by_css(".filter-organizations .organization-7").first.click()
        time.sleep(0.1)
        pos_peter = self._get_pos_by_name("Peter Russo")
        pos_hector = self._get_pos_by_name("Hector Mendoza")
        self.assertIsNone(pos_peter)
        self.assertIsNotNone(pos_hector)

    def test_sort(self):
        self.visit("/persons/")

        self.assertEqual(
            3, len(self.browser.find_by_css(".filter-organizations > label"))
        )
        self.assertEqual(3, len(self.browser.find_by_css("li.person")))
        self.assertTextIsPresent("Frank Underwood")

        # Default sorting: by name
        pos_peter = self._get_pos_by_name("Peter Russo")
        pos_hector = self._get_pos_by_name("Hector Mendoza")
        self.assertLess(pos_hector, pos_peter)

        # Switch to sorting by party
        self.browser.find_by_css("#btnSortDropdown").first.click()
        self.browser.find_by_css('.sort-selector a[data-sort="group"]').first.click()
        time.sleep(1)
        pos_peter = self._get_pos_by_name("Peter Russo")
        pos_hector = self._get_pos_by_name("Hector Mendoza")
        self.assertLess(pos_peter, pos_hector)

        # Switch back to sorting by name
        self.browser.find_by_css("#btnSortDropdown").first.click()
        self.browser.find_by_css('.sort-selector a[data-sort="name"]').first.click()
        time.sleep(1)
        pos_peter = self._get_pos_by_name("Peter Russo")
        pos_hector = self._get_pos_by_name("Hector Mendoza")
        self.assertLess(pos_hector, pos_peter)
