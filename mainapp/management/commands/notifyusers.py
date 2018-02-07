import datetime

from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.template.loader import get_template
from django.utils import timezone, translation
from django.utils.translation import ugettext as _
from html2text import html2text

from mainapp.functions.search_tools import add_modified_since, search_result_for_notification
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

        results = []
        executed = s.execute()
        for hit in executed:
            result = hit.__dict__['_d_']  # Extract the raw fields from the hit
            result["type"] = hit.meta.doc_type.replace("_document", "").replace("_", "-")
            results.append(result)

        return results

    def notify_user(self, user: User, override_since: datetime, debug: bool):
        context = {
            "base_url": settings.ABSOLUTE_URI_BASE,
            "site_name": settings.TEMPLATE_META['logo_name'],
            "alerts": [],
            "email": user.email,
        }

        for alert in user.useralert_set.all():
            notifyobjects = self.perform_search(alert, override_since)
            for obj in notifyobjects:
                search_result_for_notification(obj)

            if len(notifyobjects) > 0:
                results = []
                for obj in notifyobjects:
                    results.append(search_result_for_notification(obj))
                context["alerts"].append({
                    "title": alert.__str__(),
                    "results": results
                })

        if debug:
            self.stdout.write("User %s: %i results\n" % (user.email, len(context['alerts'])))

        if len(context['alerts']) == 0:
            return

        message_html = get_template('email/user-alert.html').render(context)
        message_text = html2text(message_html)

        if debug:
            self.stdout.write(message_text)
        else:
            self.stdout.write("Sending notification to: %s" % user.email)
            mail_from = settings.DEFAULT_FROM_EMAIL_NAME + " <" + settings.DEFAULT_FROM_EMAIL + ">"
            send_mail(_("New search results"), message_text, mail_from, [user.email], html_message=message_html)

        if not override_since:
            for alert in user.useralert_set.all():
                alert.last_match = timezone.now()
                alert.save()

    def add_arguments(self, parser):
        parser.add_argument('--override-since', type=str)
        parser.add_argument('--debug', action='store_true')

    def handle(self, *args, **options):
        from django.conf import settings
        translation.activate(settings.LANGUAGE_CODE)

        override_since = options['override_since']
        if override_since is not None:
            override_since = datetime.datetime.strptime(override_since, '%Y-%m-%d')

        users = User.objects.all()
        for user in users:
            # @TODO Filter inactive users or users that have disabled notifications
            self.notify_user(user, override_since, options['debug'])
