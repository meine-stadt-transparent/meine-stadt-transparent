from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Sends a test e-mail to check if the mail-system is configured correctly'

    def add_arguments(self, parser):
        parser.add_argument('to-email', type=str)

    def handle(self, *args, **options):
        to_email = options['to-email']

        mail_from = settings.DEFAULT_FROM_EMAIL_NAME + " <" + settings.DEFAULT_FROM_EMAIL + ">"
        msg = EmailMultiAlternatives(
            subject="Hello 🌏",
            body="The test e-mail has arrived 🎉",
            from_email=mail_from,
            to=[to_email],
            headers={
                'Precedence': 'bulk'
            }
        )
        msg.attach_alternative('<h1>The test e-mail has arrived 🎉</h1>', "text/html")
        msg.send()
