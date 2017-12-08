from mainapp.tests.live.chromedriver_test_case import ChromeDriverTestCase


class OrganizationsTest(ChromeDriverTestCase):
    fixtures = ['initdata.json']

    def test_organizations_filter(self):
        self.browser.visit('%s%s' % (self.live_server_url, '/organizations/'))
        self.assertElementDoesNotExists('.my-account-link')
        self.assertEqual(len(self.browser.find_by_css(".multi-list-filter-sublist > h2")), 3)
        self.assertEqual(len(self.browser.find_by_css(".multi-list-filter-sublist > ul")), 3)
        self.assertEqual(len(self.browser.find_by_css(".multi-list-filter-sublist > ul > li")), 7)
        self.assertTextIsPresent("Democrats")
        self.assertTextIsPresent("Republicans")
        self.browser.fill("filter", "Dem")
        self.assertTextIsPresent("Democrats")
        self.assertTextIsNotPresent("Republicans")
