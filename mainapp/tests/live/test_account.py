from unittest import skip

from django.test import override_settings

from mainapp.tests.live.chromedriver_test_case import ChromeDriverTestCase


class AccountTest(ChromeDriverTestCase):
    fixtures = ["initdata"]
    password1 = "8I$KJ37Kdk"
    email = "test@example.org"
    password2 = "sdir23744!ä"

    def check_register_new_account(self, email, password):
        self.visit("/")
        self.assertElementDoesNotExists(".my-account-link")
        self.browser.find_by_css("#main-menu-content .login-link").click()
        self.browser.find_by_css(".signup-link").click()
        self.browser.fill("email", email)
        self.browser.fill("password1", password)
        self.browser.find_by_css("#signup_form .save-row button").click()
        self.assertTextIsPresent("Confirmation e-mail sent to " + email)
        self.assertElementDoesExists(".my-account-link")

    def check_change_password(self, password):
        self.browser.find_by_css("#main-menu-content #navbarMyAccount").click()
        self.browser.find_by_css("#main-menu-content .change-password-link").click()
        # First, try it with an invalid password
        self.browser.fill("oldpassword", "wrongpassword")
        self.browser.fill("password1", self.password2)
        self.browser.fill("password2", self.password2)
        self.browser.find_by_css("form.password_change .save-row button").click()
        self.assertTextIsPresent("Please type your current password")
        self.assertTextIsNotPresent("Password successfully changed")
        # Now change it for real
        self.browser.fill("oldpassword", password)
        self.browser.fill("password1", self.password2)
        self.browser.fill("password2", self.password2)
        self.browser.find_by_css("form.password_change .save-row button").click()
        self.assertTextIsPresent("Password successfully changed")
        self.assertTextIsNotPresent("Please type your current password")
        return self.password2

    def check_password_invalidated(self, email, password, password2):
        """Check that I cannot log in with the old, but therefore with the new password."""
        self.logout()
        self.browser.find_by_css("#main-menu-content .login-link").click()
        self.browser.fill("login", email)
        self.browser.fill("password", password)
        self.browser.find_by_css("form.login button").click()
        self.assertTextIsNotPresent("Successfully signed in")
        self.assertTextIsPresent(
            "The e-mail address and/or password you specified are not correct"
        )
        self.browser.fill("login", email)
        self.browser.fill("password", password2)
        self.browser.find_by_css("form.login button").click()
        self.assertTextIsPresent("Successfully signed in")

    @override_settings(DEBUG=True)
    @skip
    def test_register_change_password(self):
        self.check_register_new_account(self.email, self.password1)

        # Check if I can login using this new account
        self.logout()
        self.login(self.email, self.password1)

        password2 = self.check_change_password(self.password1)
        self.check_password_invalidated(self.email, self.password1, password2)
