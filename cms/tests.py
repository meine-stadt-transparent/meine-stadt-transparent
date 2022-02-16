"""
The fixtures were created using:

./manage.py dumpdata --natural-foreign cms wagtailcore.page wagtailcore.site wagtailcore.pagerevision > cms/fixtures/simple_page.json
./manage.py dumpdata auth.user > cms/fixtures/user.json
"""

from django.test import TestCase


class TestCms(TestCase):
    fixtures = ["user.json", "simple_page.json"]
    user_email = "user@example.org"
    editor_email = "editor@example.org"
    password = "8I$KJ37Kdk"

    def test_show_edit_button(self):
        response = self.client.get("/infos/this-is-a-header/").content.decode()

        # This should be in its own test, but if I add a second method I get an unexplicable foreign key error
        # without context, so for now it stays here
        self.assertIn("This is a header", response)
        self.assertIn("This is a paragraph", response)

        self.assertNotIn("fa-pencil", response)
        self.client.login(username=self.editor_email, password=self.password)
        response = self.client.get("/infos/this-is-a-header/").content.decode()
        self.assertIn("fa-pencil", response)
        self.client.login(username=self.user_email, password=self.password)
        response = self.client.get("/infos/this-is-a-header/").content.decode()
        self.assertNotIn("fa-pencil", response)
