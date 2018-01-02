import datetime

from mainapp.tests.live.chromedriver_test_case import ChromeDriverTestCase


class CalendarTest(ChromeDriverTestCase):
    fixtures = ['initdata.json']

    def test_list_year(self):
        self.visit('/calendar/')
        self.assertTextIsPresent(str(datetime.datetime.now().year))
        self.browser.find_by_css('.fc-listYear-button').first.click()

        # In 2017, both meetings are visible
        self.browser.execute_script("jQuery('#calendar').fullCalendar( 'gotoDate', '2017-01-01' )")
        self.assertTextIsPresent("House Assembly Meeting 1")
        self.assertTextIsPresent("House Assembly Meeting November")

        # In 2016, both meetings are visible
        self.browser.execute_script("jQuery('#calendar').fullCalendar( 'gotoDate', '2016-01-01' )")
        self.assertTextIsNotPresent("House Assembly Meeting 1")
        self.assertTextIsNotPresent("House Assembly Meeting November")

    def test_month(self):
        self.visit('/calendar/')
        self.browser.find_by_css('.fc-month-button').first.click()

        # In september, the november-meeting is not visible
        self.browser.execute_script("jQuery('#calendar').fullCalendar( 'gotoDate', '2017-09-01' )")
        self.assertTextIsPresent("House Assembly Meeting 1")
        self.assertTextIsNotPresent("House Assembly Meeting November")

        # In november, only the november-meeting is visible
        self.browser.execute_script("jQuery('#calendar').fullCalendar( 'gotoDate', '2017-11-01' )")
        self.assertTextIsNotPresent("House Assembly Meeting 1")
        self.assertTextIsPresent("House Assembly Meeting November")
