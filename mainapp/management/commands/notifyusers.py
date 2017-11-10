import datetime

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone

from mainapp.documents import DOCUMENT_TYPE_NAMES
from mainapp.functions.search_tools import params_to_query, add_modified_since
from mainapp.models import UserAlert


class Command(BaseCommand):
    help = 'Notifies users about new search results'

    def perform_search(self, alert: UserAlert, override_since=None):
        if override_since is not None:
            since = override_since
        else:
            if alert.last_match is not None:
                since = alert.last_match
            else:
                since = timezone.now() - datetime.timedelta(days=14)

        options, s, errors = params_to_query(alert.get_search_params())
        s = add_modified_since(s, since)

        self.stdout.write("Alert: %s since %s" % (alert.search_string, since))
        results = []
        executed = s.execute()
        for hit in executed:
            result = hit.__dict__['_d_']  # Extract the raw fields from the hit
            result["type"] = hit.meta.doc_type.replace("_document", "").replace("_", "-")
            result["type_translated"] = DOCUMENT_TYPE_NAMES[result["type"]]
            results.append(result)

        return results

    def format_notification(self, title: str, objects):
        str = title + "\n" + "===========\n"
        for object in objects:
            if "short_name" in object:
                name = object["short_name"]
            elif "displayed_filename" in object:
                name = object["displayed_filename"]
            else:
                name = object.__str__()

            str += "- %s - %s  (Modified: %s)\n" % (object["type_translated"], name, object["modified"])

        str += "\n\n"
        return str

    def notify_user(self, user: User, override_since: datetime, debug: bool):
        self.stdout.write("Notifying user: %s\n===============\n" % user.email)
        notify_strs = []

        for alert in user.useralert_set.all():
            notifyobjects = self.perform_search(alert, override_since)
            if len(notifyobjects) > 0:
                notify_strs.append(self.format_notification(alert.__str__(), notifyobjects))

        if debug:
            if len(notify_strs) > 0:
                self.stdout.write("".join(notify_strs))
            else:
                self.stdout.write("-> NOTHING FOUND")
        else:
            mail_from = "Meine Stadt Transparent <" + settings.DEFAULT_FROM_EMAIL + ">"
            send_mail("New search results", "".join(notify_strs), mail_from, [user.email])
            pass

        if not override_since:
            for alert in user.useralert_set.all():
                alert.last_match = timezone.now()
                alert.save()

    def add_arguments(self, parser):
        parser.add_argument('--override-since', type=str)
        parser.add_argument('--debug', action='store_true')

    def handle(self, *args, **options):
        override_since = options['override_since']
        if override_since is not None:
            override_since = datetime.datetime.strptime(override_since, '%Y-%m-%d')

        users = User.objects.all()
        for user in users:
            # @TODO Filter inactive users or users that have disabled notifications
            self.notify_user(user, override_since, options['debug'])
