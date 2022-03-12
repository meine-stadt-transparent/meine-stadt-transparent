from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.template.loader import get_template
from django.utils.translation import gettext as _
from html2text import html2text

from mainapp.functions.mail import send_mail
from mainapp.models import UserProfile


class Command(BaseCommand):
    help = "Similar to test_email, but uses the notification template"

    def add_arguments(self, parser):
        parser.add_argument("to-email", type=str)
        parser.add_argument("--file", type=str)

    def handle(self, *args, **options):
        to_email = options["to-email"]
        profile = UserProfile.objects.filter(user__email=to_email).first()

        context = {
            "base_url": settings.ABSOLUTE_URI_BASE,
            "site_name": settings.TEMPLATE_META["logo_name"],
            "alerts": [],
            "email": to_email,
        }

        alerts = {
            'Dokumente mit einem Ortsbezug zu "Reitbahnstraße" (max. 500m entfernt)': [
                {
                    "title": "Anlage Eckpunktevereinbarung inkl.Anschreiben",
                    "url": "https://dresden.meine-stadt-transparent.de/file/41024/",
                    "type_name": "Datei",
                    "highlight": None,
                },
                {
                    "title": "V0771 / 21",
                    "url": "https://dresden.meine-stadt-transparent.de/file/40995/",
                    "type_name": "Datei",
                    "highlight": None,
                },
            ],
            'Dokumente mit "Digitalisierung"': [
                {
                    "title": "Stellungnahme V 0750 21 BMB",
                    "url": "https://dresden.meine-stadt-transparent.de/file/40738/",
                    "type_name": "Datei",
                    "highlight": "Kultur- und Nachbarschaftszentren sind eine Antwort auf Fragen einer älter werdenden"
                    "Gesellschaft bspw. zu Themen wie Einsamkeit, <mark>Digitalisierung</mark> und steigende",
                },
                {
                    "title": "V0750/21",
                    "url": "https://dresden.meine-stadt-transparent.de/file/40757/",
                    "type_name": "Datei",
                    "highlight": "Kultur- und Nachbarschaftszentren sind eine Antwort auf Fragen einer älter werdenden"
                    "Gesellschaft bspw. zu Themen wie Einsamkeit, <mark>Digitalisierung</mark> und steigende",
                },
            ],
        }

        for title, results in alerts.items():
            context["alerts"].append({"title": title, "results": results})

        message_html = get_template("email/user-alert.html").render(context)
        message_html = message_html.replace("&lt;mark&gt;", "<mark>").replace(
            "&lt;/mark&gt;", "</mark>"
        )
        if file := options.get("file"):
            Path(file).write_text(message_html)
        else:
            message_text = html2text(message_html)
            self.stdout.write("Sending notification to: %s" % to_email)
            send_mail(
                to_email,
                settings.PRODUCT_NAME + ": " + _("New search results"),
                message_text,
                message_html,
                profile,
            )
