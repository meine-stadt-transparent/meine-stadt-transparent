from mainapp.tests.live.chromedriver_test_case import ChromeDriverTestCase


class PersonsTest(ChromeDriverTestCase):
    fixtures = ['initdata.json']

    def test_register_change_password(self):
        temp_password = '8I$KJ37Kdk'  # Only used for this test case, so no harm done in committing this password ☺️
        temp_email = 'test@example.org'

        # Check if I can register a new account
        browser = self.browser
        browser.visit('%s%s' % (self.live_server_url, '/'))
        self.assertElementDoesNotExists('.my-account-link')
        browser.find_by_css('#main-menu-content .login-link').click()
        browser.find_by_css('.signup-link').click()
        browser.fill('email', temp_email)
        browser.fill('password1', temp_password)
        browser.find_by_css('#signup_form .save-row button').click()
        self.assertTextIsPresent('Confirmation e-mail sent to ' + temp_email)
        self.assertElementDoesExists('.my-account-link')

        # Check if I can login using this new account
        self.logout()
        self.login(temp_email, temp_password)

        # Check if I can change my password
        temp_password2 = 'sdir23744!ä'
        browser.find_by_css('#main-menu-content .my-account-link').click()
        browser.find_by_css('.change-password-link').click()
        # First, try it with an invalid password
        browser.fill('oldpassword', 'wrongpassword')
        browser.fill('password1', temp_password2)
        browser.fill('password2', temp_password2)
        browser.find_by_css('form.password_change .save-row button').click()
        self.assertTextIsPresent('Please type your current password')
        self.assertTextIsNotPresent('Password successfully changed')
        # Now change it for real
        browser.fill('oldpassword', temp_password)
        browser.fill('password1', temp_password2)
        browser.fill('password2', temp_password2)
        browser.find_by_css('form.password_change .save-row button').click()
        self.assertTextIsNotPresent('Please type your current password')
        self.assertTextIsPresent('Password successfully changed')

        # Check that I cannot log in with the old, but therefore with the new password
        self.logout()
        self.browser.find_by_css('#main-menu-content .login-link').click()
        self.browser.fill('login', temp_email)
        self.browser.fill('password', temp_password)
        self.browser.find_by_css('form.login button').click()
        self.assertTextIsNotPresent('Successfully signed in')
        self.assertTextIsPresent('The e-mail address and/or password you specified are not correct')
        self.browser.fill('login', temp_email)
        self.browser.fill('password', temp_password2)
        self.browser.find_by_css('form.login button').click()
        self.assertTextIsPresent('Successfully signed in')
