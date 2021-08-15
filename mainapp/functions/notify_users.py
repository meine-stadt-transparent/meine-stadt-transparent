import logging
from datetime import timedelta, datetime
from typing import Optional, List

from django.conf import settings
from django.contrib.auth.models import User
from django.template.loader import get_template
from django.utils import timezone
from django.utils.translation import gettext as _
from elasticsearch_dsl import Q
from html2text import html2text

from mainapp.functions.mail import send_mail
from mainapp.functions.search import MainappSearch, parse_hit
from mainapp.functions.search_notification_tools import search_result_for_notification
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

        search = MainappSearch(
            alert.get_search_params(),
            extra_filter=[Q("range", modified={"gte": since.isoformat()})],
        )
        executed = search.execute()
        return [parse_hit(hit) for hit in executed.hits]

    def notify_user(self, user: User) -> bool:
        context = {
            "base_url": settings.ABSOLUTE_URI_BASE,
            "site_name": settings.TEMPLATE_META["logo_name"],
            "alerts": [],
            "email": user.email,
        }

        for alert in user.useralert_set.all():
            notify_objects = self.perform_search(alert)
            for obj in notify_objects:
                search_result_for_notification(obj)

            if len(notify_objects) > 0:
                results = []
                for obj in notify_objects:
                    results.append(search_result_for_notification(obj))
                context["alerts"].append({"title": str(alert), "results": results})

        logger.debug("User %s: %i results\n" % (user.email, len(context["alerts"])))

        if len(context["alerts"]) == 0:
            return False

        message_html = get_template("email/user-alert.html").render(context)
        message_html = message_html.replace("&lt;mark&gt;", "<mark>").replace(
            "&lt;/mark&gt;", "</mark>"
        )
        message_text = html2text(message_html)

        if self.simulate:
            logging.info(message_text)
        else:
            # TODO: When this is called by cron it shouldn't write to stdout
            logger.info("Sending notification to: %s" % user.email)
            send_mail(
                user.email,
                settings.PRODUCT_NAME + ": " + _("New search results"),
                message_text,
                message_html,
                user.profile,
            )

        if not self.override_since:
            for alert in user.useralert_set.all():
                alert.last_match = timezone.now()
                alert.save()

        return True

    def notify_all(self):
        alerts_send = 0
        users = User.objects.filter(is_active=True).all()
        for user in users:
            alert_send = self.notify_user(user)
            if alert_send:
                alerts_send += 1
        logger.info(f"Sent notifications to {alerts_send} users")
