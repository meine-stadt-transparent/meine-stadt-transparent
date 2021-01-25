import logging
import os

from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import modify_settings
from selenium.webdriver.chrome.options import Options
from splinter import Browser

# On ubuntu with chromium installed as snap, we also need to use the chromedriver from the snap
if os.path.isfile("/snap/bin/chromium.chromedriver"):
    chromedriver_path = "/snap/bin/chromium.chromedriver"
else:
    chromedriver_path = "node_modules/chromedriver/bin/chromedriver"

logger = logging.getLogger(__name__)


@modify_settings(MIDDLEWARE={"remove": ["django.middleware.csrf.CsrfViewMiddleware"]})
class ChromeDriverTestCase(StaticLiveServerTestCase):
    """
    Specifics of ChromeDriverTestCase:
    - Chrome Headless is used
    - English is used for the UI
    - CSRF-checks are disabled, as referrer-checking seems to be problematic, as the HTTPS-header seems to be always set
    """

    browser = None

    @classmethod
    def setUpClass(cls):
        options = Options()
        options.add_experimental_option("prefs", {"intl.accept_languages": "en_US"})
        cls.browser = Browser(
            "chrome",
            executable_path=chromedriver_path,
            options=options,
            headless=not settings.DEBUG_TESTING,
        )
        super(ChromeDriverTestCase, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        cls.browser.quit()
        super(ChromeDriverTestCase, cls).tearDownClass()

    """
    Helper functions for a more convenient test syntax
    """

    def visit(self, path):
        self.browser.visit(self.live_server_url + path)

    def assetElementIsPresentByCss(self, css):
        self.assertTrue(len(self.browser.find_by_css(css)) > 0)

    def assetElementIsNotPresentByCss(self, css):
        self.assertTrue(len(self.browser.find_by_css(css)) == 0)

    def assertTextIsPresent(self, text):
        self.assertTrue(self.browser.is_text_present(text))

    def assertTextIsNotPresent(self, text):
        self.assertFalse(self.browser.is_text_present(text))

    def assertElementDoesExists(self, css_selector):
        self.assertTrue(self.browser.is_element_present_by_css(css_selector))

    def assertElementDoesNotExists(self, css_selector):
        self.assertFalse(self.browser.is_element_present_by_css(css_selector))

    def click_by_id(self, id):
        self.browser.find_by_id(id).first.click()

    def click_by_text(self, text):
        self.browser.find_by_text(text).first.click()

    def click_by_css(self, css):
        self.browser.find_by_css(css).first.click()

    """
    Functions for behaviors used by several test cases
    """

    def logout(self):
        self.browser.find_by_css("#main-menu-content #navbarMyAccount").click()
        self.browser.find_by_css("#main-menu-content .logout-button").click()
        self.assertTextIsPresent("You have signed out.")
        self.assertElementDoesExists("#main-menu-content .login-link")
        self.assertElementDoesNotExists("#main-menu-content .my-account-link")

    def login(self, username, password):
        self.browser.find_by_css("#main-menu-content .login-link").click()
        self.browser.fill("login", username)
        self.browser.fill("password", password)
        self.browser.find_by_css("form.login button").click()
        self.assertTextIsPresent("Successfully signed in as " + username)
