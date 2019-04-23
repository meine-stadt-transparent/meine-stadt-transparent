from django.utils import timezone

from mainapp.tests.live.chromedriver_test_case import ChromeDriverTestCase


class CalendarTest(ChromeDriverTestCase):
    fixtures = ["initdata"]

    def test_list_year(self):
        self.visit("/calendar/")
        self.assertTextIsPresent(str(timezone.now().year))
        self.browser.find_by_css(".fc-listYear-button").first.click()

        # In 2017, both meetings are visible
        self.visit("/calendar/listYear/2017-01-02/")
        self.assertTextIsPresent("House Assembly Meeting 1")
        self.assertTextIsPresent("House Assembly Meeting November")

        # In 2016, both meetings are visible
        self.visit("/calendar/listYear/2016-01-02/")
        self.assertTextIsNotPresent("House Assembly Meeting 1")
        self.assertTextIsNotPresent("House Assembly Meeting November")

    def test_month(self):
        self.visit("/calendar/")

        # Do some semi-busy waiting to avoid race conditions
        while len(self.browser.find_by_css(".fc-month-button")) == 0:
            pass

        self.browser.find_by_css(".fc-month-button").first.click()

        # In september, the november-meeting is not visible
        self.visit("/calendar/month/2017-08-28/")
        self.assertTextIsPresent("House Assembly Meeting 1")
        self.assertTextIsNotPresent("House Assembly Meeting November")

        # In november, only the november-meeting is visible
        self.visit("/calendar/month/2017-11-01/")
        self.assertTextIsNotPresent("House Assembly Meeting 1")
        self.assertTextIsPresent("House Assembly Meeting November")

    def test_cancelled(self):
        self.visit("/calendar/listYear/2016-01-02/")
        self.assetElementIsNotPresentByCss(".cancelled")

        self.visit("/calendar/month/2017-11-01/")
        self.assertTextIsPresent("House Assembly Meeting November")
        self.assetElementIsPresentByCss(".cancelled")

        self.click_by_css(".cancelled")
        self.assertTextIsPresent("This meeting has been cancelled")
