from datetime import datetime
from io import StringIO
from unittest import mock

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase

from mainapp.models import UserAlert, UserProfile
from mainapp.tests.live.helper import MockMainappSearch


class TestNotifyUsers(TestCase):
    fixtures = ["initdata"]

    def _create_user_with_alerts(self, email, alerts):
        newuser = User()
        newuser.email = email
        newuser.username = email
        newuser.is_active = 1
        newuser.save()

        UserProfile.objects.create(user=newuser)

        for alert in alerts:
            alert_object = UserAlert()
            alert_object.search_string = alert
            alert_object.last_match = None
            alert_object.user = newuser
            alert_object.save()

    @mock.patch("mainapp.functions.notify_users.send_mail")
    @mock.patch(
        "mainapp.functions.search.MainappSearch.execute", new=MockMainappSearch.execute
    )
    def test_notify(self, send_mail_function):
        self._create_user_with_alerts("test@example.org", ["test"])

        out = StringIO()
        call_command(
            "notify_users",
            stdout=out,
            override_since=datetime.fromisoformat("2017-01-01"),
        )

        self.assertEqual(send_mail_function.call_count, 1)
        self.assertEqual(send_mail_function.call_args[0][0], "test@example.org")
        self.assertTrue("Title Highlight" in send_mail_function.call_args[0][2])
        self.assertTrue(
            "Title <mark>Highlight</mark>" in send_mail_function.call_args[0][3]
        )
        self.assertTrue("Unsubscribe" in send_mail_function.call_args[0][2])
        self.assertTrue("Unsubscribe" in send_mail_function.call_args[0][3])
