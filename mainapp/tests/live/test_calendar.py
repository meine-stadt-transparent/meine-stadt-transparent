import time

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from splinter import Browser


class CalendarTest(StaticLiveServerTestCase):
    fixtures = ['initdata.json']
    browser = None

    @classmethod
    def setUpClass(cls):
        cls.browser = Browser('chrome', headless=True, executable_path="node_modules/.bin/chromedriver")
        super(CalendarTest, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        cls.browser.quit()
        super(CalendarTest, cls).tearDownClass()

    def test_list_year(self):
        self.browser.visit('%s%s' % (self.live_server_url, '/calendar/'))
        self.assertTrue(self.browser.is_text_present("2017"))
        self.browser.find_by_css('.fc-listYear-button').first.click()

        # In 2017, both meetings are visible
        self.browser.execute_script("jQuery('#calendar').fullCalendar( 'gotoDate', '2017-01-01' )")
        time.sleep(1)
        self.assertTrue(self.browser.is_text_present("House Assembly Meeting 1"))
        self.assertTrue(self.browser.is_text_present("House Assembly Meeting November"))

        # In 2016, both meetings are visible
        self.browser.execute_script("jQuery('#calendar').fullCalendar( 'gotoDate', '2016-01-01' )")
        time.sleep(1)
        self.assertFalse(self.browser.is_text_present("House Assembly Meeting 1"))
        self.assertFalse(self.browser.is_text_present("House Assembly Meeting November"))

    def test_month(self):
        self.browser.visit('%s%s' % (self.live_server_url, '/calendar/'))
        self.browser.find_by_css('.fc-month-button').first.click()

        # In september, the november-meeting is not visible
        self.browser.execute_script("jQuery('#calendar').fullCalendar( 'gotoDate', '2017-09-01' )")
        time.sleep(1)
        self.assertTrue(self.browser.is_text_present("House Assembly Meeting 1"))
        self.assertFalse(self.browser.is_text_present("House Assembly Meeting November"))

        # In november, only the november-meeting is visible
        self.browser.execute_script("jQuery('#calendar').fullCalendar( 'gotoDate', '2017-11-01' )")
        time.sleep(1)
        self.assertFalse(self.browser.is_text_present("House Assembly Meeting 1"))
        self.assertTrue(self.browser.is_text_present("House Assembly Meeting November"))
