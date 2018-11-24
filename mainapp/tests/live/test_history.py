from django.urls import reverse

from mainapp.tests.live.chromedriver_test_case import ChromeDriverTestCase


class HistoryTest(ChromeDriverTestCase):
    fixtures = ["initdata"]

    def test_revision_button(self):
        self.visit(reverse("paper", args=[1]))
        self.assertTextIsNotPresent("Revisions")
        self.visit(reverse("paper", args=[3]))
        self.assertTextIsPresent("2 Revisions")
        self.click_by_css(".revision-dropdown-toggle")
        self.click_by_css("[title='2018-01-01T01:00:00+01:00']")
        self.assertTextIsPresent("Old Revision")
        self.assertTextIsPresent("Submitters 1")
        self.click_by_text("Back to the latest version")
        self.assertEqual(
            self.live_server_url + reverse("paper", args=[3]), self.browser.url
        )
