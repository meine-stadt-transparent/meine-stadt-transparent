import logging
from datetime import timedelta, datetime
from typing import Optional, List

from django.conf import settings
from django.contrib.auth.models import User
from django.template.loader import get_template
from django.utils import timezone
from django.utils.translation import ugettext as _
from html2text import html2text

from mainapp.functions.mail import send_mail
from mainapp.functions.search_notification_tools import search_result_for_notification
from mainapp.functions.search import MainappSearch, parse_hit
from mainapp.models import UserAlert

logger = logging.getLogger(__name__)


class NotifyUsers:
    fallback_timeframe = timedelta(days=14)

    def __init__(
        self, override_since: Optional[datetime] = None, simulate: bool = False
    ):
        self.override_since = override_since
        self.simulate = simulate

    def perform_search(self, alert: UserAlert) -> List[dict]:
        if self.override_since is not None:
            since = self.override_since
        elif alert.last_match is not None:
            since = alert.last_match
        else:
            since = timezone.now() - self.fallback_timeframe

        params = alert.get_search_params()
        params["after"] = str(since)
        mainapp_search = MainappSearch(params)

        executed = mainapp_search.execute()
        results = [parse_hit(hit) for hit in executed.hits]

        return results

    def notify_user(self, user: User) -> None:
        context = {
            "base_url": settings.ABSOLUTE_URI_BASE,
            "site_name": settings.TEMPLATE_META["logo_name"],
            "alerts": [],
            "email": user.email,
        }

        for alert in user.useralert_set.all():
            notifyobjects = self.perform_search(alert)
            for obj in notifyobjects:
                search_result_for_notification(obj)

            if len(notifyobjects) > 0:
                results = []
                for obj in notifyobjects:
                    results.append(search_result_for_notification(obj))
                context["alerts"].append({"title": str(alert), "results": results})

        logger.debug("User %s: %i results\n" % (user.email, len(context["alerts"])))

        if len(context["alerts"]) == 0:
            return

        message_html = get_template("email/user-alert.html").render(context)
        message_html = message_html.replace("&lt;mark&gt;", "<mark>").replace(
            "&lt;/mark&gt;", "</mark>"
        )
        message_text = html2text(message_html)

        if self.simulate:
            logging.info(message_text)
        else:
            # TODO: When this is called by cron it shouldn't write to stdout
            logging.info("Sending notification to: %s" % user.email)
            send_mail(
                user.email,
                _("New search results"),
                message_text,
                message_html,
                user.profile,
            )

        if not self.override_since:
            for alert in user.useralert_set.all():
                alert.last_match = timezone.now()
                alert.save()

    def notify_all(self) -> None:
        users = User.objects.filter(is_active=True).all()
        for user in users:
            self.notify_user(user)
