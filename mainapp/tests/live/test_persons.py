import time

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from splinter import Browser


class PersonsTest(StaticLiveServerTestCase):
    fixtures = ['initdata.json']
    selenium = None
    browser = None

    @classmethod
    def setUpClass(cls):
        cls.browser = Browser('chrome', headless=True, executable_path="node_modules/.bin/chromedriver")
        super(PersonsTest, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        # cls.selenium.quit()
        cls.browser.quit()
        super(PersonsTest, cls).tearDownClass()

    def test_filter(self):
        self.browser.visit('%s%s' % (self.live_server_url, '/persons/'))
        self.assertTrue(self.browser.find_by_text('Bob Birch').first.visible)
        self.assertTrue(self.browser.find_by_text('William Conway').first.visible)

        # Filter for democrats
        self.browser.find_by_css('.filter-parliamentary-groups .btn-secondary').first.click()
        time.sleep(1)
        self.assertTrue(self.browser.find_by_text('Bob Birch').first.visible)
        self.assertFalse(self.browser.find_by_text('William Conway').first.visible)
