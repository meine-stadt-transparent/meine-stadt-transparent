from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium.webdriver.chrome.options import Options
from django.test import modify_settings
from splinter import Browser


@modify_settings(MIDDLEWARE={
    'remove': ['django.middleware.csrf.CsrfViewMiddleware'],
})  # There seems to be a strange but where HTTPS=on is always set, making all CSRF-checks fail
class PersonsTest(StaticLiveServerTestCase):
    fixtures = ['initdata.json']
    browser = None

    @classmethod
    def setUpClass(cls):
        options = Options()
        options.add_experimental_option('prefs', {'intl.accept_languages': 'en_US'})
        cls.browser = Browser('chrome', headless=True, executable_path="node_modules/.bin/chromedriver", options=options)
        super(PersonsTest, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        cls.browser.quit()
        super(PersonsTest, cls).tearDownClass()

    def test_register(self):
        temp_password = '8I$KJ37Kdk'
        temp_email = 'test@example.org'

        browser = self.browser
        browser.visit('%s%s' % (self.live_server_url, '/'))
        browser.find_by_css('#main-menu-content .login-link').click()
        browser.find_by_css('.signup-link').click()
        browser.fill('email', temp_email)
        browser.fill('password1', temp_password)
        browser.find_by_css('#signup_form .save-row button').click()
        if not browser.is_text_present('Confirmation e-mail sent to ' + temp_email):
            self.fail('Confirmation message is not present')
