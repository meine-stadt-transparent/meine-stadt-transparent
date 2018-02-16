from io import StringIO
from unittest import mock

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import Client
from django.test import TestCase

from mainapp.models import UserAlert
from mainapp.tests.live.helper import MockMainappSearch


class TestNotifyUsers(TestCase):
    fixtures = ['initdata']
    c = Client()

    def _create_user_with_alerts(self, email, alerts):
        newuser = User()
        newuser.email = email
        newuser.username = email
        newuser.is_active = 1
        newuser.save()

        for alert in alerts:
            alert_object = UserAlert()
            alert_object.search_string = alert
            alert_object.last_match = None
            alert_object.user = newuser
            alert_object.save()

    @mock.patch('mainapp.management.commands.notifyusers.Command.send_mail')
    @mock.patch("mainapp.functions.search_tools.MainappSearch.execute", new=MockMainappSearch.execute)
    def test_notify(self, send_mail_function):
        self._create_user_with_alerts("test@example.org", ["test"])

        out = StringIO()
        call_command('notifyusers', stdout=out, override_since="2017-01-01")

        self.assertEqual(send_mail_function.call_count, 1)
        self.assertEqual(send_mail_function.call_args[0][0], 'test@example.org')
        self.assertTrue('Title Highlight' in send_mail_function.call_args[0][1])
        self.assertTrue('Title <mark>Highlight</mark>' in send_mail_function.call_args[0][2])
        self.assertTrue('Unsubscribe' in send_mail_function.call_args[0][1])
        self.assertTrue('Unsubscribe' in send_mail_function.call_args[0][2])
