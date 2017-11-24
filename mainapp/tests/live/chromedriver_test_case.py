from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from splinter import Browser

chromedriver_path = "node_modules/.bin/chromedriver"


class ChromeDriverTestCase(StaticLiveServerTestCase):
    browser = None

    @classmethod
    def setUpClass(cls):
        cls.browser = Browser('chrome', headless=True, executable_path=chromedriver_path)
        super(ChromeDriverTestCase, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        cls.browser.quit()
        super(ChromeDriverTestCase, cls).tearDownClass()
