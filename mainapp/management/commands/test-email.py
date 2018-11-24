from django.core.management.base import BaseCommand

from mainapp.functions.mail import send_mail
from mainapp.models import UserProfile


class Command(BaseCommand):
    help = "Sends a test e-mail to check if the mail-system is configured correctly"

    def add_arguments(self, parser):
        parser.add_argument("to-email", type=str)

    def handle(self, *args, **options):
        body_text = "The test e-mail has arrived 🎉"
        body_html = "<h1>The test e-mail has arrived 🎉</h1>"

        to_email = options["to-email"]
        profile = UserProfile.objects.filter(user__email=to_email).first()

        send_mail(to_email, "Hello 🌏", body_text, body_html, profile)
